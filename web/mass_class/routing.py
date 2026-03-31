# web/mass_class/routing.py
from django.urls import path

from . import consumers

websocket_urlpatterns = [
    path("ws/mass-class/broadcast/", consumers.MassClassTeacherConsumer.as_asgi()),
    path("ws/mass-class/view/<uuid:session_id>/", consumers.MassClassStudentConsumer.as_asgi()),
]

channel_routes = {
    "rtmp_bridge": "web.mass_class.rtmp_bridge.RTMPBridgeConsumer",
}
