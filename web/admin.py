from allauth.account.models import EmailAddress
from django.contrib import admin, messages
from django.contrib.auth import login
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import models
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.utils.html import format_html

from .models import (
    Achievement,
    Badge,
    BlogComment,
    BlogPost,
    Cart,
    CartItem,
    Challenge,
    ChallengeSubmission,
    Chapter,
    ChapterApplication,
    ChapterEvent,
    ChapterEventRSVP,
    ChapterMembership,
    Course,
    CourseMaterial,
    CourseProgress,
    Donation,
    Enrollment,
    ForumCategory,
    ForumReply,
    ForumTopic,
    Goods,
    LearningStreak,
    MembershipPlan,
    MembershipSubscriptionEvent,
    Notification,
    Order,
    OrderItem,
    Payment,
    PeerChallenge,
    PeerChallengeInvitation,
    Points,
    ProductImage,
    Profile,
    ProgressTracker,
    Quiz,
    QuizOption,
    QuizQuestion,
    Review,
    SearchLog,
    Session,
    SessionAttendance,
    Storefront,
    Subject,
    SuccessStory,
    UserBadge,
    UserMembership,
    VideoRequest,
    WaitingRoom,
    WebRequest,
)

admin.site.unregister(EmailAddress)


# Create a custom EmailAddress admin
@admin.register(EmailAddress)
class EmailAddressAdmin(admin.ModelAdmin):
    list_display = ("email", "user", "primary", "verified")
    list_filter = ("primary", "verified")
    search_fields = ("email", "user__username", "user__email")
    raw_id_fields = ("user",)
    ordering = ("-verified", "-primary", "email")

    fieldsets = ((None, {"fields": ("user", "email", "primary", "verified")}),)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("user")


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = "Profile"
    fields = (
        "bio",
        "expertise",
        "avatar",
        "is_teacher",
        "referral_code",
        "referred_by",
        "referral_earnings",
        "commission_rate",
        "how_did_you_hear_about_us",
    )
    raw_id_fields = ("referred_by",)

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        formset.form.base_fields["referred_by"].required = False
        formset.form.base_fields["referral_earnings"].initial = 0
        formset.form.base_fields["commission_rate"].initial = 10.0
        return formset


class EmailAddressInline(admin.TabularInline):
    model = EmailAddress
    can_delete = True
    verbose_name_plural = "Email Addresses"
    extra = 1


