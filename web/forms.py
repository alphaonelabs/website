import re
from typing import ClassVar
from urllib.parse import parse_qs, urlparse

import bleach
from allauth.account.forms import LoginForm, SignupForm
from captcha.fields import CaptchaField
from cryptography.fernet import Fernet
from django import forms
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import IntegrityError
from django.forms.widgets import URLInput
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from markdownx.fields import MarkdownxFormField

from .models import (
    Achievement,
    Avatar,
    BlogPost,
    ChallengeSubmission,
    Course,
    CourseMaterial,
    EducationalVideo,
    ForumCategory,
    Goods,
    GradeableLink,
    LinkGrade,
    Meme,
    NotificationPreference,
    PeerChallenge,
    PeerChallengeInvitation,
    ProductImage,
    Profile,
    ProgressTracker,
    Quiz,
    QuizOption,
    QuizQuestion,
    Review,
    SelfCheckin,
    Session,
    SessionFeedback,
    SessionSurvey,
    Storefront,
    StudyGroup,
    Subject,
    SuccessStory,
    Survey,
    TeamGoal,
    TeamGoalMember,
    TeamInvite,
    VideoRequest,
    VirtualClassroom,
    VirtualClassroomCustomization,
    WaitingRoom,
)
from .referrals import handle_referral
from .widgets import (
    TailwindCaptchaTextInput,
    TailwindCheckboxInput,
    TailwindDateTimeInput,
    TailwindEmailInput,
    TailwindFileInput,
    TailwindInput,
    TailwindNumberInput,
    TailwindSelect,
    TailwindTextarea,
)

__all__ = [
    "UserRegistrationForm",
    "ProfileForm",
    "ChallengeSubmissionForm",
    "CourseCreationForm",
    "CourseForm",
    "PeerChallengeForm",
    "PeerChallengeInvitationForm",
    "SessionForm",
    "ReviewForm",
    "CourseMaterialForm",
    "TeacherSignupForm",
    "ProfileUpdateForm",
    "CustomLoginForm",
    "LearnForm",
    "TeachForm",
    "InviteStudentForm",
    "ForumCategoryForm",
    "ForumTopicForm",
    "BlogPostForm",
    "MessageTeacherForm",
    "VideoRequestForm",
    "FeedbackForm",
    "GoodsForm",
    "StorefrontForm",
    "EducationalVideoForm",
    "ProgressTrackerForm",
    "SuccessStoryForm",
    "TeamGoalForm",
    "TeamInviteForm",
    "MemeForm",
    "QuizForm",
    "QuizQuestionForm",
    "QuizOptionFormSet",
    "TakeQuizForm",
    "AvatarForm",
    "GradeableLinkForm",
    "LinkGradeForm",
    "AwardAchievementForm",
    "StudyGroupForm",
    "SelfCheckinPreForm",
    "SelfCheckinPostForm",
    "SessionFeedbackForm",
    "SessionSurveyForm",
    "SurveyForm",
    "VirtualClassroomForm",
    "VirtualClassroomCustomizationForm",
]

fernet = Fernet(settings.SECURE_MESSAGE_KEY)


class TailwindWidgetMixin:
    """Mixin providing common Tailwind CSS classes for form widgets."""

    @staticmethod
    def get_tailwind_attrs():
        return (
            "w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 "
            "focus:ring-blue-500 bg-white dark:bg-gray-800 text-gray-700 dark:text-white "
            "border-gray-300 dark:border-gray-600 dark:focus:ring-blue-400"
        )


class AccountDeleteForm(forms.Form):
    password = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
        help_text=_("Enter your password to confirm account deletion."),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if not authenticate(username=self.user.username, password=password):
            raise forms.ValidationError(_("Your password was entered incorrectly. Please enter it again."))
        return password


class UserRegistrationForm(SignupForm):
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=TailwindInput(attrs={"placeholder": "First Name"}),
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=TailwindInput(attrs={"placeholder": "Last Name"}),
    )
    is_teacher = forms.BooleanField(
        required=False,
        label="Register as a teacher",
        widget=TailwindCheckboxInput(),
    )
    referral_code = forms.CharField(
        max_length=20,
        required=False,
        widget=TailwindInput(attrs={"placeholder": "Enter referral code"}),
        help_text="Optional - Enter a referral code if you have one",
    )
    how_did_you_hear_about_us = forms.CharField(
        max_length=500,
        required=False,
        widget=TailwindTextarea(
            attrs={"rows": 2, "placeholder": "How did you hear about us? You can enter text or a link."}
        ),
        help_text="Optional - Tell us how you found us. You can enter text or a link.",
    )
    captcha = CaptchaField(widget=TailwindCaptchaTextInput)
    # NEW: Add radio buttons for profile visibility.
    is_profile_public = forms.TypedChoiceField(
        required=True,
        choices=(("True", "Public"), ("False", "Private")),
        coerce=lambda x: x == "True",  # Convert string to Boolean.
        widget=forms.RadioSelect,
        label="Profile Visibility",
        help_text="Select whether your profile details will be public or private.",
    )

    def __init__(self, *args, **kwargs):
        request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        # Update email field widget.
        self.fields["email"].widget = TailwindEmailInput(
            attrs={
                "placeholder": "your.email@example.com",
                "value": self.initial.get("email", ""),
            }
        )
        # Update password field widget.
        self.fields["password1"].widget = TailwindInput(
            attrs={
                "type": "password",
                "placeholder": "Choose a secure password",
                "class": (
                    "block w-full border rounded p-2 focus:outline-none focus:ring-2 "
                    "focus:ring-teal-300 dark:focus:ring-teal-800 bg-white dark:bg-gray-800 "
                    "border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white"
                ),
            }
        )

        # Handle referral code from POST data or session.
        if self.data:  # If form was submitted.
            referral_code = self.data.get("referral_code")
            if referral_code:
                self.fields["referral_code"].initial = referral_code
        elif request and request.session.get("referral_code"):
            referral_code = request.session.get("referral_code")
            self.fields["referral_code"].initial = referral_code
            self.initial["referral_code"] = referral_code

        # Preserve values on form errors.
        if self.data:
            for field_name in ["first_name", "last_name", "email", "referral_code", "username"]:
                if field_name in self.data and field_name in self.fields:
                    self.fields[field_name].widget.attrs["value"] = self.data[field_name]

            # Initialize how_did_you_hear_about_us if provided
            if "how_did_you_hear_about_us" in self.data:
                self.fields["how_did_you_hear_about_us"].initial = self.data["how_did_you_hear_about_us"]

        # Set a default for the new field if not provided.
        if "is_profile_public" not in self.initial:
            self.initial["is_profile_public"] = "False"  # Default to Private.

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if username:
            try:
                User.objects.get(username=username)
                raise forms.ValidationError("This username is already taken. Please choose a different one.")
            except User.DoesNotExist:
                return username
        return username

    def clean_email(self):
        email = self.cleaned_data.get("email", "").lower()
        if email:
            from allauth.account.utils import filter_users_by_email

            users = filter_users_by_email(email)
            if users:
                raise forms.ValidationError(
                    "There was a problem with your signup. Please try again with a different email address or login."
                )
        return email

    def clean_referral_code(self):
        referral_code = self.cleaned_data.get("referral_code")
        if referral_code:
            if not Profile.objects.filter(referral_code=referral_code).exists():
                raise forms.ValidationError("Invalid referral code. Please check and try again.")
        return referral_code

    def save(self, request):
        # Create the user using Allauth's default behavior.
        try:
            user = super().save(request)
        except IntegrityError:
            raise forms.ValidationError("This username is already taken. Please choose a different one.")
        except ValueError:
            raise forms.ValidationError(
                "There was a problem with your signup. Please try again with a different email address or login."
            )

        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.save()

        # Update the profile with the new radio button value.
        user.profile.is_profile_public = self.cleaned_data.get("is_profile_public")
        # Save how_did_you_hear_about_us
        user.profile.how_did_you_hear_about_us = self.cleaned_data.get("how_did_you_hear_about_us", "")
        user.profile.save()

        # Update teacher flag if provided.
        if self.cleaned_data.get("is_teacher"):
            user.profile.is_teacher = True
            user.profile.save()

        # Handle referral code if provided.
        referral_code = self.cleaned_data.get("referral_code")
        if referral_code:
            handle_referral(user, referral_code)

        # Ensure email verification is sent
        from allauth.account.models import EmailAddress

        email_address = EmailAddress.objects.get_for_user(user, user.email)
        if not email_address.verified:
            email_address.send_confirmation(request)

        return user


