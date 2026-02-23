import json
from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from ..models import MembershipPlan, Profile, UserMembership


class CreateDonationSubscriptionViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="test", email="test@example.com", password="pass")
        self.profile, _ = Profile.objects.get_or_create(user=self.user, defaults={"is_teacher": False})
        self.plan = MembershipPlan.objects.create(
            name="Basic", slug="basic", description="Basic plan", price_monthly=0, price_yearly=0
        )

    @patch("stripe.PaymentIntent.create")
    @patch("stripe.Customer.retrieve")
    def test_reuses_existing_stripe_customer(self, mock_retrieve, mock_payment_intent):
        UserMembership.objects.create(user=self.user, plan=self.plan, stripe_customer_id="cus_existing")
        mock_retrieve.return_value = Mock(id="cus_existing")
        mock_payment_intent.return_value = Mock(client_secret="secret", id="pi_123")
        self.client.login(username="test", password="pass")
        response = self.client.post(
            reverse("create_donation_subscription"),
            data=json.dumps({"amount": "10.00", "email": "test@example.com"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        mock_retrieve.assert_called_once_with("cus_existing")
