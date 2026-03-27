from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from web.models import Gathering, GatheringAnnouncement, GatheringRegistration, Profile


def _make_datetime(days_from_now):
    return timezone.now() + timezone.timedelta(days=days_from_now)


@override_settings(STRIPE_SECRET_KEY="dummy_key")
class GatheringModelTests(TestCase):
    """Unit tests for the Gathering, GatheringRegistration, and GatheringAnnouncement models."""

    @classmethod
    def setUpTestData(cls):
        cls.organizer = User.objects.create_user(username="organizer", email="organizer@example.com", password="pass")
        Profile.objects.get_or_create(user=cls.organizer)

        cls.attendee = User.objects.create_user(username="attendee", email="attendee@example.com", password="pass")
        Profile.objects.get_or_create(user=cls.attendee)

    def _create_gathering(self, **kwargs):
        defaults = {
            "title": "Test Gathering",
            "description": "A test gathering",
            "gathering_type": "meetup",
            "organizer": self.organizer,
            "start_datetime": _make_datetime(1),
            "end_datetime": _make_datetime(2),
            "is_virtual": False,
            "location": "Test Hall",
            "status": "published",
            "visibility": "public",
        }
        defaults.update(kwargs)
        return Gathering.objects.create(**defaults)

    def test_slug_auto_generated(self):
        """Slug is automatically created from the title."""
        g = self._create_gathering(title="My Cool Meetup")
        self.assertEqual(g.slug, "my-cool-meetup")

    def test_slug_unique_suffix(self):
        """Duplicate titles get a numbered suffix to keep slugs unique."""
        g1 = self._create_gathering(title="Python Night")
        g2 = self._create_gathering(title="Python Night")
        self.assertNotEqual(g1.slug, g2.slug)
        self.assertTrue(g2.slug.startswith("python-night-"))

    def test_str_representation(self):
        g = self._create_gathering(title="Hackathon Day")
        self.assertEqual(str(g), "Hackathon Day")

    def test_is_free_when_price_zero(self):
        g = self._create_gathering(price=0)
        self.assertTrue(g.is_free)

    def test_is_not_free_when_price_positive(self):
        g = self._create_gathering(price=10)
        self.assertFalse(g.is_free)

    def test_is_upcoming_for_future_event(self):
        g = self._create_gathering(
            start_datetime=_make_datetime(3),
            end_datetime=_make_datetime(4),
        )
        self.assertTrue(g.is_upcoming)

    def test_is_past_for_past_event(self):
        g = self._create_gathering(
            start_datetime=_make_datetime(-3),
            end_datetime=_make_datetime(-1),
        )
        self.assertTrue(g.is_past)

    def test_attendee_count_only_confirmed(self):
        g = self._create_gathering()
        GatheringRegistration.objects.create(gathering=g, attendee=self.attendee, status="confirmed")
        self.assertEqual(g.attendee_count, 1)

    def test_attendee_count_excludes_pending(self):
        g = self._create_gathering()
        GatheringRegistration.objects.create(gathering=g, attendee=self.attendee, status="pending")
        self.assertEqual(g.attendee_count, 0)

    def test_is_full_when_max_reached(self):
        g = self._create_gathering(max_attendees=1)
        GatheringRegistration.objects.create(gathering=g, attendee=self.attendee, status="confirmed")
        self.assertTrue(g.is_full)

    def test_is_not_full_when_below_max(self):
        g = self._create_gathering(max_attendees=5)
        self.assertFalse(g.is_full)

    def test_spots_remaining(self):
        g = self._create_gathering(max_attendees=3)
        GatheringRegistration.objects.create(gathering=g, attendee=self.attendee, status="confirmed")
        self.assertEqual(g.spots_remaining, 2)

    def test_spots_remaining_none_when_unlimited(self):
        g = self._create_gathering(max_attendees=None)
        self.assertIsNone(g.spots_remaining)

    def test_tag_list_parsed_correctly(self):
        g = self._create_gathering(tags="python, django, web")
        self.assertEqual(g.tag_list, ["python", "django", "web"])

    def test_tag_list_empty_for_no_tags(self):
        g = self._create_gathering(tags="")
        self.assertEqual(g.tag_list, [])

    def test_gathering_registration_str(self):
        g = self._create_gathering()
        reg = GatheringRegistration.objects.create(gathering=g, attendee=self.attendee, status="confirmed")
        self.assertIn(self.attendee.username, str(reg))
        self.assertIn(g.title, str(reg))

    def test_gathering_announcement_str(self):
        g = self._create_gathering()
        ann = GatheringAnnouncement.objects.create(
            gathering=g, author=self.organizer, title="Update", content="See you there!"
        )
        self.assertIn(g.title, str(ann))
        self.assertIn("Update", str(ann))