class TailwindInput(forms.widgets.Input, TailwindWidgetMixin):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("attrs", {}).update(
            {
                "class": self.get_tailwind_attrs(),
            }
        )
        super().__init__(*args, **kwargs)


class TailwindURLInput(URLInput, TailwindWidgetMixin):
    # This widget, subclassing URLInput, ensures input type="url"
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("attrs", {}).update(
            {
                "class": self.get_tailwind_attrs(),
            }
        )
        super().__init__(*args, **kwargs)


class AwardAchievementForm(forms.Form):
    student = forms.ModelChoiceField(
        queryset=User.objects.none(),
        empty_label="Select a student",
        widget=TailwindSelect(),
    )

    achievement_type = forms.ChoiceField(choices=Achievement.TYPES, widget=TailwindSelect())

    course = forms.ModelChoiceField(
        queryset=Course.objects.all(),
        empty_label="Select a course (optional)",
        required=False,
        widget=TailwindSelect(),
    )

    title = forms.CharField(max_length=100, widget=TailwindInput())

    description = forms.CharField(
        widget=TailwindTextarea(attrs={"rows": 3}),
        required=False,
    )

    badge_icon = forms.ChoiceField(
        choices=Achievement.BADGE_ICONS,
        widget=TailwindSelect(),
    )

    def __init__(self, *args, **kwargs):
        teacher = kwargs.pop("teacher", None)
        super().__init__(*args, **kwargs)

        if teacher:
            teacher_courses = Course.objects.filter(teacher=teacher)
            student_ids = []
            for course in teacher_courses:
                student_ids.extend(course.enrollments.filter(status="approved").values_list("student_id", flat=True))

            self.fields["student"].queryset = User.objects.filter(id__in=student_ids)
            self.fields["course"].queryset = teacher_courses

    def clean(self):
        cleaned_data = super().clean()
        if self.fields["student"].queryset.count() == 0:
            raise forms.ValidationError("You don't have any students in your courses who can receive achievements.")
        return cleaned_data


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ("bio", "expertise")
        widgets = {
            "bio": TailwindTextarea(attrs={"rows": 4}),
            "expertise": TailwindInput(attrs={"placeholder": "Your areas of expertise"}),
        }


class CourseCreationForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = (
            "title",
            "description",
            "image",
            "learning_objectives",
            "prerequisites",
            "price",
            "allow_individual_sessions",
            "max_students",
            "subject",
            "level",
            "tags",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "image": TailwindFileInput(
                attrs={
                    "accept": "image/*",
                    "help_text": "Course image must be 300x150 pixels",
                }
            ),
            "learning_objectives": forms.Textarea(attrs={"rows": 4}),
            "prerequisites": forms.Textarea(attrs={"rows": 4}),
            "allow_individual_sessions": TailwindCheckboxInput(
                attrs={"help_text": ("Allow students to register for individual sessions")}
            ),
            "tags": forms.TextInput(attrs={"placeholder": "Enter comma-separated tags"}),
        }

    def clean_price(self):
        price = self.cleaned_data.get("price")
        if price < 0:
            raise forms.ValidationError("Price must be greater than or equal to zero")
        return price

    def clean_max_students(self):
        max_students = self.cleaned_data.get("max_students")
        if max_students <= 0:
            msg = "Maximum number of students must be greater than zero"
            raise forms.ValidationError(msg)
        return max_students

    def clean_title(self):
        title = self.cleaned_data.get("title")
        if not title:
            raise forms.ValidationError("Title is required")

        # Check if title contains valid characters for slugification
        if not re.match(r"^[\w\s-]+$", title):
            raise forms.ValidationError("Title can only contain letters, numbers, spaces, and hyphens")

        # Check if a course with this slug already exists
        slug = slugify(title)
        if Course.objects.filter(slug=slug).exists():
            raise forms.ValidationError("A course with a similar title already exists.")

        return title


class CourseForm(forms.ModelForm):
    description = MarkdownxFormField(
        label="Description", help_text="Use markdown for formatting. You can use **bold**, *italic*, lists, etc."
    )
    learning_objectives = MarkdownxFormField(
        label="Learning Objectives",
        help_text="Use markdown for formatting. List your objectives using - or * for bullet points.",
    )
    prerequisites = MarkdownxFormField(
        label="Prerequisites",
        help_text="Use markdown for formatting. List prerequisites using - or * for bullet points.",
        required=False,
    )

    class Meta:
        model = Course
        fields = [
            "title",
            "description",
            "image",
            "learning_objectives",
            "prerequisites",
            "price",
            "allow_individual_sessions",
            "invite_only",
            "max_students",
            "subject",
            "level",
            "tags",
        ]
        widgets = {
            "title": TailwindInput(),
            "description": TailwindTextarea(attrs={"rows": 4}),
            "image": TailwindFileInput(
                attrs={
                    "accept": "image/*",
                    "help_text": "Course image must be 300x150 pixels",
                }
            ),
            "learning_objectives": TailwindTextarea(attrs={"rows": 4}),
            "prerequisites": TailwindTextarea(attrs={"rows": 4}),
            "price": TailwindNumberInput(attrs={"min": "0", "step": "0.01"}),
            "allow_individual_sessions": TailwindCheckboxInput(
                attrs={"help_text": ("Allow students to register for individual sessions")}
            ),
            "invite_only": TailwindCheckboxInput(
                attrs={"help_text": ("If enabled, students can only enroll with an invitation")}
            ),
            "max_students": TailwindNumberInput(attrs={"min": "1"}),
            "subject": TailwindSelect(),
            "level": TailwindSelect(),
            "tags": TailwindInput(attrs={"placeholder": "Enter comma-separated tags"}),
        }

    def clean_max_students(self):
        max_students = self.cleaned_data.get("max_students")
        if max_students <= 0:
            msg = "Maximum number of students must be greater than zero"
            raise forms.ValidationError(msg)
        return max_students


class SessionForm(forms.ModelForm):
    class Meta:
        model = Session
        fields = [
            "title",
            "description",
            "start_time",
            "end_time",
            "is_virtual",
            "meeting_link",
            "location",
            "price",
            "enable_rollover",
            "rollover_pattern",
            "teaching_style",
        ]
        widgets = {
            "title": TailwindInput(),
            "description": TailwindTextarea(attrs={"rows": 4}),
            "start_time": TailwindDateTimeInput(),
            "end_time": TailwindDateTimeInput(),
            "is_virtual": TailwindCheckboxInput(),
            "meeting_link": TailwindInput(attrs={"type": "url"}),
            "location": TailwindInput(),
            "teaching_style": TailwindSelect(),
            "price": TailwindNumberInput(
                attrs={
                    "min": "0",
                    "step": "0.01",
                    "help_text": ("Price for individual session registration"),
                }
            ),
            "enable_rollover": TailwindCheckboxInput(),
            "rollover_pattern": TailwindSelect(),
        }
        help_texts = {
            "start_time": "Click to select the session start date and time",
            "end_time": "Click to select the session end date and time",
            "enable_rollover": "Enable automatic date rollover if no students are enrolled",
            "rollover_pattern": "How often to roll over the session dates",
        }

    def clean(self):
        cleaned_data = super().clean()
        is_virtual = cleaned_data.get("is_virtual")
        meeting_link = cleaned_data.get("meeting_link")
        location = cleaned_data.get("location")
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")
        price = cleaned_data.get("price")

        if start_time and end_time and end_time <= start_time:
            self.add_error("end_time", "End time must be after start time.")

        if is_virtual and not meeting_link:
            msg = "Meeting link is required for virtual sessions."
            self.add_error("meeting_link", msg)
        elif not is_virtual and not location:
            msg = "Location is required for in-person sessions."
            self.add_error("location", msg)

        if price is not None and price < 0:
            self.add_error("price", "Price cannot be negative.")

        return cleaned_data


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ("rating", "comment")
        widgets = {
            "rating": TailwindNumberInput(attrs={"min": "1", "max": "5"}),
            "comment": TailwindTextarea(attrs={"rows": 4}),
        }