@admin.register(WaitingRoom)
class WaitingRoomAdmin(admin.ModelAdmin):
    list_display = ("title", "subject", "creator", "status", "created_at")
    list_filter = ("status", "subject")
    search_fields = ("title", "description", "subject", "topics")
    date_hierarchy = "created_at"
    raw_id_fields = ("creator", "participants", "fulfilled_course")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "is_teacher", "expertise", "created_at", "updated_at")
    list_filter = ("is_teacher", "created_at", "updated_at")
    search_fields = ("user__username", "user__email", "expertise", "bio")
    ordering = ("-created_at",)
    raw_id_fields = ("user",)
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("user", "is_teacher")}),
        (
            "Profile Information",
            {"fields": ("bio", "expertise", "avatar", "is_profile_public", "how_did_you_hear_about_us")},
        ),
        ("Stripe Information", {"fields": ("stripe_account_id", "stripe_account_status", "commission_rate")}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


class EmailVerifiedFilter(admin.SimpleListFilter):
    title = "Email Verification"
    parameter_name = "email_verified"

    def lookups(self, request, model_admin):
        return (
            ("verified", "Verified"),
            ("unverified", "Not Verified"),
            ("no_record", "No Verification Record"),
        )

    def queryset(self, request, queryset):
        if self.value() == "verified":
            return queryset.filter(emailaddress__verified=True)
        elif self.value() == "unverified":
            return queryset.filter(emailaddress__verified=False)
        elif self.value() == "no_record":
            # Users with no EmailAddress record
            return queryset.exclude(id__in=EmailAddress.objects.values_list("user_id", flat=True))
        return queryset


class CustomUserAdmin(BaseUserAdmin):
    inlines = (ProfileInline, EmailAddressInline)
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "email_verified",
        "get_enrollment_count",
        "formatted_date_joined",
        "formatted_last_login",
        "rate_limit_status",
    )
    list_filter = BaseUserAdmin.list_filter + (EmailVerifiedFilter, "date_joined", "last_login")
    actions = ["unlock_user"]

    # Add email to the add_fieldsets
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "password1", "password2"),
            },
        ),
    )

    # Override the fieldsets to include the signup date and last login in a separate section
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "email")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    def get_ordering(self, request):
        """Override default ordering to sort by most recent signup date"""
        return ("-date_joined",)  # Descending order by date_joined

    def unlock_user(self, request, queryset):
        """
        Admin action to reset rate limits for users who have been locked out due to failed login attempts
        """
        count = 0
        # Rate limit types in django-allauth
        rate_limit_types = ["login_attempt", "login_failed"]

        for user in queryset:
            # For each user, clear their rate limiting cache entries
            for rate_limit_type in rate_limit_types:
                # Both email and username can be used for login
                identifiers = [user.username, user.email]

                for identifier in identifiers:
                    # Clear rate limits for this identifier
                    cache_key = f"allauth/rl/{rate_limit_type}/{identifier}"
                    cache.delete(cache_key)

                # Also clear the IP-based rate limits if available
                if hasattr(request, "META") and "REMOTE_ADDR" in request.META:
                    ip = request.META.get("REMOTE_ADDR")
                    ip_cache_key = f"allauth/rl/{rate_limit_type}/{ip}"
                    cache.delete(ip_cache_key)

            count += 1

        self.message_user(
            request, f"Successfully unlocked {count} user(s). They can now log in again.", messages.SUCCESS
        )

    unlock_user.short_description = "Unlock selected users (reset login rate limits)"

    def formatted_date_joined(self, obj):
        if obj.date_joined:
            return obj.date_joined.strftime("%B %d, %Y %H:%M")
        return "-"

    formatted_date_joined.short_description = "Signup Date"
    formatted_date_joined.admin_order_field = "date_joined"

    def formatted_last_login(self, obj):
        if obj.last_login:
            return obj.last_login.strftime("%B %d, %Y %H:%M")
        return "Never logged in"

    formatted_last_login.short_description = "Last Login"
    formatted_last_login.admin_order_field = "last_login"

    def email_verified(self, obj):
        from django.utils.html import format_html

        email_obj = EmailAddress.objects.filter(user=obj, email=obj.email).first()
        if email_obj:
            if email_obj.verified:
                return format_html('<span style="color: green;">✓ Verified</span>')
            else:
                return format_html('<span style="color: red;">✗ Not verified</span>')
        return format_html('<span style="color: orange;">? No record</span>')

    email_verified.short_description = "Email Verified"
    email_verified.admin_order_field = "emailaddress__verified"

    def get_enrollment_count(self, obj):
        count = obj.enrollments.count()
        if count > 0:
            url = reverse("admin:web_enrollment_changelist") + f"?student__id__exact={obj.id}"
            return format_html('<a href="{}">{} enrollments</a>', url, count)
        return "0 enrollments"

    get_enrollment_count.short_description = "Enrollments"
    get_enrollment_count.admin_order_field = "enrollments__count"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(models.Count("enrollments"))

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<id>/login_as_user/",
                self.admin_site.admin_view(self.login_as_user),
                name="auth_user_login_as",
            ),
        ]
        return custom_urls + urls

    def login_as_user(self, request, id):
        user = self.get_object(request, id)
        if not user:
            return self._get_obj_does_not_exist_redirect(request, "auth", "user", id)

        # Store the admin's ID and login as the user
        request.session["logged_in_as"] = {
            "original_user_id": request.user.id,
            "original_username": request.user.username,
            "target_username": user.username,
        }
        request.session.modified = True
        messages.success(request, f"You are now logged in as {user.username}")

        # Login as the selected user with the default auth backend
        from django.contrib.auth.backends import ModelBackend

        backend = ModelBackend()
        user.backend = f"{backend.__module__}.{backend.__class__.__name__}"
        login(request, user)

        return HttpResponseRedirect("/")

    def get_list_display(self, request):
        list_display = super().get_list_display(request)
        if request.user.is_superuser:
            return list_display + ("login_as_button",)
        return list_display

    def login_as_button(self, obj):
        if obj == self.model.objects.get(id=self.model._meta.pk.get_prep_value(obj.pk)):
            return format_html(
                '<a class="button" href="{}">Login as User</a>', reverse("admin:auth_user_login_as", args=[obj.pk])
            )

    login_as_button.short_description = ""
    login_as_button.allow_tags = True

    def save_model(self, request, obj, form, change):
        creating = not change  # True if creating new user, False if editing
        super().save_model(request, obj, form, change)

        if creating:
            # Get email from the form data
            email = form.data.get("emailaddress_set-0-email")
            if email:
                # Set the user's email field only
                obj.email = email
                obj.save()

    def rate_limit_status(self, obj):
        """Display if the user is currently rate limited for login attempts"""
        from django.utils.html import format_html

        # Check if user is rate limited for login attempts
        login_attempt_key = f"allauth/rl/login_failed/{obj.email}"
        login_failed_key = f"allauth/rl/login_attempt/{obj.email}"

        # Check if rate limits exist in cache
        is_limited_attempt = cache.get(login_attempt_key) is not None
        is_limited_failed = cache.get(login_failed_key) is not None

        if is_limited_attempt or is_limited_failed:
            return format_html('<span style="color: red;">&#x1F512; Locked</span>')
        else:
            return format_html('<span style="color: green;">&#x1F513; Unlocked</span>')

    rate_limit_status.short_description = "Login Status"


