"""
Tests for learning.ai.cloudflare_ai.CloudflareAIClient
"""

import json
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from learning.ai.cloudflare_ai import CloudflareAIClient, CloudflareAIError


@override_settings(
    CLOUDFLARE_ACCOUNT_ID="test-account-id",
    CLOUDFLARE_API_TOKEN="test-api-token",
    CLOUDFLARE_WORKER_URL="",
    CLOUDFLARE_AI_MODEL="@cf/meta/llama-3.1-8b-instruct",
)
class CloudflareAIClientDirectAPITest(TestCase):
    """Tests for direct Cloudflare REST API calls."""

    def _make_client(self):
        return CloudflareAIClient(
            account_id="test-account-id",
            api_token="test-api-token",
            worker_url="",
        )

    @patch("learning.ai.cloudflare_ai.requests.Session.post")
    def test_chat_returns_response_text(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "success": True,
            "result": {"response": "Recursion is when a function calls itself."},
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        client = self._make_client()
        result = client.chat(messages=[{"role": "user", "content": "Explain recursion"}])

        self.assertEqual(result, "Recursion is when a function calls itself.")
        mock_post.assert_called_once()

    @patch("learning.ai.cloudflare_ai.requests.Session.post")
    def test_chat_raises_on_api_error(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "success": False,
            "errors": [{"message": "Unauthorized"}],
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        client = self._make_client()
        with self.assertRaises(CloudflareAIError):
            client.chat(messages=[{"role": "user", "content": "Hello"}])

    @patch("learning.ai.cloudflare_ai.requests.Session.post")
    def test_complete_wraps_prompt_as_user_message(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"success": True, "result": {"response": "42"}}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        client = self._make_client()
        result = client.complete("What is 6×7?")

        self.assertEqual(result, "42")
        # Verify the payload was sent with messages
        sent_json = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json", {})
        self.assertIn("messages", sent_json)
        self.assertEqual(sent_json["messages"][0]["role"], "user")

    def test_raises_without_credentials(self):
        client = CloudflareAIClient(account_id="", api_token="", worker_url="")
        with self.assertRaises(CloudflareAIError):
            client.run_model("@cf/meta/llama-3.1-8b-instruct", {"messages": []})


@override_settings(
    CLOUDFLARE_ACCOUNT_ID="test-account-id",
    CLOUDFLARE_API_TOKEN="test-api-token",
    CLOUDFLARE_WORKER_URL="https://test-worker.example.com",
    CLOUDFLARE_AI_MODEL="@cf/meta/llama-3.1-8b-instruct",
)
class CloudflareAIClientWorkerTest(TestCase):
    """Tests for routing through Cloudflare Python Worker."""

    @patch("learning.ai.cloudflare_ai.requests.Session.post")
    def test_routes_via_worker_url(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"response": "Hello from worker"}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        client = CloudflareAIClient(worker_url="https://test-worker.example.com")
        result = client.chat(messages=[{"role": "user", "content": "Hi"}])

        self.assertEqual(result, "Hello from worker")
        called_url = mock_post.call_args[0][0]
        self.assertIn("test-worker.example.com", called_url)
