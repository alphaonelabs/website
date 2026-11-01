# web/tests/test_cart_page.py

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()


class CartPageTest(TestCase):
    def setUp(self):
        self.client = Client()
        # Create and log in a test user
        self.user = User.objects.create_user(username="cartuser", password="cartpass")
        self.client.login(username="cartuser", password="cartpass")

    def test_empty_cart_page(self):
        """
        Verify that the cart page loads successfully and shows a message
        indicating the cart is empty when no items are present.
        """
        url = reverse("cart_view")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your cart is empty")
