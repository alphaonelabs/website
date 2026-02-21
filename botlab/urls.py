# Django URL configuration for the Virtual Robotics Playground feature
# This is the extracted URL pattern from web/urls.py

from django.urls import path

from . import views

urlpatterns = [
    path("robotics-playground/", views.robotics_playground, name="robotics_playground"),
]