class SessionInline(admin.TabularInline):
    model = Session
    extra = 1


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("name", "order", "created_at")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "description")
    ordering = ("order", "name")


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "subject", "teacher", "price", "status")
    list_filter = ("subject", "level", "status", "is_featured")
    search_fields = ("title", "description", "teacher__username")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [SessionInline]


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {"fields": ("course", "title", "description", "start_time", "end_time")}),
        (
            "Location Information",
            {
                "fields": ("is_virtual", "meeting_link", "meeting_id", "location", "latitude", "longitude"),
                "classes": ("collapse",),
            },
        ),
        (
            "Pricing",
            {
                "fields": ("price",),
                "classes": ("collapse",),
            },
        ),
        (
            "Rollover Settings",
            {
                "fields": (
                    "enable_rollover",
                    "rollover_pattern",
                    "original_start_time",
                    "original_end_time",
                    "is_rolled_over",
                    "teacher_confirmed",
                ),
                "classes": ("collapse",),
            },
        ),
    )
    list_display = ("title", "course", "start_time", "end_time", "is_virtual", "teaching_style")
    list_filter = ("is_virtual", "start_time")
    search_fields = ("title", "description", "course__title")


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("student", "course", "status", "enrollment_date", "completion_date")
    list_filter = ("status", "enrollment_date")
    search_fields = ("student__username", "course__title")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("student", "course", "rating", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("student__username", "course__title", "comment")


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("course", "session")


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "session_key", "item_count", "total", "created_at")
    list_filter = ("created_at", "updated_at")
    search_fields = ("user__username", "user__email", "session_key")
    readonly_fields = ("created_at", "updated_at")
    inlines = [CartItemInline]
    raw_id_fields = ("user",)


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("id", "cart", "course", "session", "price", "created_at")
    list_filter = ("created_at", "updated_at")
    search_fields = ("cart__user__username", "cart__user__email", "course__title", "session__title")
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("cart", "course", "session")


