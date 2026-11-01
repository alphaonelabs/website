from datetime import datetime

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import Client, TestCase
from django.urls import reverse

from web.forms import GradeableLinkForm, LinkGradeForm
from web.models import GradeableLink, LinkGrade

User = get_user_model()

# Note: This file should NOT import pytest to ensure compatibility with Docker environment


class GradeableLinkModelTest(TestCase):
    """Test cases for the GradeableLink model."""

    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpassword")

        # Create a test link
        self.link = GradeableLink.objects.create(
            title="Test Link",
            url="https://example.com/test",
            description="This is a test link",
            user=self.user,
            link_type="article",
        )

    def test_link_creation(self):
        """Test that a link can be created with all fields."""
        self.assertEqual(self.link.title, "Test Link")
        self.assertEqual(self.link.url, "https://example.com/test")
        self.assertEqual(self.link.description, "This is a test link")
        self.assertEqual(self.link.user, self.user)
        self.assertEqual(self.link.link_type, "article")
        self.assertTrue(isinstance(self.link.created_at, datetime))
        self.assertTrue(isinstance(self.link.updated_at, datetime))

    def test_link_string_representation(self):
        """Test the string representation of a link."""
        self.assertEqual(str(self.link), "Test Link")

    def test_link_absolute_url(self):
        """Test that get_absolute_url returns the correct URL."""
        expected_url = reverse("gradeable_link_detail", kwargs={"pk": self.link.pk})
        self.assertEqual(self.link.get_absolute_url(), expected_url)

    def test_average_grade_no_grades(self):
        """Test that average_grade returns None when there are no grades."""
        self.assertIsNone(self.link.average_grade)

    def test_average_letter_grade_no_grades(self):
        """Test that average_letter_grade returns 'No grades yet' when there are no grades."""
        self.assertEqual(self.link.average_letter_grade, "No grades yet")

    def test_grade_count_no_grades(self):
        """Test that grade_count returns 0 when there are no grades."""
        self.assertEqual(self.link.grade_count, 0)

    def test_average_grade_with_grades(self):
        """Test that average_grade calculates correctly."""
        # Create a second user for grading
        user2 = User.objects.create_user(username="grader1", email="grader1@example.com", password="graderpass")

        user3 = User.objects.create_user(username="grader2", email="grader2@example.com", password="graderpass")

        # Add grades
        LinkGrade.objects.create(link=self.link, user=user2, grade="A", comment="Great work!")

        LinkGrade.objects.create(link=self.link, user=user3, grade="B+", comment="Good job, but could be improved.")

        # A = 4.0, B+ = 3.3, Average = 3.65
        self.assertAlmostEqual(self.link.average_grade, 3.65)

    def test_average_letter_grade_with_grades(self):
        """Test that average_letter_grade returns correctly."""
        # Create a second user for grading
        user2 = User.objects.create_user(username="grader1", email="grader1@example.com", password="graderpass")

        user3 = User.objects.create_user(username="grader2", email="grader2@example.com", password="graderpass")

        # Add grades
        LinkGrade.objects.create(link=self.link, user=user2, grade="A", comment="Great work!")

        LinkGrade.objects.create(link=self.link, user=user3, grade="B+", comment="Good job, but could be improved.")

        # A = 4.0, B+ = 3.3, Average = 3.65 which maps to A-
        self.assertEqual(self.link.average_letter_grade, "A-")

    def test_grade_count_with_grades(self):
        """Test that grade_count returns correctly."""
        # Create a second user for grading
        user2 = User.objects.create_user(username="grader1", email="grader1@example.com", password="graderpass")

        user3 = User.objects.create_user(username="grader2", email="grader2@example.com", password="graderpass")

        # Add grades
        LinkGrade.objects.create(link=self.link, user=user2, grade="A", comment="Great work!")

        LinkGrade.objects.create(link=self.link, user=user3, grade="B+", comment="Good job, but could be improved.")

        self.assertEqual(self.link.grade_count, 2)


