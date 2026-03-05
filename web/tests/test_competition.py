from datetime import timedelta

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from web.models import (
    Challenge,
    Competition,
    CompetitionParticipant,
    CompetitionReward,
    Goods,
    Profile,
    Storefront,
)


class CompetitionModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")
        self.profile, _ = Profile.objects.get_or_create(user=self.user)

        # Create a challenge
        self.challenge = Challenge.objects.create(
            title="Test Challenge",
            description="Test Description",
            challenge_type="one_time",
            start_date=timezone.now().date(),
            end_date=(timezone.now() + timedelta(days=7)).date(),
        )

    def test_competition_creation(self):
        """Test that a competition can be created"""
        competition = Competition.objects.create(
            title="Test Competition",
            description="Test Description",
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=30),
            status="active",
            max_participants=100,
            entry_fee_points=50,
        )
        self.assertEqual(competition.title, "Test Competition")
        self.assertEqual(competition.status, "active")
        self.assertEqual(competition.max_participants, 100)
        self.assertEqual(competition.entry_fee_points, 50)

    def test_competition_str(self):
        """Test the string representation of Competition"""
        competition = Competition.objects.create(
            title="Test Competition",
            description="Test Description",
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=30),
            status="active",
        )
        expected_str = "Test Competition (Active)"
        self.assertEqual(str(competition), expected_str)

    def test_competition_date_validation(self):
        """Test that end date must be after start date"""
        start = timezone.now()
        end = start - timedelta(days=1)  # End before start - should fail

        competition = Competition(
            title="Test Competition",
            description="Test Description",
            start_date=start,
            end_date=end,
            status="active",
        )

        with self.assertRaises(ValidationError):
            competition.clean()

    def test_competition_is_active(self):
        """Test is_active property"""
        now = timezone.now()
        competition = Competition.objects.create(
            title="Test Competition",
            description="Test Description",
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=30),
            status="active",
        )
        self.assertTrue(competition.is_active)

        # Test inactive competition
        competition.status = "ended"
        competition.save()
        self.assertFalse(competition.is_active)

    def test_competition_challenges_relationship(self):
        """Test that challenges can be added to competition"""
        competition = Competition.objects.create(
            title="Test Competition",
            description="Test Description",
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=30),
            status="active",
        )
        competition.challenges.add(self.challenge)
        self.assertEqual(competition.challenges.count(), 1)
        self.assertEqual(competition.challenges.first(), self.challenge)

    def test_competition_is_full(self):
        """Test is_full property"""
        competition = Competition.objects.create(
            title="Test Competition",
            description="Test Description",
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=30),
            status="active",
            max_participants=1,
        )
        self.assertFalse(competition.is_full)

        # Add participant
        CompetitionParticipant.objects.create(competition=competition, user=self.user)
        self.assertTrue(competition.is_full)