@override_settings(STRIPE_SECRET_KEY="dummy_key")
class GatheringViewTests(TestCase):
    """Integration tests for gathering views."""

    @classmethod
    def setUpTestData(cls):
        cls.organizer = User.objects.create_user(username="org_user", email="org@example.com", password="pass123")
        Profile.objects.get_or_create(user=cls.organizer)

        cls.other_user = User.objects.create_user(username="other_user", email="other@example.com", password="pass123")
        Profile.objects.get_or_create(user=cls.other_user)

    def setUp(self):
        self.client = Client()
        self.gathering = Gathering.objects.create(
            title="Public Meetup",
            description="Open to all",
            gathering_type="meetup",
            organizer=self.organizer,
            start_datetime=_make_datetime(5),
            end_datetime=_make_datetime(6),
            is_virtual=False,
            location="Community Centre",
            status="published",
            visibility="public",
        )

    def test_list_view_returns_200(self):
        response = self.client.get(reverse("gathering_list"))
        self.assertEqual(response.status_code, 200)

    def test_list_view_shows_published_gathering(self):
        response = self.client.get(reverse("gathering_list"))
        self.assertContains(response, "Public Meetup")

    def test_detail_view_returns_200(self):
        response = self.client.get(reverse("gathering_detail", kwargs={"slug": self.gathering.slug}))
        self.assertEqual(response.status_code, 200)

    def test_detail_view_shows_title(self):
        response = self.client.get(reverse("gathering_detail", kwargs={"slug": self.gathering.slug}))
        self.assertContains(response, "Public Meetup")

    def test_create_view_requires_login(self):
        response = self.client.get(reverse("create_gathering"))
        self.assertRedirects(
            response, f"/accounts/login/?next={reverse('create_gathering')}", fetch_redirect_response=False
        )

    def test_create_gathering_logged_in(self):
        self.client.login(username="org_user", password="pass123")
        response = self.client.get(reverse("create_gathering"))
        self.assertEqual(response.status_code, 200)

    def test_create_gathering_post(self):
        self.client.login(username="org_user", password="pass123")
        data = {
            "title": "New Workshop",
            "description": "A great workshop",
            "gathering_type": "workshop",
            "start_datetime": (_make_datetime(10)).strftime("%Y-%m-%dT%H:%M"),
            "end_datetime": (_make_datetime(11)).strftime("%Y-%m-%dT%H:%M"),
            "is_virtual": False,
            "location": "Room 101",
            "registration_required": True,
            "price": "0.00",
            "visibility": "public",
            "status": "published",
            "max_attendees": "",
            "meeting_link": "",
            "tags": "",
        }
        response = self.client.post(reverse("create_gathering"), data)
        # Should redirect after creation
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Gathering.objects.filter(title="New Workshop").exists())

    def test_edit_gathering_by_non_organizer_redirects(self):
        self.client.login(username="other_user", password="pass123")
        response = self.client.get(reverse("edit_gathering", kwargs={"slug": self.gathering.slug}))
        # Should redirect with an error
        self.assertEqual(response.status_code, 302)

    def test_register_for_gathering_requires_login(self):
        response = self.client.post(reverse("register_for_gathering", kwargs={"slug": self.gathering.slug}))
        self.assertEqual(response.status_code, 302)

    def test_register_for_gathering(self):
        self.client.login(username="other_user", password="pass123")
        response = self.client.post(reverse("register_for_gathering", kwargs={"slug": self.gathering.slug}))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            GatheringRegistration.objects.filter(gathering=self.gathering, attendee=self.other_user).exists()
        )

    def test_cancel_registration(self):
        self.client.login(username="other_user", password="pass123")
        GatheringRegistration.objects.create(gathering=self.gathering, attendee=self.other_user, status="confirmed")
        response = self.client.post(reverse("cancel_gathering_registration", kwargs={"slug": self.gathering.slug}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            GatheringRegistration.objects.filter(gathering=self.gathering, attendee=self.other_user).exists()
        )

    def test_manage_view_requires_organizer(self):
        self.client.login(username="other_user", password="pass123")
        response = self.client.get(reverse("manage_gathering", kwargs={"slug": self.gathering.slug}))
        # Non-organizer is redirected
        self.assertEqual(response.status_code, 302)

    def test_manage_view_accessible_by_organizer(self):
        self.client.login(username="org_user", password="pass123")
        response = self.client.get(reverse("manage_gathering", kwargs={"slug": self.gathering.slug}))
        self.assertEqual(response.status_code, 200)

    def test_my_gatherings_requires_login(self):
        response = self.client.get(reverse("my_gatherings"))
        self.assertRedirects(
            response, f"/accounts/login/?next={reverse('my_gatherings')}", fetch_redirect_response=False
        )

    def test_my_gatherings_shows_own_gatherings(self):
        self.client.login(username="org_user", password="pass123")
        response = self.client.get(reverse("my_gatherings"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Public Meetup")

    def test_delete_gathering_by_organizer(self):
        self.client.login(username="org_user", password="pass123")
        slug = self.gathering.slug
        response = self.client.post(reverse("delete_gathering", kwargs={"slug": slug}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Gathering.objects.filter(slug=slug).exists())

    def test_private_gathering_hidden_from_non_organizer(self):
        private = Gathering.objects.create(
            title="Private Event",
            description="Organizer only",
            gathering_type="other",
            organizer=self.organizer,
            start_datetime=_make_datetime(5),
            end_datetime=_make_datetime(6),
            is_virtual=False,
            location="Secret location",
            status="published",
            visibility="private",
        )
        response = self.client.get(reverse("gathering_detail", kwargs={"slug": private.slug}))
        self.assertEqual(response.status_code, 404)