class CourseMaterialForm(forms.ModelForm):
    class Meta:
        model = CourseMaterial
        fields = (
            "title",
            "description",
            "material_type",
            "file",
            "external_url",
            "session",
            "is_downloadable",
            "order",
        )
        widgets = {
            "title": TailwindInput(),
            "description": TailwindTextarea(attrs={"rows": 3}),
            "material_type": TailwindSelect(),
            "file": TailwindFileInput(),
            "external_url": TailwindInput(attrs={"placeholder": "Enter video URL"}),  # Add widget for external_url
            "session": TailwindSelect(),
            "is_downloadable": TailwindCheckboxInput(),
            "order": TailwindNumberInput(attrs={"min": 0}),
        }
        labels = {
            "external_url": "External URL",  # Update label
        }

    def __init__(self, *args, course=None, **kwargs):
        super().__init__(*args, **kwargs)
        if course:
            self.fields["session"].queryset = course.sessions.all()


class TeacherSignupForm(forms.Form):
    email = forms.EmailField(widget=TailwindEmailInput())
    username = forms.CharField(
        max_length=150,
        widget=TailwindInput(attrs={"placeholder": "Choose a username"}),
        help_text="This will be your unique identifier on the platform.",
    )
    subject = forms.CharField(max_length=100, widget=TailwindInput())
    captcha = CaptchaField(widget=TailwindCaptchaTextInput)

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken. Please choose a different one.")
        return username

    def save(self):
        email = self.cleaned_data["email"]
        username = self.cleaned_data["username"]
        subject_name = self.cleaned_data["subject"]

        random_password = get_random_string(length=30)
        try:
            user = User.objects.create_user(username=username, email=email, password=random_password)
        except IntegrityError:
            raise forms.ValidationError("This username is already taken. Please try again with a different username.")

        # Set user as teacher
        profile = user.profile
        profile.is_teacher = True
        profile.save()

        # Create subject
        subject, created = Subject.objects.get_or_create(
            name=subject_name,
            defaults={
                "slug": slugify(subject_name),
                "description": f"Courses about {subject_name}",
            },
        )

        return user, subject


class ProfileUpdateForm(forms.ModelForm):
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=TailwindInput(),
        help_text="This is your public username that will be visible to other users",
    )
    first_name = forms.CharField(
        max_length=30, required=False, widget=TailwindInput(), help_text="Your real name will not be shown publicly"
    )
    last_name = forms.CharField(
        max_length=30, required=False, widget=TailwindInput(), help_text="Your real name will not be shown publicly"
    )
    email = forms.EmailField(
        required=True, widget=TailwindEmailInput(), help_text="Your email will not be shown publicly"
    )
    bio = forms.CharField(
        required=False,
        widget=TailwindTextarea(attrs={"rows": 4}),
        help_text="Tell us about yourself - this will be visible if your profile is public",
    )
    expertise = forms.CharField(
        required=False,
        widget=TailwindInput(),
        help_text=(
            "List your areas of expertise (e.g. Python, Machine Learning, Web Development) - "
            "this will be visible if your profile is public"
        ),
    )
    avatar = forms.ImageField(
        required=False,
        widget=TailwindFileInput(),
        help_text="Upload a profile picture (will be cropped to a square and resized to 200x200 pixels)",
    )
    is_profile_public = forms.TypedChoiceField(
        required=True,
        choices=(("True", "Public"), ("False", "Private")),
        coerce=lambda x: x == "True",
        widget=forms.RadioSelect,
        help_text="Select whether your profile details are public or private.",
    )
    discord_username = forms.CharField(
        max_length=50,
        required=False,
        widget=TailwindInput(),
        help_text="Discord username (visible if profile is public)",
    )
    slack_username = forms.CharField(
        max_length=50, required=False, widget=TailwindInput(), help_text="Slack username (visible if profile is public)"
    )
    github_username = forms.CharField(
        max_length=50,
        required=False,
        widget=TailwindInput(),
        help_text="GitHub username (visible if profile is public)",
    )

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance:
            try:
                profile = self.instance.profile
                self.fields["bio"].initial = profile.bio
                self.fields["expertise"].initial = profile.expertise
                self.fields["discord_username"].initial = profile.discord_username
                self.fields["slack_username"].initial = profile.slack_username
                self.fields["github_username"].initial = profile.github_username
                # Set initial value as a string.
                self.initial["is_profile_public"] = "True" if profile.is_profile_public else "False"
            except Profile.DoesNotExist:
                pass

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.exclude(pk=self.instance.pk).filter(username=username).exists():
            raise forms.ValidationError("This username is already taken. Please choose a different one.")
        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            profile, created = Profile.objects.get_or_create(user=user)
            profile.bio = self.cleaned_data["bio"]
            profile.expertise = self.cleaned_data["expertise"]
            if self.cleaned_data.get("avatar"):
                profile.avatar = self.cleaned_data["avatar"]

            # Get the is_profile_public value and ensure it's a boolean
            is_public = self.cleaned_data.get("is_profile_public")
            profile.discord_username = self.cleaned_data["discord_username"]
            profile.slack_username = self.cleaned_data["slack_username"]
            profile.github_username = self.cleaned_data["github_username"]
            profile.is_profile_public = is_public
            profile.save()
        return user


