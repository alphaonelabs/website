from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from web.views import custom_404


class AffiliationsAnd404Tests(TestCase):
    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()

    def test_affiliations_page_resolves_and_renders(self):
        """Verify /affiliations route resolves with HTTP 200 and renders cleanly."""
        url = reverse("affiliations")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "affiliations.html")
        self.assertTemplateUsed(response, "base.html")

        # Verify key content is rendered
        self.assertContains(response, "Our Affiliations")
        self.assertContains(response, "Open Science Lab")
        self.assertContains(response, "opensciencelabs.org")

        # Verify no raw Django/Jinja template syntax leaked into HTML output
        self.assertNotContains(response, "{%")
        self.assertNotContains(response, "%}")
        self.assertNotContains(response, "{{")
        self.assertNotContains(response, "}}")

    def test_affiliations_link_present_in_footer_navigation(self):
        """Verify the affiliations URL is present in the site navigation and footer."""
        affiliations_url = reverse("affiliations")
        about_response = self.client.get(reverse("about"))
        self.assertEqual(about_response.status_code, 200)
        self.assertContains(about_response, f'href="{affiliations_url}"')

    def test_custom_404_renders_clean_template_on_not_found(self):
        """Verify accessing a non-existent URL returns 404 without raw template tags."""
        response = self.client.get("/en/non-existent-page-not-found-xyz/")

        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "404.html")
        self.assertTemplateUsed(response, "base.html")
        self.assertContains(response, "Page Not Found", status_code=404)

        # Verify no raw Django/Jinja template syntax leaked into HTML output
        self.assertNotContains(response, "{%", status_code=404)
        self.assertNotContains(response, "%}", status_code=404)
        self.assertNotContains(response, "{{", status_code=404)
        self.assertNotContains(response, "}}", status_code=404)

    def test_custom_404_view_function_directly(self):
        """Verify custom_404 view handles calls with and without exception safely."""
        request = self.factory.get("/en/test-custom-404/")

        # Invocation without exception argument
        response_without_exc = custom_404(request)
        self.assertEqual(response_without_exc.status_code, 404)
        self.assertIn(b"Page Not Found", response_without_exc.content)
        self.assertNotIn(b"{%", response_without_exc.content)
        self.assertNotIn(b"{{", response_without_exc.content)

        # Invocation with exception argument
        response_with_exc = custom_404(request, exception=Exception("Page does not exist"))
        self.assertEqual(response_with_exc.status_code, 404)
        self.assertIn(b"Page Not Found", response_with_exc.content)
        self.assertNotIn(b"{%", response_with_exc.content)
        self.assertNotIn(b"{{", response_with_exc.content)
