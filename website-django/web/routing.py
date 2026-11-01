from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/classroom/(?P<classroom_id>\w+)/$", consumers.VirtualClassroomConsumer.as_asgi()),
    re_path(r"ws/whiteboard/(?P<room_name>\w+)/$", consumers.WhiteboardConsumer.as_asgi()),
]
