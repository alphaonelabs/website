"""Registration URL for the learning app."""

from django.urls import path

from .auth_views import RegisterView

urlpatterns = [
    path("", RegisterView.as_view(), name="register"),
]
