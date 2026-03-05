from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from web.models import Course, CourseMaterial, Enrollment, Profile, ShareUnlock, Subject


@override_settings(STRIPE_SECRET_KEY="dummy_key")
class ShareUnlockModelTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")
        cls.teacher = User.objects.create_user(
            username="teacher", email="teacher@example.com", password="teacherpass123"
        )
        cls.teacher.profile.is_teacher = True
        cls.teacher.profile.save()

    @classmethod
    def tearDownClass(cls):
        cls.user.delete()
        cls.teacher.delete()
        super().tearDownClass()

    def setUp(self):
        # Create a test course
        subject = Subject.objects.create(name="Test Subject")
        self.course = Course.objects.create(
            title="Test Course",
            description="Test Description",
            teacher=self.teacher,
            subject=subject,
            price=0,
        )

        # Create a material that requires sharing to unlock
        self.material = CourseMaterial.objects.create(
            course=self.course,
            title="Bonus Material",
            description="Unlock by sharing",
            material_type="document",
            external_url="https://example.com/bonus",
            unlock_by_sharing=True,
            shares_required=1,
        )

    def test_material_creation_with_unlock_by_sharing(self):
        """Test that a material can be created with unlock_by_sharing enabled"""
        self.assertTrue(self.material.unlock_by_sharing)
        self.assertEqual(self.material.shares_required, 1)

    def test_share_unlock_creation(self):
        """Test that a ShareUnlock can be created"""
        share_unlock = ShareUnlock.objects.create(user=self.user, material=self.material, platform="twitter")

        self.assertIsNotNone(share_unlock.share_token)
        self.assertEqual(len(share_unlock.share_token), 32)
        self.assertFalse(share_unlock.is_verified)
        self.assertIsNone(share_unlock.verified_at)

    def test_material_is_locked_for_user_without_shares(self):
        """Test that material is locked for user without verified shares"""
        is_unlocked = self.material.is_unlocked_for_user(self.user)
        self.assertFalse(is_unlocked)

    def test_material_is_unlocked_after_verified_share(self):
        """Test that material is unlocked after user shares and verifies"""
        share_unlock = ShareUnlock.objects.create(user=self.user, material=self.material, platform="twitter")

        # Verify the share
        share_unlock.is_verified = True
        share_unlock.verified_at = timezone.now()
        share_unlock.save()

        is_unlocked = self.material.is_unlocked_for_user(self.user)
        self.assertTrue(is_unlocked)

    def test_material_requires_multiple_shares(self):
        """Test that material can require multiple shares"""
        self.material.shares_required = 2
        self.material.save()

        # Create one verified share
        share_unlock1 = ShareUnlock.objects.create(
            user=self.user, material=self.material, platform="twitter", is_verified=True, verified_at=timezone.now()
        )

        # Material should still be locked (needs 2 shares)
        is_unlocked = self.material.is_unlocked_for_user(self.user)
        self.assertFalse(is_unlocked)

        # Create second verified share
        share_unlock2 = ShareUnlock.objects.create(
            user=self.user, material=self.material, platform="facebook", is_verified=True, verified_at=timezone.now()
        )

        # Now material should be unlocked
        is_unlocked = self.material.is_unlocked_for_user(self.user)
        self.assertTrue(is_unlocked)

    def test_material_without_unlock_by_sharing_is_always_unlocked(self):
        """Test that materials without unlock_by_sharing are always accessible"""
        normal_material = CourseMaterial.objects.create(
            course=self.course,
            title="Normal Material",
            material_type="document",
            external_url="https://example.com/normal",
            unlock_by_sharing=False,
        )

        is_unlocked = normal_material.is_unlocked_for_user(self.user)
        self.assertTrue(is_unlocked)


@override_settings(STRIPE_SECRET_KEY="dummy_key")
class ShareUnlockViewTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")
        cls.teacher = User.objects.create_user(
            username="teacher", email="teacher@example.com", password="teacherpass123"
        )
        cls.teacher.profile.is_teacher = True
        cls.teacher.profile.save()

    @classmethod
    def tearDownClass(cls):
        cls.user.delete()
        cls.teacher.delete()
        super().tearDownClass()

    def setUp(self):
        # Create a test course
        subject = Subject.objects.create(name="Test Subject")
        self.course = Course.objects.create(
            title="Test Course",
            description="Test Description",
            teacher=self.teacher,
            subject=subject,
            price=0,
        )

        # Enroll the user
        Enrollment.objects.create(student=self.user, course=self.course, status="approved")

        # Create a material that requires sharing
        self.material = CourseMaterial.objects.create(
            course=self.course,
            title="Bonus Material",
            description="Unlock by sharing",
            material_type="document",
            external_url="https://example.com/bonus",
            unlock_by_sharing=True,
            shares_required=1,
        )

    def test_create_share_token_requires_login(self):
        """Test that creating a share token requires authentication"""
        response = self.client.post(reverse("create_material_share_token", kwargs={"material_id": self.material.id}))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_create_share_token_success(self):
        """Test successful share token creation"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(
            reverse("create_material_share_token", kwargs={"material_id": self.material.id}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("share_token", data)
        self.assertIn("share_url", data)
        self.assertIn("share_text", data)

    def test_verify_share_token(self):
        """Test share token verification"""
        # Create a share unlock
        share_unlock = ShareUnlock.objects.create(user=self.user, material=self.material, platform="twitter")

        # Verify the share
        response = self.client.get(reverse("verify_material_share", kwargs={"share_token": share_unlock.share_token}))

        # Should redirect to course detail
        self.assertEqual(response.status_code, 302)

        # Check that share is verified
        share_unlock.refresh_from_db()
        self.assertTrue(share_unlock.is_verified)
        self.assertIsNotNone(share_unlock.verified_at)

    def test_course_detail_shows_locked_material(self):
        """Test that course detail page shows locked materials"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("course_detail", kwargs={"slug": self.course.slug}))

        self.assertEqual(response.status_code, 200)
        self.assertIn("material_unlock_status", response.context)

        # Check that material is locked
        unlock_status = response.context["material_unlock_status"]
        self.assertIn(self.material.id, unlock_status)
        self.assertFalse(unlock_status[self.material.id]["is_unlocked"])
        self.assertEqual(unlock_status[self.material.id]["shares_count"], 0)
        self.assertEqual(unlock_status[self.material.id]["shares_required"], 1)