class CompetitionRewardModelTests(TestCase):
    def setUp(self):
        self.competition = Competition.objects.create(
            title="Test Competition",
            description="Test Description",
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=30),
            status="active",
        )

        self.teacher = User.objects.create_user(
            username="teacher", email="teacher@example.com", password="teacherpass123"
        )
        self.teacher_profile, _ = Profile.objects.get_or_create(user=self.teacher, defaults={"is_teacher": True})
        self.storefront = Storefront.objects.create(
            teacher=self.teacher, name="Test Store", description="Test Store Description"
        )
        self.goods = Goods.objects.create(
            name="Test Merchandise",
            description="Test Description",
            price=49.99,
            product_type="physical",
            stock=100,
            storefront=self.storefront,
        )

    def test_reward_creation(self):
        """Test that a reward can be created"""
        reward = CompetitionReward.objects.create(
            competition=self.competition,
            reward_type="scholarship",
            name="$500 Scholarship",
            description="Scholarship for first place",
            position=1,
            value=500.00,
        )
        self.assertEqual(reward.name, "$500 Scholarship")
        self.assertEqual(reward.position, 1)
        self.assertEqual(reward.value, 500.00)

    def test_reward_str(self):
        """Test the string representation of CompetitionReward"""
        reward = CompetitionReward.objects.create(
            competition=self.competition,
            reward_type="points",
            name="100 Points",
            description="Points for second place",
            position=2,
            points_amount=100,
        )
        expected_str = f"100 Points - Position 2 in {self.competition.title}"
        self.assertEqual(str(reward), expected_str)

    def test_reward_validation_scholarship(self):
        """Test that scholarship rewards require a value"""
        reward = CompetitionReward(
            competition=self.competition,
            reward_type="scholarship",
            name="Scholarship",
            description="Test scholarship",
            position=1,
            # Missing value
        )
        with self.assertRaises(ValidationError):
            reward.clean()

    def test_reward_validation_points(self):
        """Test that point rewards require a points_amount"""
        reward = CompetitionReward(
            competition=self.competition,
            reward_type="points",
            name="Points Reward",
            description="Test points",
            position=1,
            # Missing points_amount
        )
        with self.assertRaises(ValidationError):
            reward.clean()

    def test_reward_validation_subscription(self):
        """Test that subscription rewards require duration"""
        reward = CompetitionReward(
            competition=self.competition,
            reward_type="premium_subscription",
            name="Premium Access",
            description="Test subscription",
            position=1,
            # Missing subscription_months
        )
        with self.assertRaises(ValidationError):
            reward.clean()

    def test_reward_validation_merchandise(self):
        """Test that merchandise rewards require goods_item"""
        reward = CompetitionReward(
            competition=self.competition,
            reward_type="goods",
            name="Merchandise",
            description="Test merchandise",
            position=1,
            # Missing goods_item
        )
        with self.assertRaises(ValidationError):
            reward.clean()

    def test_reward_unique_position_per_competition(self):
        """Test that each position can only have one reward per competition"""
        CompetitionReward.objects.create(
            competition=self.competition,
            reward_type="points",
            name="Points Reward 1",
            description="Test",
            position=1,
            points_amount=100,
        )

        # Try to create another reward at position 1
        with self.assertRaises(Exception):  # Should raise IntegrityError
            CompetitionReward.objects.create(
                competition=self.competition,
                reward_type="points",
                name="Points Reward 2",
                description="Test",
                position=1,
                points_amount=200,
            )


class CompetitionParticipantModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")
        self.profile, _ = Profile.objects.get_or_create(user=self.user)

        self.competition = Competition.objects.create(
            title="Test Competition",
            description="Test Description",
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=30),
            status="active",
        )

        # Create challenges for the competition
        self.challenge1 = Challenge.objects.create(
            title="Challenge 1",
            description="Test Description",
            challenge_type="one_time",
            start_date=timezone.now().date(),
            end_date=(timezone.now() + timedelta(days=7)).date(),
        )
        self.challenge2 = Challenge.objects.create(
            title="Challenge 2",
            description="Test Description",
            challenge_type="one_time",
            start_date=timezone.now().date(),
            end_date=(timezone.now() + timedelta(days=7)).date(),
        )
        self.competition.challenges.add(self.challenge1, self.challenge2)

    def test_participant_creation(self):
        """Test that a participant can be created"""
        participant = CompetitionParticipant.objects.create(competition=self.competition, user=self.user)
        self.assertEqual(participant.user, self.user)
        self.assertEqual(participant.competition, self.competition)
        self.assertEqual(participant.score, 0)

    def test_participant_str(self):
        """Test the string representation of CompetitionParticipant"""
        participant = CompetitionParticipant.objects.create(competition=self.competition, user=self.user, score=150)
        expected_str = f"{self.user.username} in {self.competition.title} - Score: 150"
        self.assertEqual(str(participant), expected_str)

    def test_participant_unique_per_competition(self):
        """Test that a user can only participate once per competition"""
        CompetitionParticipant.objects.create(competition=self.competition, user=self.user)

        # Try to create another participant for same user and competition
        with self.assertRaises(Exception):  # Should raise IntegrityError
            CompetitionParticipant.objects.create(competition=self.competition, user=self.user)

    def test_participant_ordering(self):
        """Test that participants are ordered by score descending"""
        user2 = User.objects.create_user(username="user2", email="user2@example.com", password="testpass123")
        Profile.objects.get_or_create(user=user2)

        participant1 = CompetitionParticipant.objects.create(competition=self.competition, user=self.user, score=100)
        participant2 = CompetitionParticipant.objects.create(competition=self.competition, user=user2, score=200)

        participants = list(CompetitionParticipant.objects.all())
        self.assertEqual(participants[0], participant2)  # Higher score first
        self.assertEqual(participants[1], participant1)
