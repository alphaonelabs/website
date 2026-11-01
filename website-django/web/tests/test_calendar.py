from django.contrib.auth import get_user_model
from django.middleware.csrf import get_token
from django.test import Client, TestCase
from django.urls import reverse


class CalendarTests(TestCase):
    def setUp(self):
        # Create a single test user for calendar creation
        self.user = get_user_model().objects.create_user(
            username="testuser", email="testuser@example.com", password="testpass123"
        )
        self.client = Client()

    def test_calendar_creation_and_sharing_flow(self):
        """Test the full flow of creating a calendar and adding time slots"""
        # Login required for calendar creation
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("create_calendar"))
        csrf_token = get_token(response.wsgi_request)

        # Create a calendar
        response = self.client.post(
            reverse("create_calendar"),
            {
                "title": "Test Calendar",
                "description": "A test calendar",
                "month": "0",  # January
                "year": "2024",
            },
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        share_token = data["share_token"]

        # Logout after creating calendar
        self.client.logout()

        # Anyone can view the calendar
        response = self.client.get(reverse("view_calendar", args=[share_token]))
        self.assertEqual(response.status_code, 200)
        csrf_token = get_token(response.wsgi_request)

        # First person adds a time slot (no login required)
        response = self.client.post(
            reverse("add_time_slot", args=[share_token]),
            {
                "name": "Alice",
                "day": "15",
                "start_time": "09:00",
                "end_time": "10:00",
            },
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])

        # Second person adds a time slot (no login required)
        response = self.client.post(
            reverse("add_time_slot", args=[share_token]),
            {
                "name": "Bob",
                "day": "15",
                "start_time": "10:00",
                "end_time": "11:00",
            },
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])

        # Verify both time slots were added
        response = self.client.get(reverse("get_calendar_data", args=[share_token]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["slots"]), 2)

        # Verify first slot
        slot1 = data["slots"][0]
        self.assertEqual(slot1["name"], "Alice")
        self.assertEqual(slot1["day"], 15)
        self.assertEqual(slot1["start_time"], "09:00")
        self.assertEqual(slot1["end_time"], "10:00")

        # Verify second slot
        slot2 = data["slots"][1]
        self.assertEqual(slot2["name"], "Bob")
        self.assertEqual(slot2["day"], 15)
        self.assertEqual(slot2["start_time"], "10:00")
        self.assertEqual(slot2["end_time"], "11:00")

    def test_calendar_validation(self):
        """Test validation for calendar creation and time slots"""
        # Login required for calendar creation
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("create_calendar"))
        csrf_token = get_token(response.wsgi_request)

        # Test invalid month (12)
        response = self.client.post(
            reverse("create_calendar"),
            {
                "title": "Test Calendar",
                "description": "A test calendar",
                "month": "12",  # Invalid month
                "year": "2024",
            },
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"], "Month must be between 0 and 11")

        # Create a valid calendar for testing time slots
        response = self.client.post(
            reverse("create_calendar"),
            {
                "title": "Test Calendar",
                "description": "A test calendar",
                "month": "0",
                "year": "2024",
            },
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        data = response.json()
        share_token = data["share_token"]

        # Logout after creating calendar
        self.client.logout()

        # Get CSRF token for time slot operations
        response = self.client.get(reverse("view_calendar", args=[share_token]))
        csrf_token = get_token(response.wsgi_request)

        # Test adding a time slot
        response = self.client.post(
            reverse("add_time_slot", args=[share_token]),
            {
                "name": "Alice",
                "day": "15",
                "start_time": "09:00",
                "end_time": "10:00",
            },
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(response.status_code, 200)

        # Test duplicate time slot (same person, same day)
        response = self.client.post(
            reverse("add_time_slot", args=[share_token]),
            {
                "name": "Alice",
                "day": "15",
                "start_time": "11:00",
                "end_time": "12:00",
            },
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"], "You already have a time slot for this day")

    def test_calendar_display_and_navigation(self):
        """Test calendar display and month navigation"""
        # Login required for calendar creation
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("create_calendar"))
        csrf_token = get_token(response.wsgi_request)

        # Create a calendar
        response = self.client.post(
            reverse("create_calendar"),
            {
                "title": "Test Calendar",
                "description": "A test calendar",
                "month": "0",  # January
                "year": "2024",
            },
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        data = response.json()
        share_token = data["share_token"]

        # Test calendar data retrieval
        response = self.client.get(reverse("get_calendar_data", args=[share_token]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["month"], 0)
        self.assertEqual(data["year"], 2024)
        self.assertEqual(data["title"], "Test Calendar")

        # Add some time slots
        response = self.client.post(
            reverse("add_time_slot", args=[share_token]),
            {
                "name": "User1",
                "day": "15",
                "start_time": "09:00",
                "end_time": "10:00",
            },
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(response.status_code, 200)

        # Verify time slot was added in calendar data
        response = self.client.get(reverse("get_calendar_data", args=[share_token]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["slots"]), 1)
        slot = data["slots"][0]
        self.assertEqual(slot["name"], "User1")
        self.assertEqual(slot["day"], 15)
        self.assertEqual(slot["start_time"], "09:00")
        self.assertEqual(slot["end_time"], "10:00")

    def test_calendar_dark_mode_compatibility(self):
        """Test calendar display in dark mode"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("create_calendar"))
        csrf_token = get_token(response.wsgi_request)

        # Create a calendar
        response = self.client.post(
            reverse("create_calendar"),
            {
                "title": "Dark Mode Calendar",
                "description": "Testing dark mode",
                "month": "0",
                "year": "2024",
            },
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        data = response.json()
        share_token = data["share_token"]

        # Test calendar view with dark mode classes
        response = self.client.get(reverse("view_calendar", args=[share_token]))
        self.assertEqual(response.status_code, 200)

        # Check for dark mode specific classes
        self.assertContains(response, "dark:bg-gray-800")
        self.assertContains(response, "dark:text-gray-200")
        self.assertContains(response, "dark:border-gray-700")
