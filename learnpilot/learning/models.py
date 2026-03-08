"""Models for the learning app."""

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class Topic(models.Model):
    """A subject area for learning (e.g., Python, Mathematics)."""

    DIFFICULTY_CHOICES = [
        ("beginner", "Beginner"),
        ("intermediate", "Intermediate"),
        ("advanced", "Advanced"),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField()
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default="beginner")
    icon = models.CharField(max_length=50, default="📚", help_text="Emoji icon for the topic")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Course(models.Model):
    """A structured course within a topic."""

    DIFFICULTY_CHOICES = [
        ("beginner", "Beginner"),
        ("intermediate", "Intermediate"),
        ("advanced", "Advanced"),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="courses")
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default="beginner")
    estimated_hours = models.FloatField(default=1.0)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["topic", "difficulty", "title"]

    def __str__(self):
        return f"{self.title} ({self.topic})"

    def total_lessons(self):
        return self.lessons.count()


class Lesson(models.Model):
    """An individual lesson within a course."""

    LESSON_TYPES = [
        ("theory", "Theory"),
        ("practice", "Practice"),
        ("quiz", "Quiz"),
        ("project", "Project"),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(max_length=200)
    content = models.TextField(help_text="Core lesson content / learning objectives")
    lesson_type = models.CharField(max_length=20, choices=LESSON_TYPES, default="theory")
    order = models.PositiveIntegerField(default=0)
    xp_reward = models.PositiveIntegerField(default=10, help_text="Experience points awarded on completion")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["course", "order"]

    def __str__(self):
        return f"{self.course.title} – {self.title}"


class LearnerProfile(models.Model):
    """Extended profile for a learner with adaptive learning data."""

    LEARNING_STYLES = [
        ("visual", "Visual"),
        ("auditory", "Auditory"),
        ("reading", "Reading/Writing"),
        ("kinesthetic", "Hands-on/Kinesthetic"),
    ]

    SKILL_LEVELS = [
        ("beginner", "Beginner"),
        ("intermediate", "Intermediate"),
        ("advanced", "Advanced"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="learner_profile")
    learning_style = models.CharField(max_length=20, choices=LEARNING_STYLES, default="visual")
    skill_level = models.CharField(max_length=20, choices=SKILL_LEVELS, default="beginner")
    preferred_topics = models.ManyToManyField(Topic, blank=True, related_name="interested_learners")
    total_xp = models.PositiveIntegerField(default=0)
    streak_days = models.PositiveIntegerField(default=0)
    last_active = models.DateTimeField(null=True, blank=True, default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Learner Profile"

    def __str__(self):
        return f"{self.user.username}'s profile"

    def update_activity(self):
        """Update streak and last-active timestamp."""
        now = timezone.now()
        if self.last_active:
            delta = now.date() - self.last_active.date()
            if delta.days == 1:
                self.streak_days += 1
            elif delta.days > 1:
                self.streak_days = 1
        else:
            self.streak_days = 1
        self.last_active = now
        self.save(update_fields=["streak_days", "last_active"])


class Progress(models.Model):
    """Tracks a learner's progress through a specific lesson."""

    learner = models.ForeignKey(LearnerProfile, on_delete=models.CASCADE, related_name="progress_records")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="progress_records")
    score = models.FloatField(default=0.0, help_text="Normalised score 0.0–1.0")
    completed = models.BooleanField(default=False)
    attempts = models.PositiveIntegerField(default=0)
    time_spent_seconds = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("learner", "lesson")
        verbose_name_plural = "Progress records"

    def __str__(self):
        status = "✓" if self.completed else "…"
        return f"{status} {self.learner.user.username} – {self.lesson.title}"

    def mark_complete(self, score: float):
        self.score = max(0.0, min(1.0, score))
        self.completed = True
        self.completed_at = timezone.now()
        self.attempts += 1
        self.save()
        # Award XP
        self.learner.total_xp += self.lesson.xp_reward
        self.learner.save(update_fields=["total_xp"])


class AdaptivePath(models.Model):
    """A personalised learning path generated by the AI for a learner."""

    learner = models.ForeignKey(LearnerProfile, on_delete=models.CASCADE, related_name="adaptive_paths")
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE)
    lessons = models.ManyToManyField(Lesson, through="PathLesson", related_name="adaptive_paths")
    rationale = models.TextField(blank=True, help_text="AI-generated explanation of path choices")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Adaptive Path"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.learner.user.username} – {self.topic.name} path"


class PathLesson(models.Model):
    """Ordered membership of a lesson in an adaptive path."""

    path = models.ForeignKey(AdaptivePath, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]
        unique_together = ("path", "lesson")


class LearningSession(models.Model):
    """An active or completed tutoring session for a learner on a lesson."""

    learner = models.ForeignKey(LearnerProfile, on_delete=models.CASCADE, related_name="sessions")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="sessions")
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"Session: {self.learner.user.username} on '{self.lesson.title}'"

    def end_session(self):
        self.ended_at = timezone.now()
        self.is_active = False
        self.save(update_fields=["ended_at", "is_active"])

    def duration_seconds(self):
        if self.ended_at:
            return int((self.ended_at - self.started_at).total_seconds())
        return int((timezone.now() - self.started_at).total_seconds())


class Message(models.Model):
    """A chat message within a learning session."""

    ROLES = [
        ("user", "Learner"),
        ("assistant", "AI Tutor"),
        ("system", "System"),
    ]

    session = models.ForeignKey(LearningSession, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=20, choices=ROLES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"[{self.role}] {self.content[:60]}…"