@admin.register(SearchLog)
class SearchLogAdmin(admin.ModelAdmin):
    list_display = ("query", "results_count", "search_type", "user", "created_at")
    list_filter = ("search_type", "created_at")
    search_fields = ("query", "user__username", "user__email")
    readonly_fields = ("created_at", "filters_applied")
    ordering = ("-created_at",)
    raw_id_fields = ("user",)

    def has_add_permission(self, request):
        return False  # Search logs should only be created through the search interface

    def has_change_permission(self, request, obj=None):
        return False  # Search logs should not be editable


@admin.register(WebRequest)
class WebRequestAdmin(admin.ModelAdmin):
    list_display = ("path", "ip_address", "user", "count", "course", "get_agent", "created", "modified")
    list_filter = ("created", "modified")
    search_fields = ("path", "ip_address", "user", "agent", "referer")
    readonly_fields = ("created", "modified")
    ordering = ("-modified",)
    raw_id_fields = ("course",)

    def get_agent(self, obj):
        return obj.agent[:100] + "..." if len(obj.agent) > 100 else obj.agent

    get_agent.short_description = "User Agent"

    def has_add_permission(self, request):
        return False  # WebRequests should only be created through middleware

    def has_change_permission(self, request, obj=None):
        return False  # WebRequests should not be editable


@admin.register(CourseMaterial)
class CourseMaterialAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "material_type", "session", "order", "is_downloadable")
    list_filter = ("material_type", "is_downloadable", "requires_enrollment", "created_at")
    search_fields = ("title", "description", "course__title", "session__title")
    ordering = ("course", "order", "created_at")
    raw_id_fields = ("course", "session")


@admin.register(CourseProgress)
class CourseProgressAdmin(admin.ModelAdmin):
    list_display = ("enrollment", "completion_percentage", "attendance_rate", "last_accessed")
    list_filter = ("last_accessed",)
    search_fields = ("enrollment__student__username", "enrollment__course__title")
    raw_id_fields = ("enrollment", "completed_sessions")


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ("student", "course", "achievement_type", "title", "badge_icon", "criteria_threshold", "awarded_at")
    list_filter = ("achievement_type", "awarded_at")
    search_fields = ("student__username", "course__title", "title", "description", "badge_icon")
    raw_id_fields = ("student", "course")


@admin.register(SessionAttendance)
class SessionAttendanceAdmin(admin.ModelAdmin):
    list_display = ("session", "student", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("session__title", "student__username", "notes")
    raw_id_fields = ("session", "student")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "notification_type", "read", "created_at")
    list_filter = ("notification_type", "read", "created_at")
    search_fields = ("user__username", "title", "message")
    raw_id_fields = ("user",)


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "status", "published_at", "created_at")
    list_filter = ("status", "created_at", "published_at")
    search_fields = ("title", "content", "author__username", "tags")
    prepopulated_fields = {"slug": ("title",)}
    raw_id_fields = ("author",)


@admin.register(SuccessStory)
class SuccessStoryAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "status", "published_at", "created_at")
    list_filter = ("status", "created_at", "published_at")
    search_fields = ("title", "content", "author__username")
    prepopulated_fields = {"slug": ("title",)}
    raw_id_fields = ("author",)


@admin.register(BlogComment)
class BlogCommentAdmin(admin.ModelAdmin):
    list_display = ("post", "author", "is_approved", "created_at")
    list_filter = ("is_approved", "created_at")
    search_fields = ("post__title", "author__username", "content")
    raw_id_fields = ("post", "author", "parent")


@admin.register(ForumTopic)
class ForumTopicAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "author", "is_pinned", "is_locked", "views", "created_at")
    list_filter = ("is_pinned", "is_locked", "created_at")
    search_fields = ("title", "content", "author__username")
    raw_id_fields = ("author", "category")


