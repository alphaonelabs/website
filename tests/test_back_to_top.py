from django.test import Client, TestCase
from django.urls import reverse


class BackToTopButtonTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_button_present_on_homepage(self):
        """The base template should include the back-to-top button element."""
        response = self.client.get(reverse("index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="back-to-top-btn"')
