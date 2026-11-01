import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from web.models import EducationalVideo, Subject

User = get_user_model()


class EducationalVideoUploadTests(TestCase):
    def setUp(self):
        # create a user and two categories
        self.user = User.objects.create_user(username="tester", password="password")
        self.math = Subject.objects.create(name="Math", slug="math", order=1)
        self.bio = Subject.objects.create(name="Biology", slug="biology", order=2)

        self.upload_url = reverse("upload_educational_video")

    def test_get_upload_page_anonymous(self):
        """Anyone can GET the upload form."""
        resp = self.client.get(self.upload_url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "<form")

    def test_post_upload_authenticated(self):
        """Logged‑in users are attached as uploader."""
        self.client.login(username="tester", password="password")
        data = {
            "title": "Auth Video",
            "video_url": "https://youtu.be/dQw4w9WgXcQ",
            "description": "A great test",
            "category": self.math.id,
        }
        resp = self.client.post(self.upload_url, data)
        self.assertRedirects(resp, reverse("educational_videos_list"))

        vid = EducationalVideo.objects.get(title="Auth Video")
        self.assertEqual(vid.uploader, self.user)
        self.assertEqual(vid.category, self.math)

    def test_post_upload_anonymous(self):
        """Anonymous submission leaves uploader None."""
        data = {
            "title": "Anon Video",
            "video_url": "https://youtu.be/dQw4w9WgXcQ",
            "description": "Anonymous desc",
            "category": self.bio.id,
        }
        resp = self.client.post(self.upload_url, data)
        self.assertRedirects(resp, reverse("educational_videos_list"))

        vid = EducationalVideo.objects.get(title="Anon Video")
        self.assertIsNone(vid.uploader)
        self.assertEqual(vid.category, self.bio)

    def test_quick_add_ajax_missing_category(self):
        """AJAX quick‑add must include category."""
        self.client.login(username="tester", password="password")
        data = {
            "video_url": "https://youtu.be/dQw4w9WgXcQ",
            "title": "Bad Quick",
            "description": "",
            "category": "",
        }
        resp = self.client.post(self.upload_url, data, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(resp.status_code, 400)
        payload = json.loads(resp.content)
        self.assertFalse(payload["success"])
        self.assertIn("category", payload["error"])

    def test_quick_add_ajax_success(self):
        """Valid AJAX quick‑add returns success JSON."""
        self.client.login(username="tester", password="password")
        data = {
            "video_url": "https://youtu.be/dQw4w9WgXcQ",
            "title": "Good Quick",
            "description": "Auto desc",
            "category": self.math.id,
        }
        resp = self.client.post(self.upload_url, data, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(resp.status_code, 200)
        payload = json.loads(resp.content)
        self.assertTrue(payload["success"])
        self.assertTrue(EducationalVideo.objects.filter(title="Good Quick").exists())

    def test_youtube_embed_url_validation(self):
        """YouTube embed URLs should be valid."""
        self.client.login(username="tester", password="password")
        data = {
            "title": "Embed Video",
            "video_url": "https://www.youtube.com/embed/dQw4w9WgXcQ",
            "description": "Test embed URL",
            "category": self.math.id,
        }
        resp = self.client.post(self.upload_url, data)
        self.assertRedirects(resp, reverse("educational_videos_list"))
        self.assertTrue(EducationalVideo.objects.filter(title="Embed Video").exists())

    def test_youtube_embed_url_no_www_validation(self):
        """YouTube embed URLs without www should be valid."""
        self.client.login(username="tester", password="password")
        data = {
            "title": "Embed Video No WWW",
            "video_url": "https://youtube.com/embed/dQw4w9WgXcQ",
            "description": "Test embed URL without www",
            "category": self.math.id,
        }
        resp = self.client.post(self.upload_url, data)
        self.assertRedirects(resp, reverse("educational_videos_list"))
        self.assertTrue(EducationalVideo.objects.filter(title="Embed Video No WWW").exists())

    def test_vimeo_video_path_url_validation(self):
        """Vimeo URLs with /video/ path should be valid."""
        self.client.login(username="tester", password="password")
        data = {
            "title": "Vimeo Video Path",
            "video_url": "https://vimeo.com/video/123456789",
            "description": "Test Vimeo video path URL",
            "category": self.bio.id,
        }
        resp = self.client.post(self.upload_url, data)
        self.assertRedirects(resp, reverse("educational_videos_list"))
        self.assertTrue(EducationalVideo.objects.filter(title="Vimeo Video Path").exists())

    def test_invalid_youtube_embed_short_id(self):
        """YouTube embed URLs with invalid video ID should be rejected."""
        self.client.login(username="tester", password="password")
        data = {
            "title": "Invalid Embed",
            "video_url": "https://www.youtube.com/embed/shortid",
            "description": "Test invalid embed URL",
            "category": self.math.id,
        }
        resp = self.client.post(self.upload_url, data, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(resp.status_code, 400)
        payload = json.loads(resp.content)
        self.assertFalse(payload["success"])
        self.assertIn("video_url", payload["error"])

    def test_invalid_vimeo_short_id(self):
        """Vimeo URLs with short video ID should be rejected."""
        self.client.login(username="tester", password="password")
        data = {
            "title": "Invalid Vimeo",
            "video_url": "https://vimeo.com/video/1234567",  # 7 digits, need 8+
            "description": "Test invalid Vimeo URL",
            "category": self.bio.id,
        }
        resp = self.client.post(self.upload_url, data, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(resp.status_code, 400)
        payload = json.loads(resp.content)
        self.assertFalse(payload["success"])
        self.assertIn("video_url", payload["error"])
