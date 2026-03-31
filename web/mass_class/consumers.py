# web/mass_class/consumers.py
import json
import uuid

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from ..models import (
    MassClassHandRaise,
    MassClassPoll,
    MassClassPollOption,
    MassClassPollVote,
    MassClassQuestion,
    MassClassStream,
    MassClassViewer,
)


class MassClassTeacherConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]

        if not user.is_authenticated:
            await self.close(code=4003)
            return

        # Check if user is a teacher (has courses)
        is_teacher = await database_sync_to_async(self._is_teacher)(user)
        if not is_teacher:
            await self.close(code=4004)
            return

        # Generate a unique session ID
        self.session_id = str(uuid.uuid4())
        self.room_group_name = f"mass_class_{self.session_id}"

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

        # Send the session ID back to the client
        await self.send(
            text_data=json.dumps(
                {
                    "type": "session_created",
                    "session_id": self.session_id,
                }
            )
        )

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

        # Close any active stream
        await database_sync_to_async(self._close_stream)(self.session_id)

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get("type")

        if msg_type == "offer":
            # Create stream record in database
            created = await database_sync_to_async(self._create_stream)(
                self.scope["user"], data["session_id"], data["sdp"]
            )

            if created:
                # Forward the offer to the RTMP bridge service
                await self.channel_layer.send(
                    "rtmp_bridge",
                    {
                        "type": "start_stream",
                        "session_id": data["session_id"],
                        "sdp": data["sdp"],
                        "teacher_channel": self.channel_name,
                    },
                )

        elif msg_type == "ice_candidate":
            await self.channel_layer.send(
                "rtmp_bridge",
                {"type": "ice_candidate", "session_id": data["session_id"], "candidate": data["candidate"]},
            )

        elif msg_type == "stop_stream":
            await database_sync_to_async(self._close_stream)(data["session_id"])

            await self.channel_layer.send("rtmp_bridge", {"type": "stop_stream", "session_id": data["session_id"]})

            # Notify all viewers that the stream has ended
            await self.channel_layer.group_send(self.room_group_name, {"type": "stream_ended"})

        elif msg_type == "chat_message":
            # Forward chat message to all viewers
            user = self.scope["user"]
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "username": user.get_full_name() or user.username,
                    "message": data["message"],
                    "is_teacher": True,
                },
            )

        elif msg_type == "create_poll":
            # Create a poll and send to all viewers
            poll_id = str(uuid.uuid4())

            # Store poll in database
            await database_sync_to_async(self._create_poll)(self.session_id, poll_id, data["question"], data["options"])

            await self.channel_layer.group_send(
                self.room_group_name,
                {"type": "new_poll", "poll_id": poll_id, "question": data["question"], "options": data["options"]},
            )

        elif msg_type == "end_poll":
            # End active poll
            await database_sync_to_async(self._end_poll)(self.session_id)

            await self.channel_layer.group_send(self.room_group_name, {"type": "poll_ended"})

        elif msg_type == "answer_question":
            # Mark question as answered
            await database_sync_to_async(self._mark_question_answered)(data["question_id"])

            await self.channel_layer.group_send(
                self.room_group_name, {"type": "question_answered", "question_id": data["question_id"]}
            )

        elif msg_type == "dismiss_question":
            # Mark question as dismissed
            await database_sync_to_async(self._dismiss_question)(data["question_id"])

            await self.channel_layer.group_send(
                self.room_group_name, {"type": "question_dismissed", "question_id": data["question_id"]}
            )

    # Stream started event handler
    async def stream_started(self, event):
        await self.send(text_data=json.dumps({"type": "stream_started", "youtube_url": event["youtube_url"]}))

    # Stream error event handler
    async def stream_error(self, event):
        await self.send(text_data=json.dumps({"type": "stream_error", "message": event["message"]}))

    # Chat message event handler
    async def chat_message(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "chat_message",
                    "username": event["username"],
                    "message": event["message"],
                    "is_teacher": event.get("is_teacher", False),
                }
            )
        )

    # Viewer count update event handler
    async def viewer_count(self, event):
        await self.send(text_data=json.dumps({"type": "viewer_count", "count": event["count"]}))

    # New question event handler
    async def new_question(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "question",
                    "id": event["question_id"],
                    "username": event["username"],
                    "question": event["question"],
                }
            )
        )

    # Poll results event handler
    async def poll_results(self, event):
        await self.send(text_data=json.dumps({"type": "poll_results", "results": event["results"]}))

    # Helper methods
    def _is_teacher(self, user):
        return user.courses_teaching.exists()

    def _create_stream(self, user, session_id, sdp):
        try:
            stream = MassClassStream.objects.create(teacher=user, stream_id=session_id, status="initializing")
            return True
        except Exception:
            return False

    def _close_stream(self, session_id):
        try:
            stream = MassClassStream.objects.get(stream_id=session_id)
            stream.status = "ended"
            stream.save()
            return True
        except MassClassStream.DoesNotExist:
            return False

    def _create_poll(self, session_id, poll_id, question, options):
        try:
            stream = MassClassStream.objects.get(stream_id=session_id)
            poll = MassClassPoll.objects.create(stream=stream, poll_id=poll_id, question=question, is_active=True)

            for option in options:
                MassClassPollOption.objects.create(poll=poll, text=option)

            return True
        except Exception:
            return False

    def _end_poll(self, session_id):
        try:
            stream = MassClassStream.objects.get(stream_id=session_id)
            active_poll = MassClassPoll.objects.filter(stream=stream, is_active=True).first()

            if active_poll:
                active_poll.is_active = False
                active_poll.save()

            return True
        except Exception:
            return False

    def _mark_question_answered(self, question_id):
        try:
            question = MassClassQuestion.objects.get(id=question_id)
            question.status = "answered"
            question.save()
            return True
        except Exception:
            return False

    def _dismiss_question(self, question_id):
        try:
            question = MassClassQuestion.objects.get(id=question_id)
            question.status = "dismissed"
            question.save()
            return True
        except Exception:
            return False


class MassClassStudentConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]

        if not user.is_authenticated:
            await self.close(code=4003)
            return

        # Get the session ID from the URL route
        self.session_id = self.scope["url_route"]["kwargs"]["session_id"]
        self.room_group_name = f"mass_class_{self.session_id}"

        # Check if stream exists and is active
        stream_active = await database_sync_to_async(self._check_stream_active)(self.session_id)
        if not stream_active:
            await self.close(code=4005)
            return

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

        # Add viewer to the count
        await database_sync_to_async(self._add_viewer)(user.id, self.session_id)

        # Update viewer count
        viewer_count = await database_sync_to_async(self._get_viewer_count)(self.session_id)
        await self.channel_layer.group_send(self.room_group_name, {"type": "viewer_count", "count": viewer_count})

        # Send stream info
        stream_info = await database_sync_to_async(self._get_stream_info)(self.session_id)
        await self.send(
            text_data=json.dumps(
                {
                    "type": "stream_info",
                    "youtube_url": stream_info["youtube_url"],
                    "teacher_name": stream_info["teacher_name"],
                    "started_at": stream_info["started_at"].isoformat() if stream_info["started_at"] else None,
                }
            )
        )

        # Send active poll if any
        active_poll = await database_sync_to_async(self._get_active_poll)(self.session_id)
        if active_poll:
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "new_poll",
                        "poll_id": active_poll["id"],
                        "question": active_poll["question"],
                        "options": active_poll["options"],
                    }
                )
            )

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

        # Remove viewer from count
        user = self.scope["user"]
        await database_sync_to_async(self._remove_viewer)(user.id, self.session_id)

        # Update viewer count
        viewer_count = await database_sync_to_async(self._get_viewer_count)(self.session_id)
        await self.channel_layer.group_send(self.room_group_name, {"type": "viewer_count", "count": viewer_count})

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get("type")

        if msg_type == "chat_message":
            user = self.scope["user"]

            # Check for spam/rate limiting
            can_send = await database_sync_to_async(self._can_send_message)(user.id)
            if not can_send:
                await self.send(
                    text_data=json.dumps({"type": "error", "message": "Please wait before sending another message"})
                )
                return

            # Forward chat message to all viewers
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "username": user.get_full_name() or user.username,
                    "message": data["message"],
                    "is_teacher": False,
                },
            )

        elif msg_type == "ask_question":
            user = self.scope["user"]

            # Rate limiting for questions
            can_ask = await database_sync_to_async(self._can_ask_question)(user.id)
            if not can_ask:
                await self.send(
                    text_data=json.dumps({"type": "error", "message": "Please wait before asking another question"})
                )
                return

            # Create question in database
            question_id = await database_sync_to_async(self._create_question)(
                user.id, self.session_id, data["question"]
            )

            # Send question to teacher and all students
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "new_question",
                    "question_id": question_id,
                    "username": user.get_full_name() or user.username,
                    "question": data["question"],
                },
            )

        elif msg_type == "poll_vote":
            user = self.scope["user"]

            # Record the vote
            await database_sync_to_async(self._record_poll_vote)(user.id, data["poll_id"], data["option_index"])

            # Get updated poll results
            poll_results = await database_sync_to_async(self._get_poll_results)(data["poll_id"])

            # Send updated results to everyone
            await self.channel_layer.group_send(self.room_group_name, {"type": "poll_results", "results": poll_results})

        elif msg_type == "raise_hand":
            user = self.scope["user"]

            # Record hand raise
            hand_id = await database_sync_to_async(self._raise_hand)(user.id, self.session_id)

            # Notify teacher
            await self.channel_layer.group_send(
                self.room_group_name,
                {"type": "hand_raised", "hand_id": hand_id, "username": user.get_full_name() or user.username},
            )

    # Message event handlers
    async def chat_message(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "chat_message",
                    "username": event["username"],
                    "message": event["message"],
                    "is_teacher": event.get("is_teacher", False),
                }
            )
        )

    async def viewer_count(self, event):
        await self.send(text_data=json.dumps({"type": "viewer_count", "count": event["count"]}))

    async def new_poll(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "new_poll",
                    "poll_id": event["poll_id"],
                    "question": event["question"],
                    "options": event["options"],
                }
            )
        )

    async def poll_results(self, event):
        await self.send(text_data=json.dumps({"type": "poll_results", "results": event["results"]}))

    async def poll_ended(self, event):
        await self.send(text_data=json.dumps({"type": "poll_ended"}))

    async def question_answered(self, event):
        await self.send(text_data=json.dumps({"type": "question_answered", "question_id": event["question_id"]}))

    async def question_dismissed(self, event):
        await self.send(text_data=json.dumps({"type": "question_dismissed", "question_id": event["question_id"]}))

    async def stream_ended(self, event):
        await self.send(text_data=json.dumps({"type": "stream_ended"}))

    async def hand_acknowledged(self, event):
        await self.send(text_data=json.dumps({"type": "hand_acknowledged", "hand_id": event["hand_id"]}))

    # Helper methods
    def _check_stream_active(self, session_id):
        return MassClassStream.objects.filter(stream_id=session_id, status__in=["active", "initializing"]).exists()

    def _add_viewer(self, user_id, session_id):
        try:
            stream = MassClassStream.objects.get(stream_id=session_id)
            MassClassViewer.objects.get_or_create(user_id=user_id, stream=stream)
            return True
        except Exception:
            return False

    def _remove_viewer(self, user_id, session_id):
        try:
            stream = MassClassStream.objects.get(stream_id=session_id)
            MassClassViewer.objects.filter(user_id=user_id, stream=stream).delete()
            return True
        except Exception:
            return False

    def _get_viewer_count(self, session_id):
        try:
            stream = MassClassStream.objects.get(stream_id=session_id)
            return stream.viewers.count()
        except Exception:
            return 0

    def _get_stream_info(self, session_id):
        try:
            stream = MassClassStream.objects.get(stream_id=session_id)
            return {
                "youtube_url": stream.youtube_url,
                "teacher_name": stream.teacher.get_full_name() or stream.teacher.username,
                "started_at": stream.started_at,
            }
        except Exception:
            return {"youtube_url": None, "teacher_name": None, "started_at": None}

    def _can_send_message(self, user_id):
        # Simple rate limiting - implement as needed
        return True

    def _can_ask_question(self, user_id):
        # Simple rate limiting - implement as needed
        return True

    def _create_question(self, user_id, session_id, question_text):
        try:
            stream = MassClassStream.objects.get(stream_id=session_id)
            question = MassClassQuestion.objects.create(
                user_id=user_id, stream=stream, question=question_text, status="pending"
            )
            return str(question.id)
        except Exception:
            return None

    def _get_active_poll(self, session_id):
        try:
            stream = MassClassStream.objects.get(stream_id=session_id)
            poll = MassClassPoll.objects.filter(stream=stream, is_active=True).first()

            if poll:
                options = list(poll.options.values_list("text", flat=True))
                return {"id": str(poll.id), "question": poll.question, "options": options}
            return None
        except Exception:
            return None

    def _record_poll_vote(self, user_id, poll_id, option_index):
        try:
            poll = MassClassPoll.objects.get(id=poll_id, is_active=True)
            options = list(poll.options.all())

            if 0 <= option_index < len(options):
                option = options[option_index]

                # Remove any existing votes from this user
                MassClassPollVote.objects.filter(user_id=user_id, option__poll=poll).delete()

                # Create new vote
                MassClassPollVote.objects.create(user_id=user_id, option=option)

                return True
            return False
        except Exception:
            return False

    def _get_poll_results(self, poll_id):
        try:
            poll = MassClassPoll.objects.get(id=poll_id)
            results = []

            for option in poll.options.all():
                results.append({"text": option.text, "count": option.votes.count()})

            return results
        except Exception:
            return []

    def _raise_hand(self, user_id, session_id):
        try:
            stream = MassClassStream.objects.get(stream_id=session_id)
            hand_raise = MassClassHandRaise.objects.create(user_id=user_id, stream=stream, status="pending")
            return str(hand_raise.id)
        except Exception:
            return None