@admin.register(ForumReply)
class ForumReplyAdmin(admin.ModelAdmin):
    list_display = ("topic", "author", "is_solution", "created_at")
    list_filter = ("is_solution", "created_at")
    search_fields = ("topic__title", "author__username", "content")
    raw_id_fields = ("topic", "author")


@admin.register(ForumCategory)
class ForumCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "order", "created_at")
    list_filter = ("created_at", "updated_at")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("order", "name")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("enrollment", "session", "amount", "currency", "status", "created_at")
    list_filter = ("status", "currency", "created_at")
    search_fields = ("enrollment__student__username", "enrollment__course__title", "stripe_payment_intent_id")
    raw_id_fields = ("enrollment", "session")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = ("week_number", "title", "start_date", "end_date")


@admin.register(ChallengeSubmission)
class ChallengeSubmissionAdmin(admin.ModelAdmin):
    list_display = ("user", "challenge", "submitted_at")


# Unregister the default User admin and register our custom one
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(Storefront)
class StorefrontAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "teacher", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("teacher__username", "store_name", "store_description")
    readonly_fields = ("id", "created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("teacher", "store_name", "is_active")}),
        ("Content", {"fields": ("store_description", "store_logo", "store_banner")}),
        ("Policies", {"fields": ("refund_policy", "privacy_policy")}),
        ("Metadata", {"fields": ("store_slug", "created_at", "updated_at")}),
    )
    autocomplete_fields = ["teacher"]

    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing existing object
            return self.readonly_fields + ("teacher",)
        return self.readonly_fields


@admin.register(Goods)
class GoodsAdmin(admin.ModelAdmin):
    list_display = ("name", "storefront", "price", "stock_status", "product_type", "is_available", "featured")
    list_filter = ("product_type", "is_available", "featured", "created_at")
    search_fields = ("name", "description", "sku", "storefront__store_name")
    readonly_fields = ("sku", "created_at", "updated_at")
    raw_id_fields = ("storefront",)
    list_editable = ("is_available", "featured")
    fieldsets = (
        (None, {"fields": ("name", "storefront", "is_available", "featured")}),
        ("Pricing", {"fields": ("price", "discount_price")}),
        ("Inventory", {"fields": ("product_type", "stock", "sku", "file")}),
        ("Content", {"fields": ("description", "category", "images")}),
        ("Dates", {"fields": ("created_at", "updated_at")}),
    )

    def stock_status(self, obj):
        if obj.product_type == "digital":
            return "N/A"
        return f"{obj.stock} in stock" if obj.stock else "Out of stock"

    stock_status.short_description = "Stock"


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    readonly_fields = ("preview",)

    def preview(self, obj):
        return format_html('<img src="{}" height="50" />', obj.image.url) if obj.image else "-"

    preview.short_description = "Preview"


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("goods", "preview", "alt_text")
    search_fields = ("goods__name", "alt_text")
    readonly_fields = ("preview",)
    raw_id_fields = ("goods",)

    def preview(self, obj):
        return format_html('<img src="{}" height="50" />', obj.image.url) if obj.image else "-"

    preview.short_description = "Preview"


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("goods", "quantity", "price_at_purchase", "discounted_price_at_purchase")
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "created_at", "updated_at")
    list_filter = ("status", "created_at")
    search_fields = ("user__email", "tracking_number")
    readonly_fields = ("id", "created_at", "updated_at")
    raw_id_fields = ("user",)
    date_hierarchy = "created_at"
    inlines = [OrderItemInline]
    actions = ["mark_as_completed"]

    fieldsets = (
        (None, {"fields": ("user", "status")}),
        ("Financials", {"fields": ("currency", "tax_rate")}),
        ("Fulfillment", {"fields": ("shipping_address", "tracking_number")}),
        ("Compliance", {"fields": ("terms_accepted", "transaction_log")}),
        ("Dates", {"fields": ("created_at", "updated_at")}),
    )

    def mark_as_completed(self, request, queryset):
        queryset.update(status="completed")

    mark_as_completed.short_description = "Mark selected orders as completed"


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "goods", "quantity", "price_at_purchase")
    list_filter = ("order__status",)
    search_fields = ("goods__name", "order__id")
    readonly_fields = ("id",)
    raw_id_fields = ("order", "goods")

    def price_display(self, obj):
        if obj.discounted_price_at_purchase:
            return f"${obj.discounted_price_at_purchase} (Discounted from ${obj.price_at_purchase})"
        return f"${obj.price_at_purchase}"

    price_display.short_description = "Price"


