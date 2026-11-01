from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from web.models import Course, Enrollment, Goods, Order, OrderItem, Profile, Storefront, Subject


@override_settings(STRIPE_SECRET_KEY="dummy_key")
class UserModelTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")

    @classmethod
    def tearDownClass(cls):
        cls.user.delete()
        super().tearDownClass()

    def setUp(self):
        self.profile, _ = Profile.objects.get_or_create(user=self.user)

    def test_user_creation(self):
        """Test that a user can be created"""
        user = User.objects.get(username="testuser")
        self.assertEqual(user.email, "test@example.com")
        self.assertTrue(user.check_password("testpass123"))

    def test_profile_creation_signal(self):
        """Test that a profile is automatically created when a user is created"""
        user = User.objects.get(username="testuser")
        self.assertTrue(hasattr(user, "profile"))
        self.assertIsInstance(user.profile, Profile)

    def test_profile_str(self):
        """Test the string representation of a Profile"""
        user = User.objects.get(username="testuser")
        expected_str = f"{user.username}'s profile (Private)"
        self.assertEqual(str(user.profile), expected_str)

    def test_profile_fields(self):
        """Test that profile fields can be set and retrieved"""
        user = User.objects.get(username="testuser")
        user.profile.bio = "Test bio"
        user.profile.expertise = "Test expertise"
        user.profile.is_teacher = True
        user.profile.save()

        updated_profile = Profile.objects.get(user=user)
        self.assertEqual(updated_profile.bio, "Test bio")
        self.assertEqual(updated_profile.expertise, "Test expertise")
        self.assertTrue(updated_profile.is_teacher)


@override_settings(STRIPE_SECRET_KEY="dummy_key")
class CourseModelTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher",
            email="teacher@example.com",
            password="teacherpass123",
        )
        self.teacher_profile, _ = Profile.objects.get_or_create(user=self.teacher, defaults={"is_teacher": True})

        # Create test subject
        self.subject = Subject.objects.create(
            name="Programming3",
            slug="programming3",
            description="Programming courses",
            icon="fas fa-code",
        )

        self.course = Course.objects.create(
            title="Test Course",
            description="Test Description",
            teacher=self.teacher,
            learning_objectives="Test Objectives",
            prerequisites="Test Prerequisites",
            price=99.99,
            max_students=50,
            subject=self.subject,
            level="beginner",
        )

    def test_course_creation(self):
        """Test course creation with valid data"""
        self.assertEqual(self.course.title, "Test Course")
        self.assertEqual(self.course.teacher, self.teacher)
        self.assertEqual(self.course.price, 99.99)
        self.assertEqual(self.course.max_students, 50)
        self.assertEqual(self.course.prerequisites, "Test Prerequisites")
        self.assertEqual(self.course.subject.name, "Programming3")
        self.assertEqual(self.course.level, "beginner")

    def test_course_str(self):
        """Test the string representation of Course"""
        self.assertEqual(str(self.course), "Test Course")

    def test_slug_generation(self):
        """Test that slug is automatically generated"""
        self.assertEqual(self.course.slug, "test-course")


class EnrollmentModelTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher",
            email="teacher@example.com",
            password="teacherpass123",
        )
        self.student = User.objects.create_user(
            username="student",
            email="student@example.com",
            password="studentpass123",
        )

        self.teacher_profile, _ = Profile.objects.get_or_create(user=self.teacher, defaults={"is_teacher": True})
        self.student_profile, _ = Profile.objects.get_or_create(user=self.student, defaults={"is_teacher": False})

        self.subject = Subject.objects.create(
            name="Programming4",
            slug="programming4",
            description="Programming courses",
            icon="fas fa-code",
        )

        self.course = Course.objects.create(
            title="Test Course",
            description="Test Description",
            teacher=self.teacher,
            learning_objectives="Test Objectives",
            prerequisites="Test Prerequisites",
            price=99.99,
            max_students=50,
            subject=self.subject,
            level="beginner",
        )

    def test_enrollment_creation(self):
        """Test enrollment creation"""
        enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course,
            status="pending",
        )
        self.assertEqual(enrollment.student, self.student)
        self.assertEqual(enrollment.course, self.course)
        self.assertEqual(enrollment.status, "pending")

    def test_enrollment_str(self):
        """Test the string representation of Enrollment"""
        enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course,
            status="pending",
        )
        expected_str = f"{self.student.username} - {self.course.title}"
        self.assertEqual(str(enrollment), expected_str)
        self.assertEqual(str(enrollment), expected_str)


class GoodsModelTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher",
            email="teacher@example.com",
            password="teacherpass123",
        )
        self.teacher_profile, _ = Profile.objects.get_or_create(user=self.teacher, defaults={"is_teacher": True})
        self.storefront = Storefront.objects.create(
            teacher=self.teacher,
            name="Test Store",
            description="Test Store Description",
        )

    def test_add_goods_to_store(self):
        """Test that a teacher can add goods to their store"""
        goods = Goods.objects.create(
            name="Test Good",
            description="Test Good Description",
            price=49.99,
            discount_price=39.99,  # Provide a default value for discount_price
            product_type="physical",
            stock=100,
            storefront=self.storefront,
        )
        self.assertEqual(goods.name, "Test Good")
        self.assertEqual(goods.storefront, self.storefront)
        self.assertEqual(goods.price, 49.99)
        self.assertEqual(goods.discount_price, 39.99)
        self.assertEqual(goods.stock, 100)
        self.assertEqual(goods.product_type, "physical")


class OrderModelTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher",
            email="teacher@example.com",
            password="teacherpass123",
        )
        self.student = User.objects.create_user(
            username="student",
            email="student@example.com",
            password="studentpass123",
        )
        self.teacher_profile, _ = Profile.objects.get_or_create(user=self.teacher, defaults={"is_teacher": True})
        self.student_profile, _ = Profile.objects.get_or_create(user=self.student, defaults={"is_teacher": False})
        self.storefront = Storefront.objects.create(
            teacher=self.teacher,
            name="Test Store",
            description="Test Store Description",
        )
        self.goods = Goods.objects.create(
            name="Test Good",
            description="Test Good Description",
            price=49.99,
            discount_price=39.99,  # Provide a default value for discount_price
            product_type="physical",
            stock=100,
            storefront=self.storefront,
        )

    def test_checkout_item(self):
        """Test that an item can be checked out completely"""
        order = Order.objects.create(
            user=self.student,
            total_price=self.goods.price,
            status="pending",
        )
        order_item = OrderItem.objects.create(
            order=order,
            goods=self.goods,
            quantity=1,
            price_at_purchase=self.goods.price,
        )
        self.assertEqual(order.user, self.student)
        self.assertEqual(order.total_price, self.goods.price)
        self.assertEqual(order.status, "pending")
        self.assertEqual(order_item.goods, self.goods)
        self.assertEqual(order_item.quantity, 1)
        self.assertEqual(order_item.price_at_purchase, self.goods.price)

        # Simulate payment completion
        order.status = "completed"
        order.save()
        self.assertEqual(order.status, "completed")
