from django.contrib.auth.models import User
from django.core import mail
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from web.models import Course, Session, SessionInvite, Subject


class SessionInviteTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpassword")
        self.teacher = User.objects.create_user(username="teacher", password="teacherpass")
        self.subject = Subject.objects.create(name="Test Subject")
        self.course = Course.objects.create(
            title="Test Course",
            description="Test course description",
            teacher=self.teacher,
            subject=self.subject,
            price=100,
        )
        self.session = Session.objects.create(
            course=self.course,
            title="Test Session",
            description="Test session description",
            start_time=timezone.now() + timezone.timedelta(days=1),
            end_time=timezone.now() + timezone.timedelta(days=1, hours=1),
            is_virtual=True,
            session_type="webinar",
        )

    def test_session_type_field(self):
        """Test that session_type field works correctly"""
        self.assertEqual(self.session.session_type, "webinar")
        self.session.session_type = "meetup"
        self.session.save()
        self.session.refresh_from_db()
        self.assertEqual(self.session.session_type, "meetup")

    def test_session_invite_creation(self):
        """Test creating a session invite"""
        invite = SessionInvite.objects.create(
            session=self.session, inviter=self.user, invitee_email="friend@example.com", message="Join my session!"
        )
        self.assertEqual(invite.status, "pending")
        self.assertEqual(invite.invitee_email, "friend@example.com")
        self.assertEqual(invite.message, "Join my session!")

    def test_session_invite_unique_constraint(self):
        """Test that duplicate invites for same session and email are not allowed"""
        SessionInvite.objects.create(session=self.session, inviter=self.user, invitee_email="friend@example.com")
        with self.assertRaises(Exception):
            SessionInvite.objects.create(session=self.session, inviter=self.user, invitee_email="friend@example.com")

    def test_invite_to_session_view_requires_login(self):
        """Test that invite_to_session view requires login"""
        response = self.client.get(reverse("invite_to_session", args=[self.session.id]))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_invite_to_session_view_access(self):
        """Test that only enrolled users or teachers can access invite view"""
        self.client.login(username="testuser", password="testpassword")
        response = self.client.get(reverse("invite_to_session", args=[self.session.id]))
        # Should redirect because user is not enrolled
        self.assertEqual(response.status_code, 302)

    def test_teacher_can_invite_to_session(self):
        """Test that teacher can access invite form"""
        self.client.login(username="teacher", password="teacherpass")
        response = self.client.get(reverse("invite_to_session", args=[self.session.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invite Friend")

    def test_send_session_invitation_email(self):
        """Test that session invitation sends email"""
        self.client.login(username="teacher", password="teacherpass")
        self.client.post(
            reverse("invite_to_session", args=[self.session.id]),
            {"email": "friend@example.com", "message": "Please join this session!"},
        )
        # Check that invitation was created
        invite = SessionInvite.objects.filter(session=self.session, invitee_email="friend@example.com").first()
        self.assertIsNotNone(invite)
        self.assertEqual(invite.message, "Please join this session!")
        # Check that email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Invitation to join", mail.outbox[0].subject)
        self.assertIn("friend@example.com", mail.outbox[0].to)

    def test_duplicate_invitation_warning(self):
        """Test that sending duplicate invitation shows warning"""
        SessionInvite.objects.create(session=self.session, inviter=self.teacher, invitee_email="friend@example.com")
        self.client.login(username="teacher", password="teacherpass")
        response = self.client.post(
            reverse("invite_to_session", args=[self.session.id]),
            {"email": "friend@example.com", "message": "Join again!"},
            follow=True,
        )
        # Check for warning message
        messages = list(response.context["messages"])
        self.assertTrue(any("already been sent" in str(m) for m in messages))