@admin.register(ProgressTracker)
class ProgressTrackerAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "current_value", "target_value", "percentage", "public", "updated_at")
    list_filter = ("public", "color", "created_at")
    search_fields = ("title", "description", "user__username")
    readonly_fields = ("embed_code", "created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("user", "title", "description")}),
        ("Progress", {"fields": ("current_value", "target_value", "color")}),
        ("Embedding", {"fields": ("public", "embed_code")}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ("email", "amount", "donation_type", "status", "created_at", "display_name")
    list_filter = ("donation_type", "status", "created_at", "anonymous")
    search_fields = ("email", "message", "user__username", "user__email")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            "Donation Information",
            {"fields": ("user", "email", "amount", "donation_type", "status", "message", "anonymous")},
        ),
        (
            "Stripe Information",
            {"fields": ("stripe_payment_intent_id", "stripe_subscription_id", "stripe_customer_id")},
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    def display_name(self, obj):
        return obj.display_name

    display_name.short_description = "Name"


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ("name", "badge_type", "is_active", "created_by", "created_at")
    list_filter = ("badge_type", "is_active")
    search_fields = ("name", "description")


@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    list_display = ("user", "badge", "award_method", "awarded_at")
    list_filter = ("award_method", "badge__badge_type")
    search_fields = ("user__username", "badge__name")
    date_hierarchy = "awarded_at"


@admin.register(LearningStreak)
class LearningStreakAdmin(admin.ModelAdmin):
    list_display = ("user", "current_streak", "longest_streak", "last_engagement")
    search_fields = ("user__username",)


# Register Peer Challenge models
@admin.register(PeerChallenge)
class PeerChallengeAdmin(admin.ModelAdmin):
    list_display = ("title", "creator", "quiz", "status", "created_at", "expires_at")
    list_filter = ("status", "created_at")
    search_fields = ("title", "description", "creator__username")
    raw_id_fields = ("creator", "quiz")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("creator", "quiz", "title", "description")}),
        ("Status", {"fields": ("status", "expires_at")}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )


@admin.register(PeerChallengeInvitation)
class PeerChallengeInvitationAdmin(admin.ModelAdmin):
    list_display = ("challenge", "participant", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("challenge__title", "participant__username", "participant__email")
    raw_id_fields = ("challenge", "participant", "user_quiz")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("challenge", "participant")}),
        ("Status", {"fields": ("status", "user_quiz")}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )


# Register Quiz-related models
@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ("title", "creator", "subject", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("title", "description", "creator__username", "id__exact")
    autocomplete_fields = ["creator", "subject"]


@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    list_display = ("text", "quiz", "question_type", "points", "order")
    list_filter = ("question_type",)
    search_fields = ("text", "quiz__title")
    autocomplete_fields = ["quiz"]


@admin.register(QuizOption)
class QuizOptionAdmin(admin.ModelAdmin):
    list_display = ("text", "question", "is_correct", "order")
    list_filter = ("is_correct",)
    search_fields = ("text", "question__text")
    autocomplete_fields = ["question"]


@admin.register(MembershipPlan)
class MembershipPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "price_monthly", "price_yearly", "billing_period", "is_active", "is_popular", "order")
    list_filter = ("is_active", "is_popular", "billing_period")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("order", "name")


