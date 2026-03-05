# web/mass_class/rtmp_bridge.py
import asyncio
import logging
import os
import signal

from channels.consumer import AsyncConsumer
from channels.db import database_sync_to_async
from django.conf import settings

from ..models import MassClassStream

logger = logging.getLogger(__name__)


class RTMPBridgeConsumer(AsyncConsumer):
    """
    Consumer that handles WebRTC to RTMP conversion and YouTube streaming
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.processes = {}  # Map of session_id -> subprocess

    async def start_stream(self, event):
        session_id = event["session_id"]
        sdp = event["sdp"]
        teacher_channel = event["teacher_channel"]

        # Create SDP file
        sdp_path = os.path.join(settings.MEDIA_ROOT, f"sdp_{session_id}.sdp")
        with open(sdp_path, "w") as f:
            f.write(sdp["sdp"])

        # Get YouTube stream key from the database
        youtube_key = await database_sync_to_async(self._get_youtube_key)(session_id)

        if not youtube_key:
            # Report error back to teacher
            await self.channel_layer.send(
                teacher_channel, {"type": "stream_error", "message": "Failed to get YouTube stream key."}
            )
            return

        # YouTube RTMP URL
        rtmp_url = f"rtmp://a.rtmp.youtube.com/live2/{youtube_key}"

        # Start GStreamer pipeline
        try:
            # This is a simplified example - in production, you'd need proper WebRTC to RTMP
            # conversion using GStreamer or similar media pipeline tools
            command = [
                "gst-launch-1.0",
                "webrtcsrc",
                f"sdp={sdp_path}",
                "!",
                "videoconvert",
                "!",
                "x264enc",
                "bitrate=2500",
                "speed-preset=veryfast",
                "tune=zerolatency",
                "!",
                "video/x-h264,profile=main",
                "!",
                "h264parse",
                "!",
                "flvmux",
                "streamable=true",
                "!",
                "rtmpsink",
                f"location={rtmp_url}",
            ]

            process = await asyncio.create_subprocess_exec(
                *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            self.processes[session_id] = process

            # Update stream status in database
            await database_sync_to_async(self._update_stream_status)(
                session_id, "active", f"https://www.youtube.com/watch?v={youtube_key}"
            )

            # Notify teacher that streaming has started
            await self.channel_layer.send(
                teacher_channel,
                {"type": "stream_started", "youtube_url": f"https://www.youtube.com/watch?v={youtube_key}"},
            )

            # Monitor process in background
            _task = asyncio.create_task(self._monitor_process(session_id, teacher_channel))

        except Exception:
            logger.exception("Failed to start GStreamer")

            # Report error back to teacher
            await self.channel_layer.send(
                teacher_channel, {"type": "stream_error", "message": "Failed to start streaming"}
            )

    async def ice_candidate(self, event):
        # Process ICE candidate (necessary for WebRTC)
        # In a real implementation, this would update the WebRTC connection
        pass

    async def stop_stream(self, event):
        session_id = event["session_id"]

        if session_id in self.processes:
            process = self.processes[session_id]
            try:
                process.terminate()
                await process.wait()
            except Exception:
                # Force kill if terminate fails
                try:
                    os.kill(process.pid, signal.SIGKILL)
                except Exception:
                    logger.exception("Failed to kill process")

            del self.processes[session_id]

        # Update stream status in database
        await database_sync_to_async(self._update_stream_status)(session_id, "ended", None)

    async def _monitor_process(self, session_id, teacher_channel):
        process = self.processes.get(session_id)
        if not process:
            return

        # Wait for process to complete
        stdout, stderr = await process.communicate()

        # Check if process exited with error
        if process.returncode != 0:
            error_message = stderr.decode() if stderr else "Unknown error"
            logger.error(f"Streaming process failed: {error_message}")

            # Notify teacher of error
            await self.channel_layer.send(
                teacher_channel, {"type": "stream_error", "message": f"Streaming failed: {error_message}"}
            )

            # Update stream status in database
            await database_sync_to_async(self._update_stream_status)(session_id, "error", None)

        # Clean up
        if session_id in self.processes:
            del self.processes[session_id]

    def _get_youtube_key(self, session_id):
        """Get YouTube stream key from the teacher's profile"""
        try:
            stream = MassClassStream.objects.get(stream_id=session_id)
            teacher = stream.teacher
            # Get the YouTube stream key from the teacher's profile
            if hasattr(teacher, 'profile') and teacher.profile.youtube_stream_key:
                return teacher.profile.youtube_stream_key
            return None
        except Exception:
            logger.exception("Error getting YouTube stream key")
            return None

    def _update_stream_status(self, session_id, status, youtube_url=None):
        try:
            stream = MassClassStream.objects.get(stream_id=session_id)
            stream.status = status

            if youtube_url:
                stream.youtube_url = youtube_url

            if status == "active" and not stream.started_at:
                from django.utils import timezone

                stream.started_at = timezone.now()

            stream.save()
            return True
        except Exception:
            logger.exception("Error updating stream status")
            return False
