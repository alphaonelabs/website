import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()


class EvaluateCodeTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("virtual_lab:evaluate_code")
        self.user = User.objects.create_user(username="testuser", password="testpassword", email="test@example.com")
        self.payload = {"code": "print('Hello, World!')", "language": "python", "stdin": ""}
        cache.clear()

    def test_unauthenticated_access_blocked(self):
        # 1. Test: Unauthenticated access blocked
        # - Expect redirect or 302/403
        response = self.client.post(self.url, data=json.dumps(self.payload), content_type="application/json")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    @patch("web.virtual_lab.views.requests.post")
    def test_rate_limiting_works(self, mock_post):
        # 2. Test: Rate limiting works
        # - Simulate 6 POST requests
        # - 6th request should return 429
        self.client.login(username="testuser", password="testpassword")

        # Mock the external API response
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"run": {"stdout": "Hello, World!\n", "stderr": ""}}

        # First 5 requests should pass
        for i in range(5):
            response = self.client.post(self.url, data=json.dumps(self.payload), content_type="application/json")
            self.assertEqual(response.status_code, 200, f"Request {i + 1} failed")

        # 6th request should fail with 429
        response = self.client.post(self.url, data=json.dumps(self.payload), content_type="application/json")
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()["error"], "Rate limit exceeded. Try again later.")

    def test_invalid_json_handling(self):
        self.client.login(username="testuser", password="testpassword")
        response = self.client.post(self.url, data="invalid json", content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Invalid JSON payload")
