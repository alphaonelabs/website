# Django view for the Virtual Robotics Playground feature
# This is the extracted view function from web/views.py

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def robotics_playground(request: HttpRequest) -> HttpResponse:
    """Render the virtual robotics playground."""
    return render(request, "robotics_playground.html")
