from django.urls import re_path
from web.mass_class import routing as mass_class_routing


from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/classroom/(?P<classroom_id>\w+)/$", consumers.VirtualClassroomConsumer.as_asgi()),
    re_path(r"ws/whiteboard/(?P<room_name>\w+)/$", consumers.WhiteboardConsumer.as_asgi()),
]

websocket_urlpatterns = [] + mass_class_routing.websocket_urlpatterns
