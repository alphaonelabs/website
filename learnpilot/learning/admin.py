"""Admin registration for learning models."""

from django.contrib import admin

from .models import (
    AdaptivePath,
    Course,
    Lesson,
    LearnerProfile,
    LearningSession,
    Message,
    PathLesson,
    Progress,
    Topic,
)


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("name", "difficulty", "icon")
    search_fields = ("name",)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "topic", "difficulty", "estimated_hours", "is_published")
    list_filter = ("topic", "difficulty", "is_published")
    search_fields = ("title",)


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "lesson_type", "order", "xp_reward")
    list_filter = ("course__topic", "lesson_type")
    search_fields = ("title",)
    ordering = ("course", "order")


@admin.register(LearnerProfile)
class LearnerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "skill_level", "learning_style", "total_xp", "streak_days")
    search_fields = ("user__username",)


@admin.register(Progress)
class ProgressAdmin(admin.ModelAdmin):
    list_display = ("learner", "lesson", "score", "completed", "attempts")
    list_filter = ("completed",)


@admin.register(AdaptivePath)
class AdaptivePathAdmin(admin.ModelAdmin):
    list_display = ("learner", "topic", "is_active", "created_at")
    list_filter = ("topic", "is_active")


admin.register(PathLesson)(admin.ModelAdmin)


@admin.register(LearningSession)
class LearningSessionAdmin(admin.ModelAdmin):
    list_display = ("learner", "lesson", "started_at", "is_active")
    list_filter = ("is_active",)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("session", "role", "created_at")
    list_filter = ("role",)
