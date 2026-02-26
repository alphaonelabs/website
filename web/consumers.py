import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone

from .models import VirtualClassroom, VirtualClassroomParticipant, VirtualClassroomWhiteboard
from .utils import can_access_classroom

logger = logging.getLogger(__name__)
User = get_user_model()


class VirtualClassroomConsumer(AsyncWebsocketConsumer):
    def _get_avatar_url_sync(self) -> str | None:
        """Return the current user's avatar URL, if available."""
        profile = getattr(self.user, "profile", None)
        avatar = getattr(profile, "avatar", None)
        return avatar.url if avatar else None

    @database_sync_to_async
    def get_avatar_url(self) -> str | None:
        """Fetch avatar URL via a sync wrapper safe for async consumers."""
        return self._get_avatar_url_sync()

    async def connect(self):
        self.classroom_id = self.scope["url_route"]["kwargs"]["classroom_id"]
        self.room_group_name = f"classroom_{self.classroom_id}"
        self.user = self.scope["user"]

        # Check if user is authenticated - reject if not
        if not self.user.is_authenticated:
            await self.close()
            return

        try:
            # Verify user has access to this classroom
            if not await self.verify_classroom_access():
                await self.close()
                return

            # Join room group
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)

            await self.accept()

            # Add user to active participants
            participant = await self.add_participant()
            if participant:
                # Clean up stale cache entries first
                await self.cleanup_stale_cache_entries()

                # Store in cache for real-time access
                await self.cache_participant_presence()

                avatar_url = await self.get_avatar_url()

                # Broadcast to others that user has joined
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "participant_joined",
                        "user": {
                            "username": self.user.username,
                            "full_name": self.user.get_full_name() or self.user.username,
                            "avatar_url": avatar_url,
                        },
                        "seat_id": participant.seat_id,
                    },
                )

                # Send current participants list to everyone
                await self.send_participants_list()

                # Broadcast classroom presence update
                await self.broadcast_classroom_presence()

            # Send current user info to the newly connected client
            await self.send(
                json.dumps(
                    {
                        "type": "user_info",
                        "user": {
                            "username": self.user.username,
                            "full_name": f"{self.user.first_name} {self.user.last_name}",
                            "seat_id": participant.seat_id if participant else None,
                        },
                    }
                )
            )
        except Exception:
            logger.exception("Error in connect")
            await self.close()

    async def disconnect(self, close_code):
        try:
            if hasattr(self, "user") and self.user.is_authenticated:
                # Remove user from active participants
                await self.remove_participant()

                # Clean up cache
                await self.remove_participant_presence()

                # Broadcast to others that user has left
                if hasattr(self, "room_group_name"):
                    try:
                        await self.channel_layer.group_send(
                            self.room_group_name,
                            {
                                "type": "participant_left",
                                "user": {
                                    "username": self.user.username,
                                    "full_name": self.user.get_full_name() or self.user.username,
                                },
                            },
                        )

                        # Broadcast updated presence
                        await self.broadcast_classroom_presence()
                    except Exception as e:
                        logger.error(f"Error sending participant_left message: {str(e)}")

                # Leave room group
                if hasattr(self, "room_group_name") and hasattr(self, "channel_name"):
                    try:
                        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
                    except Exception as e:
                        logger.error(f"Error discarding from group: {str(e)}")

        except Exception as e:
            logger.error(f"Error in disconnect: {str(e)}")
        finally:
            # Ensure connection is closed
            try:
                await self.close()
            except Exception:
                pass

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get("type")

            if message_type == "update_seat":
                seat_id = data.get("seat_id")
                # Check if seat is already occupied before updating
                is_occupied = await self.is_seat_occupied(seat_id)
                if is_occupied:
                    # Send error message to user
                    await self.send(
                        json.dumps(
                            {
                                "type": "seat_occupied",
                                "message": "This seat is already taken by another student.",
                                "seat_id": seat_id,
                            }
                        )
                    )
                else:
                    # Update participant's seat and last_active timestamp
                    participant = await self.update_participant_seat(seat_id)
                    if participant:
                        await self.update_seat_assignment_cache(seat_id)
                        await self.touch_participant_activity()
                        await self.broadcast_classroom_presence()
                        # Broadcast seat update to all users
                        await self.channel_layer.group_send(
                            self.room_group_name,
                            {
                                "type": "seat_updated",
                                "user": {
                                    "username": self.user.username,
                                    "full_name": self.user.get_full_name() or self.user.username,
                                },
                                "seat_id": seat_id,
                                "last_active": participant.last_active.isoformat(),
                            },
                        )
                        # Send updated participants list
                        await self.send_participants_list()
            elif message_type == "leave_seat":
                seat_id = data.get("seat_id")
                # Clear participant's seat
                participant = await self.clear_participant_seat()
                if participant:
                    avatar_url = await self.get_avatar_url()
                    # Update cache with empty string to clear seat
                    await self.update_seat_assignment_cache("")
                    # Update last_active timestamp
                    await self.touch_participant_activity()

                    # Broadcast seat leave
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            "type": "seat_left",
                            "user": {
                                "username": self.user.username,
                                "full_name": self.user.get_full_name() or self.user.username,
                                "avatar_url": avatar_url,
                            },
                            "seat_id": seat_id,
                        },
                    )

                    # Broadcast updated presence
                    await self.broadcast_classroom_presence()
                    # Send updated participants list
                    await self.send_participants_list()
            elif message_type == "position_update":
                # Update last_active timestamp
                await self.touch_participant_activity()
                # Broadcast position update to all other users
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "position_update",
                        "username": self.user.username,
                        "full_name": self.user.get_full_name() or self.user.username,
                        "position": data.get("position"),
                        "direction": data.get("direction"),
                        "isMoving": data.get("isMoving"),
                    },
                )
            elif message_type == "seat_updated":
                # Handle seat update
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "seat_updated",
                        "user": {
                            "username": self.user.username,
                            "full_name": f"{self.user.first_name} {self.user.last_name}",
                        },
                        "seat_id": data.get("seat_id"),
                    },
                )
        except json.JSONDecodeError:
            logger.error("Invalid JSON received")
        except Exception:
            logger.exception("Error in receive")

    async def participant_joined(self, event):
        """Handle when a new participant joins"""
        await self.send(text_data=json.dumps(event))

    async def participant_left(self, event):
        """Handle when a participant leaves"""
        await self.send(text_data=json.dumps(event))

    async def seat_updated(self, event):
        await self.send(text_data=json.dumps(event))

    async def seat_left(self, event):
        """Handle when a participant leaves a seat"""
        await self.send(text_data=json.dumps(event))

    async def seat_occupied(self, event):
        """Handle when trying to take an occupied seat"""
        await self.send(text_data=json.dumps(event))

    async def position_update(self, event):
        """Handle position update from other participants"""
        await self.send(text_data=json.dumps(event))

    async def participants_list(self, event):
        """Send the current list of participants"""
        await self.send(text_data=json.dumps({"type": "participants_list", "participants": event["participants"]}))

    @database_sync_to_async
    def verify_classroom_access(self) -> bool:
        """Verify user has access to this classroom"""
        try:
            classroom = VirtualClassroom.objects.get(id=self.classroom_id)
            return can_access_classroom(self.user, classroom)
        except VirtualClassroom.DoesNotExist:
            return False
        except Exception:
            logger.exception("Error verifying classroom access")
            return False

    @database_sync_to_async
    def add_participant(self):
        """Add user to active participants (without auto-assigning seat)"""
        try:
            classroom = VirtualClassroom.objects.get(id=self.classroom_id)
            participant, _created = VirtualClassroomParticipant.objects.get_or_create(
                classroom=classroom,
                user=self.user,
                defaults={"seat_id": ""},  # Start unseated (empty string) so users can move freely
            )
            return participant
        except Exception as e:
            logger.error(f"Error adding participant: {str(e)}")
            return None

    @database_sync_to_async
    def remove_participant(self):
        """Remove user from active participants"""
        try:
            VirtualClassroomParticipant.objects.filter(classroom_id=self.classroom_id, user=self.user).delete()
        except Exception as e:
            logger.error(f"Error removing participant: {str(e)}")

    @database_sync_to_async
    def update_participant_seat(self, seat_id):
        """Update participant's seat and last_active timestamp"""
        try:
            participant = VirtualClassroomParticipant.objects.filter(
                classroom_id=self.classroom_id, user=self.user
            ).first()
            if participant:
                participant.seat_id = seat_id
                participant.save()  # This will update last_active due to auto_now=True
                return participant
        except Exception as e:
            logger.error(f"Error updating participant seat: {str(e)}")
        return None

    @database_sync_to_async
    def touch_participant_activity(self) -> None:
        """Update last_active timestamp for current participant"""
        VirtualClassroomParticipant.objects.filter(classroom_id=self.classroom_id, user=self.user).update(
            last_active=timezone.now()
        )

    @database_sync_to_async
    def is_seat_occupied(self, seat_id):
        """Check if a seat is already occupied by another user"""
        try:
            # Get participants who were active in the last 5 minutes
            five_minutes_ago = timezone.now() - timezone.timedelta(minutes=5)
            occupied = (
                VirtualClassroomParticipant.objects.filter(
                    classroom_id=self.classroom_id, seat_id=seat_id, last_active__gte=five_minutes_ago
                )
                .exclude(user=self.user)
                .exists()
            )
            return occupied
        except Exception as e:
            logger.error(f"Error checking seat occupancy: {str(e)}")
            return False

    @database_sync_to_async
    def clear_participant_seat(self):
        """Clear participant's seat assignment"""
        try:
            participant = VirtualClassroomParticipant.objects.filter(
                classroom_id=self.classroom_id, user=self.user
            ).first()
            if participant:
                participant.seat_id = ""
                participant.save()  # This will update last_active due to auto_now=True
                return participant
        except Exception as e:
            logger.error(f"Error clearing participant seat: {str(e)}")
        return None

    @database_sync_to_async
    def get_participants_list(self):
        """Get list of current participants with their seat assignments"""
        try:
            # Get participants who were active in the last 5 minutes
            five_minutes_ago = timezone.now() - timezone.timedelta(minutes=5)
            participants = VirtualClassroomParticipant.objects.filter(
                classroom_id=self.classroom_id, last_active__gte=five_minutes_ago
            ).select_related("user")

            return [
                {
                    "username": p.user.username,
                    "full_name": p.user.get_full_name() or p.user.username,
                    "seat_id": p.seat_id,
                    "joined_at": p.joined_at.isoformat(),
                    "last_active": p.last_active.isoformat(),
                }
                for p in participants
            ]
        except Exception as e:
            logger.error(f"Error getting participants list: {str(e)}")
            return []

    async def send_participants_list(self):
        """Send current participants list to the group"""
        try:
            participants = await self.get_participants_list()
            await self.channel_layer.group_send(
                self.room_group_name, {"type": "participants_list", "participants": participants}
            )
        except Exception as e:
            logger.error(f"Error sending participants list: {str(e)}")

    @database_sync_to_async
    def cache_participant_presence(self) -> None:
        """Cache participant presence for real-time access (users start unseated)"""
        try:
            cache_key = f"classroom_{self.classroom_id}_presence"
            current_presence = cache.get(cache_key, {})

            # Get user's current seat if they have one (may be None)
            participant = VirtualClassroomParticipant.objects.get(classroom_id=self.classroom_id, user=self.user)
            assigned_seat = participant.seat_id  # Will be None if not yet seated

            current_presence[self.user.username] = {
                "user_id": self.user.id,
                "full_name": self.user.get_full_name() or self.user.username,
                "avatar_url": self._get_avatar_url_sync(),
                "joined_at": timezone.now().isoformat(),
                "seat_id": assigned_seat,
            }

            # Cache for 1 hour, will be refreshed on activity
            cache.set(cache_key, current_presence, 3600)
        except Exception:
            logger.exception("Error caching participant presence")

    @database_sync_to_async
    def cleanup_stale_cache_entries(self) -> None:
        """Remove stale cache entries and sync with active WebSocket connections"""
        try:
            cache_key = f"classroom_{self.classroom_id}_presence"
            current_presence = cache.get(cache_key, {})
            five_minutes_ago = timezone.now() - timezone.timedelta(minutes=5)
            active_usernames = set(
                VirtualClassroomParticipant.objects.filter(
                    classroom_id=self.classroom_id, last_active__gte=five_minutes_ago
                ).values_list("user__username", flat=True)
            )
            cleaned_presence = {u: v for u, v in current_presence.items() if u in active_usernames}
            cache.set(cache_key, cleaned_presence, 3600)
        except Exception:
            logger.exception("Error cleaning up stale cache entries")

    @database_sync_to_async
    def remove_participant_presence(self) -> None:
        """Remove participant from cache"""
        try:
            cache_key = f"classroom_{self.classroom_id}_presence"
            current_presence = cache.get(cache_key, {})

            if self.user.username in current_presence:
                del current_presence[self.user.username]
                cache.set(cache_key, current_presence, 3600)
        except Exception:
            logger.exception("Error removing participant presence")

    @database_sync_to_async
    def update_seat_assignment_cache(self, seat_id: str) -> None:
        """Update seat assignment in cache"""
        try:
            cache_key = f"classroom_{self.classroom_id}_presence"
            current_presence = cache.get(cache_key, {})

            if self.user.username in current_presence:
                current_presence[self.user.username]["seat_id"] = seat_id
                cache.set(cache_key, current_presence, 3600)
        except Exception:
            logger.exception("Error updating seat assignment cache")

    async def broadcast_classroom_presence(self) -> None:
        """Broadcast current classroom presence to all participants"""
        try:
            cache_key = f"classroom_{self.classroom_id}_presence"
            current_presence = await database_sync_to_async(cache.get)(cache_key, {})

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "classroom_presence_update",
                    "presence": current_presence,
                },
            )
        except Exception:
            logger.exception("Error broadcasting classroom presence")

    async def classroom_presence_update(self, event: dict) -> None:
        """Handle classroom presence updates"""
        await self.send(text_data=json.dumps({"type": "classroom_presence_update", "presence": event["presence"]}))


class WhiteboardConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = f"whiteboard_{self.room_name}"
        self.user = self.scope["user"]

        # Extract classroom_id from room_name (format: whiteboard_<classroom_id>)
        try:
            self.classroom_id = int(self.room_name.split("_")[1])
        except (IndexError, ValueError):
            await self.close()
            return

        # Check if user is authenticated
        if not self.user.is_authenticated:
            await self.close()
            return

        try:
            # Verify user has access to this classroom
            if not await self.verify_whiteboard_access():
                await self.close()
                return

            # Join room group
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)

            await self.accept()

            # Add user to active users list
            await self.add_user_to_room()

            # Send current active users list to everyone
            await self.send_active_users()

        except Exception as e:
            logger.error(f"Error in whiteboard connect: {str(e)}")
            await self.close()

    async def disconnect(self, close_code):
        try:
            if hasattr(self, "user") and self.user.is_authenticated:
                # Remove user from active users
                await self.remove_user_from_room()

                # Update active users list
                await self.send_active_users()

                # Leave room group
                if hasattr(self, "room_group_name") and hasattr(self, "channel_name"):
                    await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

        except Exception as e:
            logger.error(f"Error in whiteboard disconnect: {str(e)}")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get("type")

            if message_type == "canvas_update":
                # Only teachers can update the canvas
                is_teacher = await self.is_user_teacher()
                if is_teacher:
                    # Save canvas data to database
                    await self.save_canvas_data(data.get("canvas_data", ""), data.get("background_image", ""))

                    # Broadcast to all users except sender
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            "type": "canvas_update",
                            "canvas_data": data.get("canvas_data", ""),
                            "background_image": data.get("background_image", ""),
                            "sender": self.user.username,
                        },
                    )

            elif message_type == "drawing_action":
                # Only teachers can draw
                is_teacher = await self.is_user_teacher()
                if is_teacher:
                    # Broadcast real-time drawing actions
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {"type": "drawing_action", "action": data.get("action", {}), "sender": self.user.username},
                    )

            elif message_type == "clear_board":
                # Only teachers can clear the board
                is_teacher = await self.is_user_teacher()
                if is_teacher:
                    # Clear database
                    await self.clear_canvas_data()

                    # Broadcast clear action
                    await self.channel_layer.group_send(
                        self.room_group_name, {"type": "clear_board", "sender": self.user.username}
                    )

        except json.JSONDecodeError:
            logger.error("Invalid JSON received in whiteboard")
        except Exception as e:
            logger.error(f"Error in whiteboard receive: {str(e)}")

    async def canvas_update(self, event):
        """Handle canvas update broadcasts"""
        # Don't send back to the sender
        if event.get("sender") != self.user.username:
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "canvas_update",
                        "canvas_data": event["canvas_data"],
                        "background_image": event["background_image"],
                    }
                )
            )

    async def drawing_action(self, event):
        """Handle real-time drawing action broadcasts"""
        # Don't send back to the sender
        if event.get("sender") != self.user.username:
            await self.send(text_data=json.dumps({"type": "drawing_action", "action": event["action"]}))

    async def clear_board(self, event):
        """Handle clear board broadcasts"""
        # Don't send back to the sender
        if event.get("sender") != self.user.username:
            await self.send(text_data=json.dumps({"type": "clear_board"}))

    async def user_joined(self, event):
        """Handle when a user joins the whiteboard"""
        await self.send(text_data=json.dumps(event))

    async def user_left(self, event):
        """Handle when a user leaves the whiteboard"""
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def verify_whiteboard_access(self):
        """Verify user has access to this whiteboard/classroom"""
        try:
            classroom = VirtualClassroom.objects.get(id=self.classroom_id)

            # Check if user is the teacher
            if classroom.teacher == self.user:
                return True

            # Check if user is enrolled in the course
            if classroom.course:
                return classroom.course.enrollments.filter(student=self.user, status="approved").exists()

            return False
        except VirtualClassroom.DoesNotExist:
            return False
        except Exception as e:
            logger.error(f"Error verifying whiteboard access: {str(e)}")
            return False

    @database_sync_to_async
    def is_user_teacher(self):
        """Check if the current user is the teacher for this classroom"""
        try:
            classroom = VirtualClassroom.objects.get(id=self.classroom_id)
            return classroom.teacher == self.user
        except VirtualClassroom.DoesNotExist:
            return False
        except Exception as e:
            logger.error(f"Error checking if user is teacher: {str(e)}")
            return False

    @database_sync_to_async
    def save_canvas_data(self, canvas_data, background_image):
        """Save canvas data to database"""
        try:
            classroom = VirtualClassroom.objects.get(id=self.classroom_id)
            whiteboard, created = VirtualClassroomWhiteboard.objects.get_or_create(
                classroom=classroom, defaults={"canvas_data": {"data": canvas_data}, "last_updated_by": self.user}
            )

            whiteboard.canvas_data = {"data": canvas_data}
            if background_image:
                whiteboard.background_image = background_image
            whiteboard.last_updated_by = self.user
            whiteboard.save()

            return True
        except Exception as e:
            logger.error(f"Error saving canvas data: {str(e)}")
            return False

    @database_sync_to_async
    def clear_canvas_data(self):
        """Clear canvas data from database"""
        try:
            classroom = VirtualClassroom.objects.get(id=self.classroom_id)
            whiteboard, created = VirtualClassroomWhiteboard.objects.get_or_create(
                classroom=classroom, defaults={"canvas_data": {}, "last_updated_by": self.user}
            )

            whiteboard.canvas_data = {}
            whiteboard.background_image = ""
            whiteboard.last_updated_by = self.user
            whiteboard.save()

            return True
        except Exception as e:
            logger.error(f"Error clearing canvas data: {str(e)}")
            return False

    active_users = {}  # Class variable to track active users per room

    async def add_user_to_room(self):
        """Add user to active users list"""
        if self.room_group_name not in WhiteboardConsumer.active_users:
            WhiteboardConsumer.active_users[self.room_group_name] = set()

        WhiteboardConsumer.active_users[self.room_group_name].add(self.user.username)

    async def remove_user_from_room(self):
        """Remove user from active users list"""
        if self.room_group_name in WhiteboardConsumer.active_users:
            WhiteboardConsumer.active_users[self.room_group_name].discard(self.user.username)

            # Clean up empty rooms
            if not WhiteboardConsumer.active_users[self.room_group_name]:
                del WhiteboardConsumer.active_users[self.room_group_name]

    async def send_active_users(self):
        """Send active users list to all connected clients"""
        users_list = []
        if self.room_group_name in WhiteboardConsumer.active_users:
            users_list = [{"username": username} for username in WhiteboardConsumer.active_users[self.room_group_name]]

        await self.channel_layer.group_send(self.room_group_name, {"type": "active_users_update", "users": users_list})

    async def active_users_update(self, event):
        """Handle active users update broadcasts"""
        await self.send(
            text_data=json.dumps({"type": "user_joined", "users": event["users"]})  # Reuse existing handler
        )
