import logging
import os
from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from icalendar import Calendar, Event, vText

from .models import Enrollment, Session

logger = logging.getLogger(__name__)

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar"]


def generate_ical_feed(user):
    """
    Generate an iCal feed for a user's course sessions.

    Args:
        user: User model instance

    Returns:
        bytes: iCal feed content
    """
    cal = Calendar()
    site_name = getattr(settings, "SITE_NAME", "Education Website")
    site_domain = getattr(settings, "SITE_DOMAIN", "example.com")

    cal.add("prodid", f"-//{site_name}//Course Calendar//EN")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("x-wr-calname", f"{site_name} - Course Schedule")
    cal.add("x-wr-timezone", "UTC")

    # Get all sessions for the user
    if user.profile.is_teacher:
        sessions = Session.objects.filter(course__teacher=user)
    else:
        enrollments = Enrollment.objects.filter(student=user, status="approved")
        sessions = Session.objects.filter(course__enrollments__in=enrollments)

    for session in sessions:
        event = Event()
        event.add("summary", f"{session.course.title} - {session.title}")
        event.add("description", session.description)
        event.add("dtstart", session.start_time)
        event.add("dtend", session.end_time)
        event.add("dtstamp", timezone.now())

        # Add location (virtual or physical)
        if session.is_virtual and session.meeting_link:
            event.add("location", session.meeting_link)
        elif session.location:
            event.add("location", session.location)

        # Add organizer
        event.add("organizer", vText(f"mailto:{session.course.teacher.email}"))

        # Add unique identifier
        event["uid"] = f"session-{session.id}@{site_domain}"

        # Add reminder alerts
        event.add("begin", "valarm")
        event.add("trigger", timedelta(minutes=-30))
        event.add("action", "DISPLAY")
        event.add(
            "description",
            f"Reminder: {session.course.title} session starting in 30 minutes",
        )
        event.add("end", "valarm")

        cal.add_component(event)

    return cal.to_ical()


def generate_google_calendar_link(session):
    """
    Generate a Google Calendar event link for a session.

    Args:
        session: Session model instance

    Returns:
        str: Google Calendar event link
    """
    base_url = "https://calendar.google.com/calendar/render"
    params = {
        "action": "TEMPLATE",
        "text": f"{session.course.title} - {session.title}",
        "details": session.description,
        "dates": (f"{session.start_time.strftime('%Y%m%dT%H%M%SZ')}/" f"{session.end_time.strftime('%Y%m%dT%H%M%SZ')}"),
    }

    # Add location if available
    if session.is_virtual and session.meeting_link:
        params["location"] = session.meeting_link
    elif session.location:
        params["location"] = session.location

    # Build query string
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    return f"{base_url}?{query_string}"


def generate_outlook_calendar_link(session):
    """
    Generate an Outlook Calendar event link for a session.

    Args:
        session: Session model instance

    Returns:
        str: Outlook Calendar event link
    """
    base_url = "https://outlook.live.com/calendar/0/deeplink/compose"
    params = {
        "subject": f"{session.course.title} - {session.title}",
        "body": session.description,
        "startdt": session.start_time.isoformat(),
        "enddt": session.end_time.isoformat(),
        "path": "/calendar/action/compose",
        "rru": "addevent",
    }

    # Add location if available
    if session.is_virtual and session.meeting_link:
        params["location"] = session.meeting_link
    elif session.location:
        params["location"] = session.location

    # Build query string
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    return f"{base_url}?{query_string}"


def google_calendar_api():
    """
    Get Google Calendar API service.

    Returns:
        googleapiclient.discovery.Resource: The Calendar API service
        or None if credentials are not available.
    """
    creds = None
    credentials_path = os.environ.get("SERVICE_ACCOUNT_FILE", "google_credentials.json")
    token_path = os.path.join(settings.BASE_DIR, "token.json")

    # Load credentials from token.json if it exists
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(credentials_path):
                return None

            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open(token_path, "w") as token:
            token.write(creds.to_json())

    try:
        service = build("calendar", "v3", credentials=creds)
        return service
    except Exception as e:
        logger.error(f"Failed to build calendar service: {str(e)}")
        return None


def create_calendar_event(session):
    """Create a Google Calendar event for a session."""
    service = google_calendar_api()
    if not service:
        return None

    try:
        event = {
            "summary": f"{session.course.title} - {session.title}",
            "description": session.description,
            "start": {
                "dateTime": session.start_time.isoformat(),
                "timeZone": settings.TIME_ZONE,
            },
            "end": {
                "dateTime": session.end_time.isoformat(),
                "timeZone": settings.TIME_ZONE,
            },
        }

        if session.is_virtual:
            event["conferenceData"] = {
                "createRequest": {
                    "requestId": f"event-{session.id}",
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            }
        else:
            event["location"] = session.location

        event = (
            service.events()
            .insert(
                calendarId="primary",
                body=event,
                conferenceDataVersion=1 if session.is_virtual else 0,
            )
            .execute()
        )

        return event.get("id")
    except Exception as e:
        logger.error(f"Failed to create calendar event: {str(e)}")
        return None


def get_user_calendar_events(user, start_date=None, end_date=None):
    """Get calendar events for a user within a date range."""
    service = google_calendar_api()
    if not service:
        return []

    try:
        now = datetime.utcnow()
        time_min = start_date.isoformat() + "Z" if start_date else now.isoformat() + "Z"
        time_max = end_date.isoformat() + "Z" if end_date else (now + timedelta(days=30)).isoformat() + "Z"

        # Mock events for testing
        if settings.TESTING:
            return [
                {
                    "id": "event1",
                    "summary": "Test Event 1",
                    "start": {"dateTime": time_min},
                    "end": {"dateTime": time_max},
                },
                {
                    "id": "event2",
                    "summary": "Test Event 2",
                    "start": {"dateTime": time_min},
                    "end": {"dateTime": time_max},
                },
            ]

        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=time_min,
                timeMax=time_max,
                maxResults=50,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

        return events_result.get("items", [])
    except Exception as e:
        logger.error(f"Failed to get calendar events: {str(e)}")
        return []


def update_calendar_event(session):
    """Update a Google Calendar event."""
    service = google_calendar_api()
    if not service:
        return False

    try:
        event = {
            "summary": f"{session.course.title} - {session.title}",
            "description": session.description,
            "start": {
                "dateTime": session.start_time.isoformat(),
                "timeZone": settings.TIME_ZONE,
            },
            "end": {
                "dateTime": session.end_time.isoformat(),
                "timeZone": settings.TIME_ZONE,
            },
        }

        if session.is_virtual:
            event["conferenceData"] = {
                "createRequest": {
                    "requestId": f"event-{session.id}",
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            }
        else:
            event["location"] = session.location

        service.events().update(
            calendarId="primary",
            eventId=session.meeting_id,
            body=event,
            conferenceDataVersion=1 if session.is_virtual else 0,
        ).execute()
        return True
    except Exception as e:
        logger.error(f"Failed to update calendar event: {str(e)}")
        return False


def delete_calendar_event(session):
    """Delete a Google Calendar event."""
    service = google_calendar_api()
    if not service:
        return False

    try:
        service.events().delete(calendarId="primary", eventId=session.meeting_id).execute()
        return True
    except Exception as e:
        logger.error(f"Failed to delete calendar event: {str(e)}")
        return False
