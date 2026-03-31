from django.contrib import admin

from .models import Discovery, DiscoveryProject, Experiment, Hypothesis, IterationLog, KnowledgeBase


@admin.register(DiscoveryProject)
class DiscoveryProjectAdmin(admin.ModelAdmin):
    list_display = ["title", "user", "domain", "status", "is_public", "created_at"]
    list_filter = ["domain", "status", "is_public", "created_at"]
    search_fields = ["title", "description", "user__username"]
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = "created_at"


@admin.register(Hypothesis)
class HypothesisAdmin(admin.ModelAdmin):
    list_display = ["statement_preview", "project", "status", "confidence_score", "is_ai_generated", "created_at"]
    list_filter = ["status", "is_ai_generated", "created_at"]
    search_fields = ["statement", "rationale", "project__title"]
    date_hierarchy = "created_at"

    def statement_preview(self, obj):
        return obj.statement[:100] + "..." if len(obj.statement) > 100 else obj.statement

    statement_preview.short_description = "Statement"


@admin.register(Experiment)
class ExperimentAdmin(admin.ModelAdmin):
    list_display = ["experiment_type", "hypothesis_preview", "status", "started_at", "completed_at"]
    list_filter = ["experiment_type", "status", "created_at"]
    search_fields = ["description", "hypothesis__statement"]
    date_hierarchy = "created_at"

    def hypothesis_preview(self, obj):
        return obj.hypothesis.statement[:50] + "..." if len(obj.hypothesis.statement) > 50 else obj.hypothesis.statement

    hypothesis_preview.short_description = "Hypothesis"


@admin.register(Discovery)
class DiscoveryAdmin(admin.ModelAdmin):
    list_display = ["title", "project", "significance", "is_verified", "created_at"]
    list_filter = ["significance", "is_verified", "created_at"]
    search_fields = ["title", "summary", "project__title"]
    date_hierarchy = "created_at"


@admin.register(KnowledgeBase)
class KnowledgeBaseAdmin(admin.ModelAdmin):
    list_display = ["title", "content_type", "domain", "created_at"]
    list_filter = ["content_type", "domain", "created_at"]
    search_fields = ["title", "abstract", "content"]
    date_hierarchy = "created_at"


@admin.register(IterationLog)
class IterationLogAdmin(admin.ModelAdmin):
    list_display = ["hypothesis_preview", "iteration_number", "action", "created_at"]
    list_filter = ["action", "created_at"]
    search_fields = ["details", "ai_reasoning", "hypothesis__statement"]
    date_hierarchy = "created_at"

    def hypothesis_preview(self, obj):
        return obj.hypothesis.statement[:50] + "..." if len(obj.hypothesis.statement) > 50 else obj.hypothesis.statement

    hypothesis_preview.short_description = "Hypothesis"
