from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from web.models import FeatureVote


class FeatureVoteModelTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")
        cls.user2 = User.objects.create_user(username="testuser2", email="test2@example.com", password="testpass123")

    @classmethod
    def tearDownClass(cls):
        cls.user.delete()
        cls.user2.delete()
        super().tearDownClass()

    def setUp(self):
        self.feature_id = "test-feature"
        self.test_ip = "192.168.1.1"

    def test_feature_vote_creation_with_user(self):
        """Test that a feature vote can be created with a user"""
        vote = FeatureVote.objects.create(feature_id=self.feature_id, user=self.user, vote="up")
        self.assertEqual(vote.feature_id, self.feature_id)
        self.assertEqual(vote.user, self.user)
        self.assertEqual(vote.vote, "up")
        self.assertIsNone(vote.ip_address)

    def test_feature_vote_creation_with_ip(self):
        """Test that a feature vote can be created with an IP address"""
        vote = FeatureVote.objects.create(feature_id=self.feature_id, ip_address=self.test_ip, vote="down")
        self.assertEqual(vote.feature_id, self.feature_id)
        self.assertEqual(vote.ip_address, self.test_ip)
        self.assertEqual(vote.vote, "down")
        self.assertIsNone(vote.user)

    def test_feature_vote_str(self):
        """Test the string representation of a FeatureVote"""
        vote = FeatureVote.objects.create(feature_id=self.feature_id, user=self.user, vote="up")
        self.assertEqual(str(vote), "Thumbs Up for test-feature by testuser")

        ip_vote = FeatureVote.objects.create(feature_id=self.feature_id, ip_address=self.test_ip, vote="down")
        self.assertEqual(str(ip_vote), f"Thumbs Down for test-feature by {self.test_ip}")

    def test_unique_constraint_user(self):
        """Test that a user can only vote once per feature"""
        # Create first vote
        FeatureVote.objects.create(feature_id=self.feature_id, user=self.user, vote="up")

        # Try to create another vote for the same feature and user
        with self.assertRaises(ValidationError) as context:
            FeatureVote.objects.create(feature_id=self.feature_id, user=self.user, vote="down")
        self.assertIn("user", context.exception.message_dict)

    def test_unique_constraint_ip(self):
        """Test that an IP address can only vote once per feature when no user is provided"""
        # Create first vote
        FeatureVote.objects.create(feature_id=self.feature_id, ip_address=self.test_ip, user=None, vote="up")

        # Try to create another vote for the same feature and IP
        with self.assertRaises(ValidationError) as context:
            FeatureVote.objects.create(feature_id=self.feature_id, ip_address=self.test_ip, user=None, vote="down")
        self.assertIn("ip_address", context.exception.message_dict)

    def test_user_can_vote_multiple_features(self):
        """Test that a user can vote on multiple different features"""
        # Vote on first feature
        FeatureVote.objects.create(feature_id=self.feature_id, user=self.user, vote="up")

        # Vote on second feature
        FeatureVote.objects.create(feature_id="another-feature", user=self.user, vote="down")
        self.assertEqual(FeatureVote.objects.filter(user=self.user).count(), 2)

    def test_ip_can_vote_when_user_exists(self):
        """Test that an IP address can vote if no user is provided"""
        # Create vote with IP
        FeatureVote.objects.create(feature_id=self.feature_id, ip_address=self.test_ip, user=None, vote="up")

        # Create vote with user
        FeatureVote.objects.create(feature_id="another-feature", user=self.user, vote="down")
        self.assertEqual(FeatureVote.objects.filter(ip_address=self.test_ip).count(), 1)
        self.assertEqual(FeatureVote.objects.filter(user=self.user).count(), 1)

    def test_vote_choices(self):
        """Test that vote choices are enforced"""
        with self.assertRaises(ValidationError):
            FeatureVote.objects.create(feature_id=self.feature_id, user=self.user, vote="invalid")

    def test_required_fields(self):
        """Test that required fields are validated"""
        # Test missing feature_id
        with self.assertRaises(ValidationError) as context:
            FeatureVote.objects.create(user=self.user, vote="up")
        self.assertIn("feature_id", context.exception.message_dict)

        # Test missing vote
        with self.assertRaises(ValidationError) as context:
            FeatureVote.objects.create(feature_id=self.feature_id, user=self.user)
        self.assertIn("vote", context.exception.message_dict)

    def test_mutually_exclusive_fields(self):
        """Test that user and IP address are mutually exclusive"""
        with self.assertRaises(ValidationError) as context:
            FeatureVote.objects.create(feature_id=self.feature_id, user=self.user, ip_address=self.test_ip, vote="up")
        self.assertIn("Cannot provide both user and IP address", str(context.exception))

    def test_required_voter(self):
        """Test that either user or IP address must be provided"""
        with self.assertRaises(ValidationError) as context:
            FeatureVote.objects.create(feature_id=self.feature_id, vote="up")
        self.assertIn("Either user or IP address must be provided", str(context.exception))
