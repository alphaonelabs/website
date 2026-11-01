from django import forms
from django.contrib.auth.models import User

from .models import BlogComment, Course, CourseMaterial, Review, StudyGroup
from .widgets import (
    TailwindCheckboxInput,
    TailwindEmailInput,
    TailwindFileInput,
    TailwindInput,
    TailwindNumberInput,
    TailwindSelect,
    TailwindTextarea,
)


class BlogCommentForm(forms.ModelForm):
    class Meta:
        model = BlogComment
        fields = ["content"]
        widgets = {
            "content": TailwindTextarea(attrs={"rows": 3, "placeholder": "Write your comment here..."}),
        }


class MessageForm(forms.Form):
    content = forms.CharField(widget=TailwindTextarea(attrs={"rows": 3, "placeholder": "Type your message here..."}))


class LearningInquiryForm(forms.Form):
    name = forms.CharField(max_length=100, widget=TailwindInput())
    email = forms.EmailField(widget=TailwindEmailInput())
    subject_interest = forms.CharField(
        widget=TailwindTextarea(
            attrs={
                "rows": 4,
                "placeholder": "What subjects are you interested in learning?",
            }
        )
    )
    learning_goals = forms.CharField(
        widget=TailwindTextarea(
            attrs={
                "rows": 4,
                "placeholder": "Tell us about your learning goals",
            }
        )
    )
    preferred_schedule = forms.CharField(
        widget=TailwindInput(attrs={"placeholder": "What days/times work best for you?"})
    )
    experience_level = forms.ChoiceField(
        choices=[
            ("beginner", "Beginner"),
            ("intermediate", "Intermediate"),
            ("advanced", "Advanced"),
        ],
        widget=TailwindSelect(),
    )


class TeachingInquiryForm(forms.Form):
    name = forms.CharField(max_length=100, widget=TailwindInput())
    email = forms.EmailField(widget=TailwindEmailInput())
    expertise = forms.CharField(
        widget=TailwindTextarea(attrs={"rows": 4, "placeholder": "What subjects would you like to teach?"})
    )
    experience = forms.CharField(
        widget=TailwindTextarea(attrs={"rows": 4, "placeholder": "Tell us about your teaching experience"})
    )


class StudyGroupForm(forms.ModelForm):
    class Meta:
        model = StudyGroup
        fields = ["name", "description", "max_members", "is_private"]
        widgets = {
            "name": TailwindInput(),
            "description": TailwindTextarea(attrs={"rows": 3}),
            "max_members": TailwindNumberInput(attrs={"min": "2"}),
            "is_private": TailwindCheckboxInput(),
        }


class CourseSearchForm(forms.Form):
    query = forms.CharField(required=False, widget=TailwindInput(attrs={"placeholder": "Search courses..."}))
    subject = forms.ChoiceField(required=False, widget=TailwindSelect(), choices=[("", "All Subjects")])
    level = forms.ChoiceField(
        required=False,
        widget=TailwindSelect(),
        choices=[
            ("", "All Levels"),
            ("beginner", "Beginner"),
            ("intermediate", "Intermediate"),
            ("advanced", "Advanced"),
        ],
    )
    price_min = forms.DecimalField(
        required=False,
        widget=TailwindNumberInput(attrs={"min": "0", "step": "0.01", "placeholder": "Min price"}),
        min_value=0,
    )
    price_max = forms.DecimalField(
        required=False,
        widget=TailwindNumberInput(attrs={"min": "0", "step": "0.01", "placeholder": "Max price"}),
        min_value=0,
    )

    def clean(self):
        cleaned_data = super().clean()
        price_min = cleaned_data.get("price_min")
        price_max = cleaned_data.get("price_max")

        if price_min and price_max and price_min > price_max:
            raise forms.ValidationError("Minimum price cannot be greater than maximum price")

        return cleaned_data


class CourseUpdateForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = [
            "title",
            "description",
            "learning_objectives",
            "prerequisites",
            "price",
            "max_students",
            "subject",
            "level",
            "tags",
            "status",
        ]
        widgets = {
            "title": TailwindInput(),
            "description": TailwindTextarea(attrs={"rows": 4}),
            "learning_objectives": TailwindTextarea(attrs={"rows": 4}),
            "prerequisites": TailwindTextarea(attrs={"rows": 4}),
            "price": TailwindNumberInput(attrs={"min": "0", "step": "0.01"}),
            "max_students": TailwindNumberInput(attrs={"min": "1"}),
            "subject": TailwindSelect(),
            "level": TailwindSelect(),
            "tags": TailwindInput(attrs={"placeholder": "Enter comma-separated tags"}),
            "status": TailwindSelect(),
        }

    def clean_price(self):
        price = self.cleaned_data.get("price")
        if price <= 0:
            raise forms.ValidationError("Price must be greater than zero")
        return price

    def clean_max_students(self):
        max_students = self.cleaned_data.get("max_students")
        if max_students <= 0:
            raise forms.ValidationError("Maximum number of students must be greater than zero")
        return max_students


class CourseReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["rating", "comment"]
        widgets = {
            "rating": TailwindNumberInput(attrs={"min": "1", "max": "5"}),
            "comment": TailwindTextarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Share your experience with this course...",
                }
            ),
        }


class MaterialUploadForm(forms.ModelForm):
    class Meta:
        model = CourseMaterial
        fields = [
            "title",
            "description",
            "material_type",
            "file",
            "session",
            "is_downloadable",
            "order",
        ]
        widgets = {
            "title": TailwindInput(),
            "description": TailwindTextarea(attrs={"rows": 3}),
            "material_type": TailwindSelect(),
            "file": TailwindFileInput(),
            "session": TailwindSelect(),
            "is_downloadable": TailwindCheckboxInput(),
            "order": TailwindNumberInput(attrs={"min": "0"}),
        }


class TopicCreationForm(forms.Form):
    title = forms.CharField(max_length=200, widget=TailwindInput(attrs={"placeholder": "Topic title"}))
    content = forms.CharField(
        widget=TailwindTextarea(attrs={"rows": 6, "placeholder": "Write your topic content here..."})
    )


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]

    bio = forms.CharField(widget=forms.Textarea, required=False)

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit and self.cleaned_data.get("bio"):
            user.profile.bio = self.cleaned_data["bio"]
            user.profile.save()
        return user