class LinkGradeModelTest(TestCase):
    """Test cases for the LinkGrade model."""

    def setUp(self):
        # Create a test user and a grader
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpassword")

        self.grader = User.objects.create_user(username="grader", email="grader@example.com", password="graderpass")

        # Create a test link
        self.link = GradeableLink.objects.create(
            title="Test Link",
            url="https://example.com/test",
            description="This is a test link",
            user=self.user,
            link_type="article",
        )

        # Create a grade
        self.grade = LinkGrade.objects.create(
            link=self.link, user=self.grader, grade="A-", comment="Good work, but could use some improvements."
        )

    def test_grade_creation(self):
        """Test that a grade can be created with all fields."""
        self.assertEqual(self.grade.link, self.link)
        self.assertEqual(self.grade.user, self.grader)
        self.assertEqual(self.grade.grade, "A-")
        self.assertEqual(self.grade.comment, "Good work, but could use some improvements.")
        self.assertTrue(isinstance(self.grade.created_at, datetime))

    def test_grade_string_representation(self):
        """Test the string representation of a grade."""
        expected_str = f"{self.grader.username} graded {self.link.title} with {self.grade.grade}"
        self.assertEqual(str(self.grade), expected_str)

    def test_numeric_grade_property(self):
        """Test that numeric_grade returns the correct value."""
        self.assertEqual(self.grade.numeric_grade, 3.7)  # A- = 3.7

        # Create a grade with a different value
        grade_b = LinkGrade.objects.create(
            link=self.link,
            user=User.objects.create_user(username="user2", email="user2@example.com", password="pass"),
            grade="B",
            comment="Good effort.",
        )
        self.assertEqual(grade_b.numeric_grade, 3.0)  # B = 3.0

    def test_validation_comment_required_for_lower_grades(self):
        """Test that a comment is required for grades below A."""
        # Create a grade without a comment for a grade below A
        grade = LinkGrade(
            link=self.link,
            user=User.objects.create_user(username="user3", email="user3@example.com", password="pass"),
            grade="B+",
            comment="",
        )

        # Should raise a validation error
        with self.assertRaises(ValidationError):
            grade.clean()

    def test_validation_comment_not_required_for_a_grades(self):
        """Test that a comment is not required for A and A+ grades."""
        # Create a grade without a comment for an A grade
        grade_a = LinkGrade(
            link=self.link,
            user=User.objects.create_user(username="user4", email="user4@example.com", password="pass"),
            grade="A",
            comment="",
        )

        # Should not raise a validation error
        try:
            grade_a.clean()
        except ValidationError:
            self.fail("ValidationError was raised for grade 'A' without a comment")

        # Create a grade without a comment for an A+ grade
        grade_a_plus = LinkGrade(
            link=self.link,
            user=User.objects.create_user(username="user5", email="user5@example.com", password="pass"),
            grade="A+",
            comment="",
        )

        # Should not raise a validation error
        try:
            grade_a_plus.clean()
        except ValidationError:
            self.fail("ValidationError was raised for grade 'A+' without a comment")

    def test_unique_together_constraint(self):
        """Test that a user can only grade a link once."""
        # Try to create a second grade from the same user for the same link
        with self.assertRaises((ValidationError, IntegrityError)):  # Be specific about expected exceptions
            LinkGrade.objects.create(
                link=self.link, user=self.grader, grade="B", comment="Changed my mind"  # Same user as self.grade
            )