class CustomLoginForm(LoginForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["login"].widget.attrs.update(
            {
                "class": (
                    "block w-full rounded-md border-0 py-2 px-4 "
                    "text-gray-900 dark:text-white shadow-sm "
                    "ring-1 ring-inset ring-gray-300 "
                    "dark:ring-gray-600 "
                    "placeholder:text-gray-400 "
                    "focus:ring-2 focus:ring-inset "
                    "focus:ring-orange-500 dark:bg-gray-700 "
                    "sm:text-base sm:leading-6"
                )
            }
        )
        self.fields["password"].widget.attrs.update(
            {
                "class": (
                    "block w-full rounded-md border-0 py-2 px-4 "
                    "text-gray-900 dark:text-white shadow-sm "
                    "ring-1 ring-inset ring-gray-300 "
                    "dark:ring-gray-600 "
                    "placeholder:text-gray-400 "
                    "focus:ring-2 focus:ring-inset "
                    "focus:ring-orange-500 dark:bg-gray-700 "
                    "sm:text-base sm:leading-6 pr-10"
                )
            }
        )
        self.fields["remember"].widget.attrs.update(
            {
                "class": (
                    "h-4 w-4 text-orange-500 "
                    "focus:ring-orange-500 "
                    "border-gray-300 dark:border-gray-600 "
                    "rounded cursor-pointer"
                )
            }
        )

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data is None:
            return {}

        # Check if user exists and can log in
        if "login" in cleaned_data:
            email = cleaned_data["login"]
            try:
                User.objects.get(email=email)
            except User.DoesNotExist:
                raise forms.ValidationError(
                    "No account found with this email address. Please check the email or sign up."
                )

        return cleaned_data


class EducationalVideoForm(forms.ModelForm):
    """
    Form for creating and editing educational videos.
    Validates that video URLs are from YouTube or Vimeo.
    """

    # Make description optional in the form
    description = forms.CharField(
        required=False,
        widget=TailwindTextarea(
            attrs={
                "rows": 4,
                "placeholder": "Describe what viewers will learn from this video (optional)",
            }
        ),
        help_text="Optional – what this video is about",
    )

    class Meta:
        model = EducationalVideo
        fields = ["title", "description", "video_url", "category"]
        widgets = {
            "title": TailwindInput(attrs={"placeholder": "Video title"}),
            "video_url": TailwindInput(attrs={"placeholder": "YouTube or Vimeo URL", "type": "url"}),
            "category": TailwindSelect(
                attrs={
                    "class": (
                        "w-full px-4 py-2 border border-gray-300 dark:border-gray-600"
                        " rounded-lg focus:ring-2 focus:ring-blue-500"
                    )
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Order subjects by 'order' first, then alphabetically by 'name'
        self.fields["category"].queryset = Subject.objects.all().order_by("order", "name")

    def clean_video_url(self):
        url = self.cleaned_data.get("video_url", "").strip()
        if not url:
            return url  # let required validation handle empties

        parsed = urlparse(url)
        host = parsed.netloc.lower()

        # YouTube validation
        if host == "youtube.com" or host == "www.youtube.com":
            # Standard YouTube URLs with ?v= parameter
            qs = parse_qs(parsed.query)
            vid = qs.get("v", [""])[0]
            if len(vid) == 11 and re.match(r"^[A-Za-z0-9_-]{11}$", vid):
                return url

            # YouTube embed URLs like /embed/VIDEO_ID
            if parsed.path.startswith("/embed/"):
                vid = parsed.path[7:]  # Remove "/embed/"
                if len(vid) == 11 and re.match(r"^[A-Za-z0-9_-]{11}$", vid):
                    return url

        # YouTube short URL validation
        if host == "youtu.be":
            vid = parsed.path.lstrip("/")
            if len(vid) == 11 and re.match(r"^[A-Za-z0-9_-]{11}$", vid):
                return url

        # Vimeo validation
        if host == "vimeo.com" or host == "www.vimeo.com":
            path_parts = parsed.path.lstrip("/").split("/")
            vid = path_parts[-1]  # Get the last part of the path

            # Handle both /VIDEO_ID and /video/VIDEO_ID formats
            if vid.isdigit() and len(vid) >= 8:
                return url

        raise forms.ValidationError("Please enter a valid YouTube or Vimeo URL")


class SuccessStoryForm(forms.ModelForm):
    content = MarkdownxFormField(
        label="Content", help_text="Use markdown for formatting. You can use **bold**, *italic*, lists, etc."
    )

    class Meta:
        model = SuccessStory
        fields = ["title", "content", "excerpt", "featured_image", "status"]
        widgets = {
            "title": TailwindInput(attrs={"placeholder": "Your success story title"}),
            "excerpt": TailwindTextarea(
                attrs={"rows": 3, "placeholder": "A brief summary of your success story (optional)"}
            ),
            "featured_image": TailwindFileInput(
                attrs={"accept": "image/*", "help_text": "Featured image for your success story (optional)"}
            ),
            "status": TailwindSelect(),
        }


class LearnForm(forms.ModelForm):
    """Form for creating and editing waiting rooms."""

    class Meta:
        model = WaitingRoom
        fields = ["title", "description", "subject", "topics"]

        widgets = {
            "title": TailwindInput(attrs={"placeholder": "What would you like to learn?"}),
            "description": TailwindTextarea(attrs={"rows": 4, "placeholder": "Describe what you want to learn"}),
            "subject": TailwindInput(attrs={"placeholder": "Main subject (e.g., Mathematics, Programming)"}),
            "topics": TailwindInput(
                attrs={"placeholder": "e.g., Python, Machine Learning, Data Science", "class": "tag-input"}
            ),
        }
        help_texts = {
            "title": "Give your waiting room a descriptive title",
            "subject": "The main subject area for this waiting room",
            "topics": "Enter topics separated by commas",
        }

    def clean_topics(self):
        """Validate and clean the topics field."""
        topics = self.cleaned_data.get("topics")
        if not topics:
            raise forms.ValidationError("Please enter at least one topic.")

        # Ensure we have at least one non-empty topic after splitting
        topic_list = [t.strip() for t in topics.split(",") if t.strip()]
        if not topic_list:
            raise forms.ValidationError("Please enter at least one valid topic.")

        return topics


class TeachForm(forms.Form):
    """Form for creating course draft by both authenticated and unauthenticated users."""

    course_title = forms.CharField(
        max_length=200,
        label="Course Title",
        widget=TailwindInput(
            attrs={
                "placeholder": "Enter your course title",
                "class": "block w-full border rounded p-2 focus:outline-none focus:ring-2 focus:ring-indigo-500",
            }
        ),
    )
    course_image = forms.ImageField(
        required=True,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "gif"])],
        widget=TailwindFileInput(
            attrs={
                "accept": "image/*",
                "help_text": "Upload a course image (required)",
                "class": "block w-full border rounded p-2 focus:outline-none focus:ring-2 focus:ring-indigo-500",
            }
        ),
    )
    course_description = forms.CharField(
        label="Course Description",
        widget=TailwindTextarea(
            attrs={
                "rows": 4,
                "placeholder": "Describe what your course will cover...",
            }
        ),
        help_text="Provide a detailed description of your course.",
    )
    preferred_session_times = forms.DateTimeField(
        label="Preferred Session Time",
        widget=TailwindDateTimeInput(),
        help_text="Select preferred time for your course sessions.",
        required=False,
    )
    flexible_timing = forms.BooleanField(
        label="Flexible Timing",
        required=False,
        widget=TailwindCheckboxInput(
            attrs={
                "class": "h-4 w-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500",
            }
        ),
        help_text="Check if you're open to scheduling sessions at various times.",
    )
    email = forms.EmailField(
        label="Email Address",
        widget=TailwindInput(
            attrs={
                "placeholder": "Your email address",
                "class": "block w-full border rounded p-2 focus:outline-none focus:ring-2 focus:ring-indigo-500",
            }
        ),
        help_text="We'll use this to create your account or link to an existing one.",
    )
    captcha = CaptchaField(
        widget=TailwindCaptchaTextInput(
            attrs={"class": "block w-full border rounded p-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"}
        )
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        # If the user is authenticated, remove email and captcha fields
        if user and user.is_authenticated:
            del self.fields["email"]
            del self.fields["captcha"]

    def clean_course_title(self):
        """Validate and clean the course_title field."""
        title = self.cleaned_data.get("course_title")
        # Validate title contains only valid characters
        if not re.match(r"^[\w\s-]+$", title):
            raise forms.ValidationError("Title can only contain letters, numbers, spaces, and hyphens")

        return title

    def clean_preferred_session_times(self):
        """Validate the preferred_session_times."""
        preferred_time = self.cleaned_data.get("preferred_session_times")
        if preferred_time and preferred_time < timezone.now():
            raise forms.ValidationError("Preferred session time cannot be in the past.")
        return preferred_time

    def clean_course_image(self):
        """Validate and clean the course_image field."""
        image = self.cleaned_data.get("course_image")
        if image:
            max_size = 5 * 1024 * 1024  # 5MB
            if image.size > max_size:
                raise forms.ValidationError("Image must be less than 5MB")
        return image


class InviteStudentForm(forms.Form):
    email = forms.EmailField(
        label="Student's Email",
        widget=forms.EmailInput(
            attrs={
                "class": (
                    "w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 "
                    "bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 "
                    "focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400 focus:border-transparent"
                ),
                "placeholder": "Enter student's email address",
            }
        ),
    )
    message = forms.CharField(
        required=False,
        label="Personal Message (optional)",
        widget=forms.Textarea(
            attrs={
                "class": (
                    "w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 "
                    "bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 "
                    "focus:ring-2 focus:ring-indigo-500 dark:focus:ring-indigo-400 focus:border-transparent"
                ),
                "placeholder": "Add a personal message to your invitation",
                "rows": 3,
            }
        ),
    )


class ForumCategoryForm(forms.ModelForm):
    """Form for creating and editing forum categories."""

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get("name")
        if name and not cleaned_data.get("slug"):
            cleaned_data["slug"] = slugify(name)
        return cleaned_data

    class Meta:
        model = ForumCategory
        fields = ["name", "description", "icon", "slug"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": (
                        "w-full border border-gray-300 dark:border-gray-600 rounded p-2 "
                        "focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 "
                        "dark:focus:ring-offset-gray-800 bg-white dark:bg-gray-800"
                    )
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": (
                        "w-full border border-gray-300 dark:border-gray-600 rounded p-2 "
                        "focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 "
                        "dark:focus:ring-offset-gray-800 bg-white dark:bg-gray-800"
                    ),
                    "rows": 4,
                }
            ),
            "icon": forms.TextInput(
                attrs={
                    "class": (
                        "w-full border border-gray-300 dark:border-gray-600 rounded p-2 "
                        "focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 "
                        "dark:focus:ring-offset-gray-800 bg-white dark:bg-gray-800"
                    ),
                    "placeholder": "fa-folder",
                }
            ),
            "slug": forms.TextInput(
                attrs={
                    "class": "w-full border-gray-300 dark:border-gray-600 rounded p-2 bg-gray-200 cursor-not-allowed",
                    "readonly": "readonly",
                }
            ),
        }
        help_texts = {
            "icon": "Enter a Font Awesome icon class (e.g., fa-folder, fa-book, fa-code)",
        }