@admin.register(UserMembership)
class UserMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "status", "billing_period", "start_date", "end_date", "is_active")
    list_filter = ("status", "billing_period", "plan")
    search_fields = ("user__email", "user__username", "stripe_customer_id", "stripe_subscription_id")
    raw_id_fields = ("user", "plan")
    readonly_fields = ("created_at", "updated_at")


@admin.register(MembershipSubscriptionEvent)
class MembershipSubscriptionEventAdmin(admin.ModelAdmin):
    list_display = ("user", "event_type", "created_at")
    list_filter = ("event_type", "created_at")
    search_fields = ("user__email", "user__username", "stripe_event_id")
    raw_id_fields = ("user", "membership")
    readonly_fields = ("created_at",)


@admin.register(Points)
class PointsAdmin(admin.ModelAdmin):
    list_display = ("user", "amount", "reason", "point_type", "awarded_at", "challenge")
    list_filter = ("point_type", "awarded_at")
    search_fields = ("user__username", "user__email", "reason")
    raw_id_fields = ("user", "challenge")
    readonly_fields = ("awarded_at", "updated_at")
    date_hierarchy = "awarded_at"
    fieldsets = (
        (None, {"fields": ("user", "amount", "reason", "point_type")}),
        ("Related Data", {"fields": ("challenge", "current_streak")}),
        ("Timestamps", {"fields": ("awarded_at", "updated_at"), "classes": ("collapse",)}),
    )


@admin.register(VideoRequest)
class VideoRequestAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "category", "requester", "created_at")
    list_filter = ("status", "category")
    search_fields = ("title", "description", "requester__username")


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ("name", "region", "country", "status", "member_count", "created_by", "created_at")
    list_filter = ("status", "country", "created_at")
    search_fields = ("name", "region", "country", "description")
    prepopulated_fields = {"slug": ("name",)}
    raw_id_fields = ("created_by",)
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("name", "slug", "description", "status")}),
        ("Location", {"fields": ("region", "country", "latitude", "longitude")}),
        ("Details", {"fields": ("meeting_schedule", "image", "contact_email", "website", "social_links")}),
        ("Meta", {"fields": ("created_by", "created_at", "updated_at")}),
    )


@admin.register(ChapterMembership)
class ChapterMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "chapter", "role", "status", "joined_at")
    list_filter = ("role", "status", "joined_at")
    search_fields = ("user__username", "chapter__name")
    raw_id_fields = ("chapter", "user")
    readonly_fields = ("joined_at", "updated_at")


@admin.register(ChapterEvent)
class ChapterEventAdmin(admin.ModelAdmin):
    list_display = ("title", "chapter", "event_type", "start_datetime", "status", "rsvp_count", "created_by")
    list_filter = ("event_type", "status", "is_virtual", "start_datetime")
    search_fields = ("title", "description", "chapter__name")
    prepopulated_fields = {"slug": ("title",)}
    raw_id_fields = ("chapter", "created_by")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("chapter", "title", "slug", "description", "event_type", "status")}),
        ("Schedule", {"fields": ("start_datetime", "end_datetime")}),
        ("Location", {"fields": ("location", "is_virtual", "virtual_link")}),
        ("Capacity", {"fields": ("max_attendees",)}),
        ("Media", {"fields": ("image",)}),
        ("Meta", {"fields": ("created_by", "created_at", "updated_at")}),
    )


@admin.register(ChapterEventRSVP)
class ChapterEventRSVPAdmin(admin.ModelAdmin):
    list_display = ("user", "event", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("user__username", "event__title")
    raw_id_fields = ("event", "user")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ChapterApplication)
class ChapterApplicationAdmin(admin.ModelAdmin):
    list_display = ("chapter_name", "region", "applicant", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("chapter_name", "region", "applicant__username")
    raw_id_fields = ("applicant", "reviewed_by")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("applicant", "chapter_name", "region", "country")}),
        ("Application Details", {"fields": ("description", "proposed_schedule", "experience")}),
        ("Review", {"fields": ("status", "reviewed_by", "review_notes")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