class GradeableLinkFormTest(TestCase):
    """Test cases for the GradeableLinkForm."""

    def test_form_valid_data(self):
        """Test that the form works with valid data."""
        form = GradeableLinkForm(
            data={
                "title": "Test Link",
                "url": "https://example.com/test",
                "description": "This is a test link",
                "link_type": "article",
            }
        )

        self.assertTrue(form.is_valid())

    def test_form_empty_data(self):
        """Test that the form correctly validates required fields."""
        form = GradeableLinkForm(data={})

        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)
        self.assertIn("url", form.errors)
        self.assertIn("link_type", form.errors)

    def test_form_invalid_url(self):
        """Test that the form validates URLs."""
        form = GradeableLinkForm(
            data={
                "title": "Test Link",
                "url": "not-a-url",
                "description": "This is a test link",
                "link_type": "article",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("url", form.errors)


class LinkGradeFormTest(TestCase):
    """Test cases for the LinkGradeForm."""

    def test_form_valid_data_with_comment(self):
        """Test that the form works with valid data and a comment."""
        form = LinkGradeForm(data={"grade": "B+", "comment": "Good job, but could be improved."})

        self.assertTrue(form.is_valid())

    def test_form_valid_data_a_grade_no_comment(self):
        """Test that the form works with an A grade and no comment."""
        form = LinkGradeForm(data={"grade": "A", "comment": ""})

        self.assertTrue(form.is_valid())

    def test_form_valid_data_a_plus_grade_no_comment(self):
        """Test that the form works with an A+ grade and no comment."""
        form = LinkGradeForm(data={"grade": "A+", "comment": ""})

        self.assertTrue(form.is_valid())

    def test_form_invalid_lower_grade_no_comment(self):
        """Test that the form requires a comment for grades below A."""
        form = LinkGradeForm(data={"grade": "B+", "comment": ""})

        self.assertFalse(form.is_valid())
        self.assertIn("comment", form.errors)

    def test_form_empty_data(self):
        """Test that the form correctly validates required fields."""
        form = LinkGradeForm(data={})

        self.assertFalse(form.is_valid())
        self.assertIn("grade", form.errors)


class GradeableLinkViewsTest(TestCase):
    """Test cases for the gradeable link views."""

    def setUp(self):
        # Create a test user and a grader
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpassword")

        self.grader = User.objects.create_user(username="grader", email="grader@example.com", password="graderpass")

        # Create a test link
        self.link = GradeableLink.objects.create(
            title="Test Link",
            url="https://example.com/test",
            description="This is a test link",
            user=self.user,
            link_type="article",
        )

        # Set up the test client
        self.client = Client()

    def test_link_list_view(self):
        """Test that the link list view works."""
        response = self.client.get(reverse("gradeable_link_list"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "grade_links/link_list.html")
        self.assertContains(response, "Test Link")

    def test_link_detail_view(self):
        """Test that the link detail view works."""
        response = self.client.get(reverse("gradeable_link_detail", args=[self.link.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "grade_links/link_detail.html")
        self.assertContains(response, "Test Link")
        self.assertContains(response, "https://example.com/test")

    def test_link_create_view_unauthenticated(self):
        """Test that unauthenticated users can't access the create view."""
        response = self.client.get(reverse("gradeable_link_create"))

        # Should redirect to login page
        self.assertRedirects(response, f"{reverse('account_login')}?next={reverse('gradeable_link_create')}")

    def test_link_create_view_authenticated(self):
        """Test that authenticated users can access the create view."""
        self.client.login(username="testuser", password="testpassword")
        response = self.client.get(reverse("gradeable_link_create"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "grade_links/submit_link.html")

    def test_link_create_submission(self):
        """Test that users can submit links."""
        self.client.login(username="testuser", password="testpassword")

        response = self.client.post(
            reverse("gradeable_link_create"),
            {
                "title": "New Test Link",
                "url": "https://example.com/newtest",
                "description": "This is a new test link",
                "link_type": "project",
            },
        )

        # Should redirect to list view after successful submission
        self.assertRedirects(response, reverse("gradeable_link_list"))

        # Check that the link was created
        self.assertTrue(GradeableLink.objects.filter(title="New Test Link").exists())

    def test_grade_link_view_unauthenticated(self):
        """Test that unauthenticated users can't access the grade view."""
        response = self.client.get(reverse("grade_link", args=[self.link.pk]))

        # Should redirect to login page
        self.assertRedirects(response, f"{reverse('account_login')}?next={reverse('grade_link', args=[self.link.pk])}")

    def test_grade_link_view_authenticated(self):
        """Test that authenticated users can access the grade view."""
        self.client.login(username="grader", password="graderpass")
        response = self.client.get(reverse("grade_link", args=[self.link.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "grade_links/grade_link.html")

    def test_grade_link_submission(self):
        """Test that users can submit grades."""
        self.client.login(username="grader", password="graderpass")

        response = self.client.post(
            reverse("grade_link", args=[self.link.pk]), {"grade": "B+", "comment": "Good job, but could be improved."}
        )

        # Should redirect to detail view after successful submission
        self.assertRedirects(response, reverse("gradeable_link_detail", args=[self.link.pk]))

        # Check that the grade was created
        self.assertTrue(
            LinkGrade.objects.filter(
                link=self.link, user=self.grader, grade="B+", comment="Good job, but could be improved."
            ).exists()
        )

    def test_grade_link_submission_invalid(self):
        """Test that the form validation works."""
        self.client.login(username="grader", password="graderpass")

        response = self.client.post(
            reverse("grade_link", args=[self.link.pk]),
            {"grade": "B+", "comment": ""},  # No comment, should be invalid for B+
        )

        self.assertEqual(response.status_code, 200)  # Stays on the same page
        self.assertTemplateUsed(response, "grade_links/grade_link.html")
        self.assertContains(response, "A comment is required for grades below A")

        # Check that no grade was created
        self.assertFalse(LinkGrade.objects.filter(link=self.link, user=self.grader).exists())

    def test_update_existing_grade(self):
        """Test that users can update their existing grades."""
        # First create a grade
        grade = LinkGrade.objects.create(link=self.link, user=self.grader, grade="B", comment="Initial comment")

        self.client.login(username="grader", password="graderpass")

        # Now try to update it
        response = self.client.post(
            reverse("grade_link", args=[self.link.pk]), {"grade": "A-", "comment": "Updated comment"}
        )

        # Should redirect to detail view after successful submission
        self.assertRedirects(response, reverse("gradeable_link_detail", args=[self.link.pk]))

        # Refresh the grade from the database
        grade.refresh_from_db()

        # Check that the grade was updated
        self.assertEqual(grade.grade, "A-")
        self.assertEqual(grade.comment, "Updated comment")

        # Should still be only one grade
        self.assertEqual(LinkGrade.objects.filter(link=self.link, user=self.grader).count(), 1)

    def test_template_container_alignment(self):
        """Test that templates have proper container alignment classes."""
        # Test list view template
        response = self.client.get(reverse("gradeable_link_list"))
        self.assertContains(response, "max-w-6xl mx-auto px-4 sm:px-6")

        # Test detail view template
        response = self.client.get(reverse("gradeable_link_detail", args=[self.link.pk]))
        self.assertContains(response, "max-w-6xl mx-auto px-4 sm:px-6")

        # Test grade submission view template (login required)
        self.client.login(username="grader", password="graderpass")
        response = self.client.get(reverse("grade_link", args=[self.link.pk]))
        self.assertContains(response, "max-w-6xl mx-auto px-4 sm:px-6")

        # Test link creation view template
        response = self.client.get(reverse("gradeable_link_create"))
        self.assertContains(response, "max-w-6xl mx-auto px-4 sm:px-6")

    def test_grade_distribution_visualization(self):
        """Test grade distribution visualization in detail view."""
        # Create grades to have a distribution
        LinkGrade.objects.create(link=self.link, user=self.grader, grade="A", comment="Great work!")

        user2 = User.objects.create_user(username="grader2", email="grader2@example.com", password="password2")

        LinkGrade.objects.create(link=self.link, user=user2, grade="B", comment="Good work but needs improvements")

        # Test detail view with grade distribution
        response = self.client.get(reverse("gradeable_link_detail", args=[self.link.pk]))

        # Check that grade distribution visualization elements are present
        self.assertContains(response, "Grade Distribution")
        self.assertContains(response, "bg-green-100")  # A grade styling
        self.assertContains(response, "bg-blue-100")  # B grade styling

    def test_grade_meter_in_grade_form(self):
        """Test that grade meter is present in the grade submission form."""
        self.client.login(username="grader", password="graderpass")
        response = self.client.get(reverse("grade_link", args=[self.link.pk]))

        # Check that grade meter elements are present
        self.assertContains(response, "grade-meter")
        self.assertContains(response, 'id="grade-value-display"')
        self.assertContains(response, 'id="numeric-grade-display"')

    def test_grading_criteria_guide(self):
        """Test that grading criteria guide is present in the grade form."""
        self.client.login(username="grader", password="graderpass")
        response = self.client.get(reverse("grade_link", args=[self.link.pk]))

        # Check that grading criteria elements are present
        self.assertContains(response, 'id="grading-criteria"')
        self.assertContains(response, "Grading Criteria Guide")
        self.assertContains(response, "Exceptional (4.3)")
        self.assertContains(response, "Excellent (4.0)")

    def test_comment_suggestions(self):
        """Test that comment suggestions are present in the grade form."""
        self.client.login(username="grader", password="graderpass")
        response = self.client.get(reverse("grade_link", args=[self.link.pk]))

        # Check that comment suggestion elements are present
        self.assertContains(response, 'id="comment-suggestions"')
        self.assertContains(response, 'id="show-suggestions-btn"')
        self.assertContains(response, "Show comment suggestions")

    def test_confirmation_modal(self):
        """Test that confirmation modal is present in the grade form."""
        self.client.login(username="grader", password="graderpass")
        response = self.client.get(reverse("grade_link", args=[self.link.pk]))

        # Check that confirmation modal elements are present
        self.assertContains(response, 'id="confirmation-modal"')
        self.assertContains(response, 'id="cancel-btn"')
        self.assertContains(response, 'id="confirm-submit-btn"')
        self.assertContains(response, "Submit Grade?")

    def test_accessibility_features(self):
        """Test that accessibility features are present in templates."""
        # Test grade form view
        self.client.login(username="grader", password="graderpass")
        response = self.client.get(reverse("grade_link", args=[self.link.pk]))

        # Check aria attributes and roles
        self.assertContains(response, "aria-label")
        self.assertContains(response, "aria-hidden")
        self.assertContains(response, 'aria-current="page"')

        # Check for focus states in JS
        self.assertContains(response, "focus-within:ring-2")

        # Test detail view for accessibility features
        response = self.client.get(reverse("gradeable_link_detail", args=[self.link.pk]))
        self.assertContains(response, 'aria-label="Breadcrumb"')

    def test_responsive_layout(self):
        """Test that responsive layout classes are present in templates."""
        # Test detail view
        response = self.client.get(reverse("gradeable_link_detail", args=[self.link.pk]))

        # Check responsive grid layout
        self.assertContains(response, "grid grid-cols-1 lg:grid-cols-3")
        self.assertContains(response, "lg:col-span-2")

        # Check responsive flex layout
        self.assertContains(response, "flex items-center")
        self.assertContains(response, "md:flex-row")

        # Test grade form view
        self.client.login(username="grader", password="graderpass")
        response = self.client.get(reverse("grade_link", args=[self.link.pk]))

        # Check responsive grid layout for grade options
        self.assertContains(response, "grid-cols-3 sm:grid-cols-4 md:grid-cols-6")

    def test_character_counter(self):
        """Test that character counter is present in the grade form."""
        self.client.login(username="grader", password="graderpass")
        response = self.client.get(reverse("grade_link", args=[self.link.pk]))

        # Check character counter
        self.assertContains(response, 'id="character-counter"')
        self.assertContains(response, "characters")