class PeerChallengeForm(forms.ModelForm):
    """Form for creating and editing peer challenges."""

    class Meta:
        model = PeerChallenge
        fields = ["quiz", "title", "description", "expires_at"]
        widgets = {
            "quiz": TailwindSelect(),
            "title": TailwindInput(attrs={"placeholder": "Challenge title"}),
            "description": TailwindTextarea(attrs={"rows": 3, "placeholder": "Describe your challenge"}),
            "expires_at": TailwindDateTimeInput(attrs={"placeholder": "Expiration date (optional)"}),
        }
        help_texts = {
            "expires_at": "Optional deadline for the challenge",
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show quizzes created by the current user
        if user:
            self.fields["quiz"].queryset = Quiz.objects.filter(creator=user, status="published")


class PeerChallengeInvitationForm(forms.ModelForm):
    """Form for inviting users to a peer challenge."""

    participants = forms.CharField(
        widget=TailwindTextarea(attrs={"rows": 2, "placeholder": "Enter usernames, separated by commas"}),
        help_text="Enter usernames separated by commas",
    )

    class Meta:
        model = PeerChallengeInvitation
        fields = ["message"]
        widgets = {
            "message": TailwindTextarea(attrs={"rows": 3, "placeholder": "Add a personal message to your invitation"}),
        }

    def clean_participants(self):
        participants = self.cleaned_data.get("participants", "")
        if not participants:
            raise forms.ValidationError("You must invite at least one participant")

        usernames = [username.strip() for username in participants.split(",") if username.strip()]
        if not usernames:
            raise forms.ValidationError("You must invite at least one participant")

        from django.contrib.auth.models import User

        # Check if users exist
        found_users = User.objects.filter(username__in=usernames)
        found_usernames = found_users.values_list("username", flat=True)

        # Get missing usernames
        missing = set(usernames) - set(found_usernames)
        if missing:
            raise forms.ValidationError(f"The following users do not exist: {', '.join(missing)}")

        return found_users

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get("name")
        if name:
            cleaned_data["slug"] = slugify(name)
        return cleaned_data


class ForumTopicForm(forms.Form):
    title = forms.CharField(
        max_length=200,
        required=True,
        widget=TailwindInput(
            attrs={
                "class": (
                    "w-full border border-gray-300 dark:border-gray-600 rounded p-2 "
                    "focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 "
                    "dark:focus:ring-offset-gray-800 bg-white dark:bg-gray-800"
                ),
                "placeholder": "Enter your topic title",
            }
        ),
    )
    content = forms.CharField(
        required=True,
        widget=TailwindTextarea(
            attrs={
                "class": (
                    "w-full border border-gray-300 dark:border-gray-600 rounded p-2 "
                    "focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 "
                    "dark:focus:ring-offset-gray-800 bg-white dark:bg-gray-800"
                ),
                "rows": 6,
                "placeholder": "Write your topic content here...",
            }
        ),
    )
    github_issue_url = forms.URLField(
        required=False,
        widget=TailwindURLInput(attrs={"placeholder": "https://github.com/your-org/your-repo/issues/123"}),
        help_text="Link to a related GitHub issue (optional)",
    )
    github_milestone_url = forms.URLField(
        required=False,
        widget=TailwindURLInput(attrs={"placeholder": "https://github.com/your-org/your-repo/milestone/1"}),
        help_text="Link to a related GitHub milestone (optional)",
    )

    def clean_github_issue_url(self):
        url = self.cleaned_data.get("github_issue_url")
        if url and (not url.startswith("https://github.com/") or "/issues/" not in url):
            raise forms.ValidationError("Please enter a valid GitHub issue URL")
        return url

    def clean_github_milestone_url(self):
        url = self.cleaned_data.get("github_milestone_url")
        if url and (not url.startswith("https://github.com/") or "milestone" not in url):
            raise forms.ValidationError("Please enter a valid GitHub milestone URL")
        return url


class AvatarForm(forms.ModelForm):
    """Form for customizing user avatars."""

    class Meta:
        model = Avatar
        fields = [
            "style",
            "background_color",
            "top",
            "eyebrows",
            "eyes",
            "nose",
            "mouth",
            "facial_hair",
            "skin_color",
            "hair_color",
            "accessory",
            "clothing",
            "clothing_color",
        ]
        widgets = {
            "style": TailwindSelect(),
            "background_color": TailwindInput(attrs={"type": "color"}),
            "top": TailwindSelect(),
            "eyebrows": TailwindSelect(),
            "eyes": TailwindSelect(),
            "nose": TailwindSelect(),
            "mouth": TailwindSelect(),
            "facial_hair": TailwindSelect(),
            "skin_color": TailwindSelect(),
            "hair_color": TailwindInput(attrs={"type": "color"}),
            "accessory": TailwindSelect(),
            "clothing": TailwindSelect(),
            "clothing_color": TailwindInput(attrs={"type": "color"}),
        }


class BlogPostForm(forms.ModelForm):
    """Form for creating and editing blog posts."""

    class Meta:
        model = BlogPost
        fields = ["title", "content", "excerpt", "featured_image", "status", "tags"]

        input_classes = (
            "w-full border border-gray-300 dark:border-gray-600 rounded p-2 "
            "focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 "
            "dark:focus:ring-offset-gray-800 bg-white dark:bg-gray-800"
        )

        widgets = {
            "title": forms.TextInput(attrs={"class": input_classes}),
            "content": forms.Textarea(attrs={"class": input_classes, "rows": 10}),
            "excerpt": forms.Textarea(attrs={"class": input_classes, "rows": 3}),
            "tags": forms.TextInput(
                attrs={
                    "class": input_classes,
                    "placeholder": "Enter comma-separated tags",
                }
            ),
            "status": forms.Select(attrs={"class": input_classes}),
        }


class MessageTeacherForm(forms.Form):
    name = forms.CharField(
        widget=TailwindInput(
            attrs={
                "class": (
                    "w-full px-4 py-2 border border-gray-300 dark:border-gray-600 "
                    "rounded-lg focus:ring-2 focus:ring-blue-500"
                )
            }
        ),
    )
    email = forms.EmailField(
        widget=TailwindEmailInput(
            attrs={
                "class": (
                    "w-full px-4 py-2 border border-gray-300 dark:border-gray-600 "
                    "rounded-lg focus:ring-2 focus:ring-blue-500"
                )
            }
        ),
    )
    message = forms.CharField(
        widget=TailwindTextarea(
            attrs={
                "class": (
                    "w-full px-4 py-2 border border-gray-300 dark:border-gray-600 "
                    "rounded-lg focus:ring-2 focus:ring-blue-500"
                ),
                "rows": 5,
            }
        ),
        required=True,
    )
    captcha = CaptchaField(
        required=False,
        widget=TailwindCaptchaTextInput(
            attrs={
                "class": (
                    "w-full px-4 py-2 border border-gray-300 dark:border-gray-600 "
                    "rounded-lg focus:ring-2 focus:ring-blue-500"
                )
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        # If the user is authenticated, remove name, email, and captcha fields.
        if user and user.is_authenticated:
            del self.fields["name"]
            del self.fields["email"]
            del self.fields["captcha"]

    def clean_message(self):
        """
        Encrypts the message field using Fernet before processing.
        Returns the encrypted message as a decoded string.
        """
        message = self.cleaned_data.get("message")
        if not message:
            raise ValidationError("Message cannot be empty.")
        try:
            encrypted_message = fernet.encrypt(message.encode("utf-8"))
            return encrypted_message.decode("utf-8")
        except Exception as e:
            raise ValidationError("Encryption failed: " + str(e))


class FeedbackForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        required=False,
        widget=TailwindInput(
            attrs={
                "placeholder": "Your name (optional)",
                "class": (
                    "w-full px-4 py-2 border border-gray-300 dark:border-gray-600 "
                    "rounded-lg focus:ring-2 focus:ring-blue-500"
                ),
            }
        ),
    )
    email = forms.EmailField(
        required=False,
        widget=TailwindEmailInput(
            attrs={
                "placeholder": "Your email (optional)",
                "class": (
                    "w-full px-4 py-2 border border-gray-300 dark:border-gray-600 "
                    "rounded-lg focus:ring-2 focus:ring-blue-500"
                ),
            }
        ),
    )
    description = forms.CharField(
        widget=TailwindTextarea(
            attrs={
                "placeholder": "Your feedback...",
                "rows": 4,
                "class": (
                    "w-full px-4 py-2 border border-gray-300 dark:border-gray-600 "
                    "rounded-lg focus:ring-2 focus:ring-blue-500"
                ),
            }
        ),
        required=True,
    )
    captcha = CaptchaField(widget=TailwindCaptchaTextInput)


class ChallengeSubmissionForm(forms.ModelForm):
    class Meta:
        model = ChallengeSubmission
        fields = ["submission_text"]
        widgets = {
            "submission_text": forms.Textarea(
                attrs={"rows": 5, "placeholder": "Describe your results or reflections..."}
            ),
        }


class TailwindTextarea(forms.widgets.Textarea):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("attrs", {}).update(
            {"class": "w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"}
        )
        super().__init__(*args, **kwargs)


class GoodsForm(forms.ModelForm):
    """Form for creating/updating goods with full validation"""

    class Meta:
        model = Goods
        fields = [
            "name",
            "description",
            "price",
            "discount_price",
            "product_type",
            "stock",
            "file",
            "category",
            "is_available",
        ]
        widgets = {
            "name": TailwindInput(attrs={"placeholder": "Algebra Basics Workbook"}),
            "description": TailwindTextarea(attrs={"rows": 4, "placeholder": "Detailed product description"}),
            "price": forms.NumberInput(attrs={"class": "tailwind-input-class", "min": "0", "step": "0.01"}),
            "discount_price": forms.NumberInput(attrs={"class": "tailwind-input-class", "min": "0", "step": "0.01"}),
            "product_type": forms.Select(attrs={"onchange": "toggleDigitalFields(this.value)"}),
            "stock": forms.NumberInput(attrs={"data-product-type": "physical"}),
            "file": forms.FileInput(attrs={"accept": ".pdf,.zip,.mp4,.docx", "data-product-type": "digital"}),
            "category": forms.TextInput(attrs={"placeholder": "Educational Materials"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product_type"].initial = "physical"

        if self.instance and self.instance.pk:
            if self.instance.product_type == "digital":
                self.fields["file"].required = True
                self.fields["stock"].required = False
            else:
                self.fields["stock"].required = True

    def clean(self):
        cleaned_data = super().clean()
        product_type = cleaned_data.get("product_type")
        price = cleaned_data.get("price")
        discount_price = cleaned_data.get("discount_price")
        stock = cleaned_data.get("stock")
        file = cleaned_data.get("file")

        if discount_price and discount_price >= price:
            self.add_error("discount_price", "Discount must be lower than base price")

        if product_type == "digital":
            if stock is not None:
                self.add_error("stock", "Digital products can't have stock")
            if not file and not self.instance.file:
                self.add_error("file", "File required for digital products")
        else:
            if stock is None:
                self.add_error("stock", "Stock required for physical products")
            if file:
                self.add_error("file", "Files only for digital products")

        return cleaned_data

    def save(self, commit=True):
        goods = super().save(commit=False)

        # Handle product type specific fields
        if goods.product_type == "digital":
            goods.stock = None
        else:
            goods.file = None

        if commit:
            goods.save()
            self.save_images(goods)

        return goods

    def save_images(self, goods):
        # Delete existing images if replacing
        if "images" in self.changed_data:
            goods.images.all().delete()

        # Create new ProductImage instances
        for img in self.files.getlist("images"):
            ProductImage.objects.create(goods=goods, image=img)


class StorefrontForm(forms.ModelForm):
    class Meta:
        model = Storefront
        fields = [
            "name",
            "description",
            "store_slug",
            "logo",
            "is_active",
        ]


class TeamGoalCompletionForm(forms.ModelForm):
    class Meta:
        model = TeamGoalMember
        fields = ["completion_image", "completion_link", "completion_notes"]
        widgets = {
            "completion_notes": forms.Textarea(attrs={"rows": 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        image = cleaned_data.get("completion_image")
        link = cleaned_data.get("completion_link")
        notes = cleaned_data.get("completion_notes")
        if not image and not link and not notes:
            raise forms.ValidationError("Please provide at least one form of proof (image, link, or notes).")
        return cleaned_data


class TeamGoalForm(forms.ModelForm):
    """Form for creating and editing team goals."""

    class Meta:
        model = TeamGoal
        fields = ["title", "description", "deadline"]
        widgets = {
            "deadline": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def clean_deadline(self):
        """Validate that the deadline is in the future."""
        deadline = self.cleaned_data.get("deadline")
        if deadline and deadline < timezone.now():
            raise forms.ValidationError("Deadline cannot be in the past.")
        return deadline


class TeamInviteForm(forms.ModelForm):
    """Form for inviting users to a team goal."""

    recipient_search = forms.CharField(
        label="Invite User",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Search by username or email",
                "list": "user-list",
                "autocomplete": "off",
            }
        ),
        required=False,
    )

    class Meta:
        model = TeamInvite
        fields = ["recipient"]
        widgets = {
            "recipient": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        current_user = kwargs.pop("current_user", None)
        self.team_goal = kwargs.pop("team_goal", None)
        super().__init__(*args, **kwargs)
        # Get all users except the current user (will be filtered in the view)
        if current_user:
            self.fields["recipient"].queryset = User.objects.exclude(id=current_user.id)
        else:
            self.fields["recipient"].queryset = User.objects.all()

    def clean_recipient(self):
        recipient = self.cleaned_data.get("recipient")
        if self.team_goal and recipient:
            # Check if the user is already a member of the team
            if self.team_goal.members.filter(user=recipient).exists():
                raise forms.ValidationError("This user is already a member of the team.")
            # Check if there's already a pending invitation
            if TeamInvite.objects.filter(goal=self.team_goal, recipient=recipient, status="pending").exists():
                raise forms.ValidationError("This user already has a pending invitation.")
        return recipient


class ProgressTrackerForm(forms.ModelForm):
    class Meta:
        model = ProgressTracker
        fields = ["title", "description", "current_value", "target_value", "color", "public"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }


class MemeForm(forms.ModelForm):
    new_subject = forms.CharField(
        max_length=100,
        required=False,
        widget=TailwindInput(
            attrs={
                "placeholder": "Enter a new subject name",
                "class": "w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500",
            }
        ),
        help_text="If your subject isn't listed, enter a new one here",
    )

    class Meta:
        model = Meme
        fields = ["title", "subject", "new_subject", "caption", "image"]
        widgets = {
            "title": TailwindInput(
                attrs={
                    "placeholder": "Enter a descriptive title",
                    "required": True,
                }
            ),
            "subject": TailwindSelect(
                attrs={
                    "class": "w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500"
                }
            ),
            "caption": TailwindTextarea(
                attrs={
                    "placeholder": "Add a caption for your meme",
                    "rows": 3,
                }
            ),
            "image": TailwindFileInput(
                attrs={
                    "accept": "image/png,image/jpeg,image/gif",
                    "required": True,
                    "help_text": "Upload a meme image (JPG, PNG, or GIF, max 2MB)",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["subject"].required = False
        self.fields["subject"].help_text = "Select an existing subject"

        # Improve error messages
        self.fields["image"].error_messages = {
            "required": "Please select an image file.",
            "invalid": "Please upload a valid image file.",
        }

    def clean(self):
        cleaned_data = super().clean()
        subject = cleaned_data.get("subject")
        new_subject = cleaned_data.get("new_subject")

        if not subject and not new_subject:
            raise forms.ValidationError("You must either select an existing subject or create a new one.")

        return cleaned_data

    def save(self, commit=True):
        meme = super().save(commit=False)

        # Create new subject if provided
        new_subject_name = self.cleaned_data.get("new_subject")
        if new_subject_name and not self.cleaned_data.get("subject"):
            from django.utils.text import slugify

            subject, created = Subject.objects.get_or_create(
                name=new_subject_name, defaults={"slug": slugify(new_subject_name)}
            )
            meme.subject = subject

        if commit:
            meme.save()
        return meme


class StudentEnrollmentForm(forms.Form):
    first_name = forms.CharField(
        max_length=30, required=True, widget=TailwindInput(attrs={"placeholder": "First Name"}), label="First Name"
    )
    last_name = forms.CharField(
        max_length=30, required=True, widget=TailwindInput(attrs={"placeholder": "Last Name"}), label="Last Name"
    )
    email = forms.EmailField(
        required=True, widget=TailwindEmailInput(attrs={"placeholder": "Student Email"}), label="Student Email"
    )


class QuizForm(forms.ModelForm):
    """Form for creating and editing quizzes."""

    class Meta:
        model = Quiz
        fields = [
            "title",
            "description",
            "subject",
            "status",
            "time_limit",
            "randomize_questions",
            "show_correct_answers",
            "allow_anonymous",
            "max_attempts",
        ]
        widgets = {
            "title": TailwindInput(attrs={"placeholder": "Quiz Title"}),
            "description": TailwindTextarea(attrs={"rows": 3, "placeholder": "Quiz Description"}),
            "subject": TailwindSelect(),
            "status": TailwindSelect(),
            "time_limit": TailwindNumberInput(
                attrs={"min": "0", "placeholder": "Time limit in minutes (leave empty for no limit)"}
            ),
            "randomize_questions": TailwindCheckboxInput(),
            "show_correct_answers": TailwindCheckboxInput(),
            "allow_anonymous": TailwindCheckboxInput(),
            "max_attempts": TailwindNumberInput(attrs={"min": "0", "placeholder": "0 for unlimited attempts"}),
        }

    def __init__(self, *args, **kwargs):
        kwargs.pop("user", None)  # Use this if needed for filtering
        super().__init__(*args, **kwargs)

        # Subject queryset filtering based on user type could be added here


class QuizQuestionForm(forms.ModelForm):
    """Form for creating and editing quiz questions."""

    class Meta:
        model = QuizQuestion
        fields = ["text", "question_type", "explanation", "points", "image"]
        widgets = {
            "text": TailwindTextarea(attrs={"rows": 3, "placeholder": "Question text"}),
            "question_type": TailwindSelect(),
            "explanation": TailwindTextarea(attrs={"rows": 2, "placeholder": "Explanation for the correct answer"}),
            "points": TailwindNumberInput(attrs={"min": "1", "value": "1"}),
            "order": TailwindNumberInput(attrs={"min": "0", "value": "0"}),
            "image": TailwindFileInput(attrs={"accept": "image/*"}),
        }


# Form for quiz options using formset factory
QuizOptionFormSet = forms.inlineformset_factory(
    QuizQuestion,
    QuizOption,
    fields=("text", "is_correct"),
    widgets={
        "text": TailwindInput(attrs={"placeholder": "Option text"}),
        "is_correct": TailwindCheckboxInput(),
    },
    extra=4,
    can_delete=True,
    validate_min=True,
    min_num=1,
)


class TakeQuizForm(forms.Form):
    """Form for taking quizzes. Dynamically generated based on questions."""

    def __init__(self, *args, quiz=None, **kwargs):
        super().__init__(*args, **kwargs)
        if quiz:
            for question in quiz.questions.all().order_by("order"):
                if question.question_type == "multiple":
                    # For multiple choice, add a multi-select field
                    options = question.options.all().order_by("order")
                    choices = [(str(option.id), option.text) for option in options]
                    self.fields[f"question_{question.id}"] = forms.MultipleChoiceField(
                        label=question.text, choices=choices, widget=forms.CheckboxSelectMultiple, required=False
                    )
                elif question.question_type == "true_false":
                    # For true/false, add a radio select field
                    options = question.options.all().order_by("order")
                    choices = [(str(option.id), option.text) for option in options]
                    self.fields[f"question_{question.id}"] = forms.ChoiceField(
                        label=question.text, choices=choices, widget=forms.RadioSelect, required=False
                    )
                elif question.question_type == "short":
                    # For short answer, add a text field
                    self.fields[f"question_{question.id}"] = forms.CharField(
                        label=question.text,
                        widget=TailwindTextarea(attrs={"rows": 2, "placeholder": "Your answer..."}),
                        required=False,
                    )


class GradeableLinkForm(forms.ModelForm):
    """Form for submitting a link to be graded."""

    class Meta:
        model = GradeableLink
        fields = ["title", "url", "description", "link_type"]
        widgets = {
            "title": TailwindInput(attrs={"placeholder": "Enter a descriptive title"}),
            "url": TailwindInput(attrs={"placeholder": "https://example.com", "type": "url"}),
            "description": TailwindTextarea(attrs={"rows": 4, "placeholder": "Describe what you want feedback on..."}),
            "link_type": TailwindSelect(),
        }
        help_texts = {
            "title": "A clear title describing what you want feedback on",
            "url": "Link to the PR, article, or content you want graded",
            "description": "Provide context about what you're looking for feedback on",
        }


class LinkGradeForm(forms.ModelForm):
    """Form for grading a link."""

    class Meta:
        model = LinkGrade
        fields = ["grade", "comment"]
        widgets = {
            "comment": TailwindTextarea(attrs={"rows": 4, "placeholder": "Comment required for grades below A"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Use radio buttons for grade selection
        self.fields["grade"].widget = forms.RadioSelect(choices=LinkGrade.GRADE_CHOICES)

    def clean(self):
        cleaned_data = super().clean()
        grade = cleaned_data.get("grade")
        comment = cleaned_data.get("comment")

        if grade not in ["A+", "A"] and not comment:
            self.add_error("comment", "A comment is required for grades below A.")

        return cleaned_data


class NotificationPreferencesForm(forms.ModelForm):
    class Meta:
        model = NotificationPreference
        fields = ["reminder_days_before", "reminder_hours_before", "email_notifications", "in_app_notifications"]
        widgets = {
            "reminder_days_before": forms.NumberInput(attrs={"min": 1, "max": 14}),
            "reminder_hours_before": forms.NumberInput(attrs={"min": 1, "max": 72}),
        }


class StudyGroupForm(forms.ModelForm):
    class Meta:
        model = StudyGroup
        fields = ["name", "description", "course", "max_members", "is_private"]


class SelfCheckinPreForm(forms.ModelForm):
    """Form for students to check in before a session with their confidence level"""

    pre_rating = forms.IntegerField(
        widget=forms.RadioSelect(
            choices=[
                (1, "1 - Not confident at all"),
                (2, "2 - Slightly confident"),
                (3, "3 - Moderately confident"),
                (4, "4 - Very confident"),
                (5, "5 - Extremely confident"),
            ],
            attrs={"class": "rating-select"},
        ),
        label="How confident are you about this session's topic?",
        min_value=1,
        max_value=5,
    )

    notes = forms.CharField(
        widget=TailwindTextarea(
            attrs={"rows": 3, "placeholder": "Anything specific you want to learn or struggling with?"}
        ),
        required=False,
        label="Notes (optional)",
    )

    class Meta:
        model = SelfCheckin
        fields = ["pre_rating", "notes"]


class SelfCheckinPostForm(forms.ModelForm):
    """Form for students to check in after a session with their confidence level"""

    post_rating = forms.IntegerField(
        widget=forms.RadioSelect(
            choices=[
                (1, "1 - Not confident at all"),
                (2, "2 - Slightly confident"),
                (3, "3 - Moderately confident"),
                (4, "4 - Very confident"),
                (5, "5 - Extremely confident"),
            ],
            attrs={"class": "rating-select"},
        ),
        label="How confident are you NOW about this session's topic?",
        min_value=1,
        max_value=5,
    )

    notes = forms.CharField(
        widget=TailwindTextarea(
            attrs={"rows": 3, "placeholder": "Any thoughts about your progress during this session?"}
        ),
        required=False,
        label="Notes (optional)",
    )

    class Meta:
        model = SelfCheckin
        fields = ["post_rating", "notes"]


class SessionFeedbackForm(forms.ModelForm):
    """Form for submitting Rose, Bud, Thorn feedback for a session"""

    rose = forms.CharField(
        widget=TailwindTextarea(
            attrs={"rows": 3, "placeholder": "Something that went well or that you liked about the session"}
        ),
        required=False,
        label="Rose 🌹 (What went well)",
    )

    bud = forms.CharField(
        widget=TailwindTextarea(
            attrs={"rows": 3, "placeholder": "Something you want to learn more about or that has potential"}
        ),
        required=False,
        label="Bud 🌱 (What has potential)",
    )

    thorn = forms.CharField(
        widget=TailwindTextarea(
            attrs={"rows": 3, "placeholder": "Something that was difficult, confusing, or frustrating"}
        ),
        required=False,
        label="Thorn 🌵 (What was difficult)",
    )

    class Meta:
        model = SessionFeedback
        fields = ["rose", "bud", "thorn"]


class SessionSurveyForm(forms.ModelForm):
    """Form for submitting ratings for a session"""

    content_rating = forms.IntegerField(
        widget=forms.RadioSelect(
            choices=[(1, "1 - Poor"), (2, "2 - Fair"), (3, "3 - Good"), (4, "4 - Very Good"), (5, "5 - Excellent")],
            attrs={"class": "rating-select"},
        ),
        label="How beneficial was the session content?",
        min_value=1,
        max_value=5,
    )

    teaching_rating = forms.IntegerField(
        widget=forms.RadioSelect(
            choices=[(1, "1 - Poor"), (2, "2 - Fair"), (3, "3 - Good"), (4, "4 - Very Good"), (5, "5 - Excellent")],
            attrs={"class": "rating-select"},
        ),
        label="How effective was the teaching/presentation?",
        min_value=1,
        max_value=5,
    )

    pace_rating = forms.IntegerField(
        widget=forms.RadioSelect(
            choices=[
                (1, "1 - Too slow"),
                (2, "2 - Slightly slow"),
                (3, "3 - Just right"),
                (4, "4 - Slightly fast"),
                (5, "5 - Too fast"),
            ],
            attrs={"class": "rating-select"},
        ),
        label="How was the pace of the session?",
        min_value=1,
        max_value=5,
    )

    materials_rating = forms.IntegerField(
        widget=forms.RadioSelect(
            choices=[(1, "1 - Poor"), (2, "2 - Fair"), (3, "3 - Good"), (4, "4 - Very Good"), (5, "5 - Excellent")],
            attrs={"class": "rating-select"},
        ),
        label="How useful were the materials?",
        min_value=1,
        max_value=5,
    )

    comments = forms.CharField(
        widget=TailwindTextarea(attrs={"rows": 3, "placeholder": "Any additional comments or suggestions?"}),
        required=False,
        label="Additional Comments (optional)",
    )

    class Meta:
        model = SessionSurvey
        fields = ["content_rating", "teaching_rating", "pace_rating", "materials_rating", "comments"]
class VideoRequestForm(forms.ModelForm):
    """Form for users to request educational videos on specific topics, with XSS protection."""

    ALLOWED_TAGS: ClassVar[list[str]] = ["b", "i", "strong", "em", "ul", "ol", "li", "p", "a"]
    ALLOWED_ATTRIBUTES: ClassVar[dict[str, list[str]]] = {
        # Only allow href, title and target attributes on anchor tags for security
        "a": ["href", "title", "target"],
    }

    class Meta:
        model = VideoRequest
        fields = ["title", "description", "category"]
        widgets = {
            "title": TailwindInput(attrs={"placeholder": "Title of the video you're requesting"}),
            "description": TailwindTextarea(
                attrs={
                    "rows": 4,
                    "placeholder": (
                        "Describe what you'd like to learn from this video "
                        "(e.g., 'I'd like a video on calculus basics')",
                    ),
                }
            ),
            "category": TailwindSelect(
                attrs={
                    "class": (
                        "w-full px-4 py-2 border border-gray-300 dark:border-gray-600"
                        " rounded-lg focus:ring-2 focus:ring-blue-500",
                    )
                }
            ),
        }

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Subject.objects.all().order_by("name")

    def clean_title(self) -> str:
        title = self.cleaned_data.get("title", "")  # Added default value
        # Strip all tags to ensure title contains only plain text
        return bleach.clean(title, tags=self.ALLOWED_TAGS, attributes=self.ALLOWED_ATTRIBUTES, strip=True)

    def clean_description(self) -> str:
        description = self.cleaned_data.get("description", "")
        return bleach.clean(
            description,
            tags=self.ALLOWED_TAGS,
            attributes=self.ALLOWED_ATTRIBUTES,
            strip=True,
        )


class SurveyForm(forms.ModelForm):
    title = forms.CharField(
        max_length=200,
        widget=TailwindInput(attrs={"placeholder": "Enter survey title"}),
        help_text="Give your survey a clear and descriptive title",
    )

    class Meta:
        model = Survey
        fields = ["title"]

    def clean_title(self) -> str:
        title = self.cleaned_data.get("title")
        if len(title) < 5:
            raise forms.ValidationError(_("Title too short"), code="invalid_length", params={"min_length": 5})
        return title


class VirtualClassroomForm(forms.ModelForm):
    """Form for creating and editing virtual classrooms."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields["course"].queryset = Course.objects.filter(teacher=user)

    class Meta:
        model = VirtualClassroom
        fields = ["name", "course", "max_students"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300"
                    "dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500"
                }
            ),
            "course": forms.Select(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 dark:border-gray-600"
                    " rounded-lg focus:ring-2 focus:ring-blue-500"
                }
            ),
            "max_students": forms.NumberInput(
                attrs={
                    "class": "w-full px-4 py-2 border border-gray-300 dark:border-gray-600"
                    " rounded-lg focus:ring-2 focus:ring-blue-500"
                }
            ),
        }


class VirtualClassroomCustomizationForm(forms.ModelForm):
    """Form for customizing virtual classroom appearance."""

    class Meta:
        model = VirtualClassroomCustomization
        fields = [
            "wall_color",
            "floor_color",
            "desk_color",
            "chair_color",
            "board_color",
            "number_of_rows",
            "desks_per_row",
            "has_plants",
            "has_windows",
            "has_bookshelf",
            "has_clock",
            "has_carpet",
        ]
        widgets = {
            "wall_color": forms.TextInput(attrs={"type": "color", "class": "w-full h-10 rounded-lg cursor-pointer"}),
            "floor_color": forms.TextInput(attrs={"type": "color", "class": "w-full h-10 rounded-lg cursor-pointer"}),
            "desk_color": forms.TextInput(attrs={"type": "color", "class": "w-full h-10 rounded-lg cursor-pointer"}),
            "chair_color": forms.TextInput(attrs={"type": "color", "class": "w-full h-10 rounded-lg cursor-pointer"}),
            "board_color": forms.TextInput(attrs={"type": "color", "class": "w-full h-10 rounded-lg cursor-pointer"}),
            "number_of_rows": forms.NumberInput(
                attrs={
                    "class": (
                        "w-full px-4 py-2 border border-gray-300 dark:border-gray-600 "
                        "rounded-lg focus:ring-2 focus:ring-blue-500"
                    ),
                    "min": "1",
                    "max": "10",
                }
            ),
            "desks_per_row": forms.NumberInput(
                attrs={
                    "class": (
                        "w-full px-4 py-2 border border-gray-300 dark:border-gray-600 "
                        "rounded-lg focus:ring-2 focus:ring-blue-500"
                    ),
                    "min": "1",
                    "max": "8",
                }
            ),
            "has_plants": forms.CheckboxInput(
                attrs={"class": "w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"}
            ),
            "has_windows": forms.CheckboxInput(
                attrs={"class": "w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"}
            ),
            "has_bookshelf": forms.CheckboxInput(
                attrs={"class": "w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"}
            ),
            "has_clock": forms.CheckboxInput(
                attrs={"class": "w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"}
            ),
            "has_carpet": forms.CheckboxInput(
                attrs={"class": "w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"}
            ),
        }

    def clean_number_of_rows(self):
        value = self.cleaned_data.get("number_of_rows")
        if value is None or value < 1 or value > 10:
            raise forms.ValidationError("Number of rows must be between 1 and 10.")
        return value

    def clean_desks_per_row(self):
        value = self.cleaned_data.get("desks_per_row")
        if value is None or value < 1 or value > 8:
            raise forms.ValidationError("Desks per row must be between 1 and 8.")
        return value
