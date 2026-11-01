import logging
from datetime import timedelta
from typing import Any, Optional

import requests
import stripe
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import models
from django.utils import timezone

User = get_user_model()
logger = logging.getLogger(__name__)


def can_access_classroom(user: User, classroom) -> bool:
    """Return True if the user can access the classroom."""
    if not user or not user.is_authenticated:
        return False
    if user == classroom.teacher:
        return True
    if classroom.course_id:
        return classroom.course.enrollments.filter(student=user, status="approved").exists()
    return True


def send_slack_message(message):
    """Send message to Slack webhook"""
    webhook_url = settings.SLACK_WEBHOOK_URL
    if not webhook_url:
        return False

    try:
        response = requests.post(webhook_url, json={"text": message})
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def format_currency(amount):
    """Format amount as currency"""
    return f"${amount:.2f}"


def get_or_create_cart(request):
    """Helper function to get or create a cart for both logged in and guest users."""
    from web.models import Cart

    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        cart, created = Cart.objects.get_or_create(session_key=session_key)
    return cart


def calculate_user_points_for_period(user, days=None):
    """Calculate points for a user within a specific period

    Args:
        user: The user to calculate points for
        days: Number of days to include (None for all-time)
    """
    from web.models import Points

    queryset = Points.objects.filter(user=user)

    if days is not None:
        period_start = timezone.now() - timedelta(days=days)
        queryset = queryset.filter(awarded_at__gte=period_start)

    return queryset.aggregate(total=models.Sum("amount"))["total"] or 0


def calculate_user_weekly_points(user):
    """Calculate weekly points for a user"""
    return calculate_user_points_for_period(user, days=7)


def calculate_user_monthly_points(user):
    """Calculate monthly points for a user"""
    return calculate_user_points_for_period(user, days=30)


def calculate_user_total_points(user):
    """Calculate total points for a user"""
    return calculate_user_points_for_period(user)


def calculate_user_streak(user):
    """Calculate current streak for a user"""
    from web.models import Points

    streak_record = (
        Points.objects.filter(user=user, point_type="streak", current_streak__isnull=False)
        .order_by("-awarded_at")
        .first()
    )

    return streak_record.current_streak if streak_record else 0


def calculate_and_update_user_streak(user, challenge):
    from django.db import transaction

    from web.models import Challenge, ChallengeSubmission, Points

    with transaction.atomic():
        # Calculate and update streak
        last_week = challenge.week_number - 1
        if last_week > 0:
            last_week_challenge = Challenge.objects.filter(week_number=last_week).first()
            if last_week_challenge:
                last_week_submission = ChallengeSubmission.objects.filter(
                    user=user, challenge=last_week_challenge
                ).exists()

                if last_week_submission:
                    # User completed consecutive weeks, calculate their current streak
                    streak_points = (
                        Points.objects.filter(user=user, point_type="streak").order_by("-awarded_at").first()
                    )

                    current_streak = 1
                    if streak_points and streak_points.current_streak:
                        current_streak = streak_points.current_streak + 1

                    # Record the updated streak
                    Points.objects.create(
                        user=user,
                        challenge=None,
                        amount=0,  # Just a record, no points awarded for the streak itself
                        reason=f"Current streak: {current_streak}",
                        point_type="streak",
                        current_streak=current_streak,
                    )

                    # Award bonus points for streak milestones
                    if current_streak > 0 and current_streak % 5 == 0:
                        bonus = current_streak // 5 * 5  # 5 points per milestone
                        Points.objects.create(
                            user=user,
                            challenge=None,
                            amount=bonus,
                            reason=f"Streak milestone bonus ({current_streak} weeks)",
                            point_type="bonus",
                        )


def get_user_global_rank(user):
    """Calculate a user's global rank based on total points."""
    from django.db.models import Sum

    from web.models import Points

    # Skip if user is a teacher or not authenticated
    if not user or not user.is_authenticated or user.profile.is_teacher:
        return None

    # Get user's points
    user_points = calculate_user_total_points(user)

    # If user has no points, they're not ranked
    if not user_points:
        return None

    # Count users with more points (excluding teachers)
    users_ahead = (
        Points.objects.filter(user__profile__is_teacher=False)
        .values("user")
        .annotate(total=Sum("amount"))
        .filter(total__gt=user_points)
        .count()
    )

    # User's rank is users ahead + 1 (tied users all get same rank)
    return users_ahead + 1


def get_user_weekly_rank(user):
    """Calculate a user's weekly rank based on points in the last 7 days."""
    from datetime import timedelta

    from django.db.models import Sum
    from django.utils import timezone

    from web.models import Points

    # Skip if user is a teacher or not authenticated
    if not user or not user.is_authenticated or user.profile.is_teacher:
        return None

    # Define time period
    one_week_ago = timezone.now() - timedelta(days=7)

    # Get user's weekly points
    user_points = calculate_user_weekly_points(user)

    # If user has no weekly points, they're not ranked
    if not user_points:
        return None

    # Count users with more weekly points (excluding teachers)
    users_ahead = (
        Points.objects.filter(awarded_at__gte=one_week_ago, user__profile__is_teacher=False)
        .values("user")
        .annotate(total=Sum("amount"))
        .filter(total__gt=user_points)
        .count()
    )

    # User's rank is users ahead + 1 (tied users all get same rank)
    return users_ahead + 1


def get_user_monthly_rank(user):
    """Calculate a user's monthly rank based on points in the last 30 days."""
    from datetime import timedelta

    from django.db.models import Sum
    from django.utils import timezone

    from web.models import Points

    # Skip if user is a teacher or not authenticated
    if not user or not user.is_authenticated or user.profile.is_teacher:
        return None

    # Define time period
    one_month_ago = timezone.now() - timedelta(days=30)

    # Get user's monthly points
    user_points = calculate_user_monthly_points(user)

    # If user has no monthly points, they're not ranked
    if not user_points:
        return None

    # Count users with more monthly points (excluding teachers)
    users_ahead = (
        Points.objects.filter(awarded_at__gte=one_month_ago, user__profile__is_teacher=False)
        .values("user")
        .annotate(total=Sum("amount"))
        .filter(total__gt=user_points)
        .count()
    )

    # User's rank is users ahead + 1 (tied users all get same rank)
    return users_ahead + 1


def get_leaderboard(current_user=None, period=None, limit=10):
    """
    Get leaderboard data based on period (None/global, weekly, or monthly)
    Returns a list of users with their points sorted by total points
    Excludes teachers from the leaderboard
    """
    from datetime import timedelta

    from django.db.models import Count, Sum
    from django.utils import timezone

    from web.models import Points, User

    # Define time periods if needed
    one_week_ago = timezone.now() - timedelta(days=7)
    one_month_ago = timezone.now() - timedelta(days=30)

    # Get leaderboard entries from database with proper sorting
    if period == "weekly":
        # Get weekly leaderboard
        leaderboard_entries = (
            Points.objects.filter(
                awarded_at__gte=one_week_ago, user__profile__is_teacher=False, user__profile__is_profile_public=True
            )
            .values("user")
            .annotate(points=Sum("amount"))
            .filter(points__gt=0)
            .order_by("-points")[:limit]
        )

    elif period == "monthly":
        # Get monthly leaderboard
        leaderboard_entries = (
            Points.objects.filter(
                awarded_at__gte=one_month_ago, user__profile__is_teacher=False, user__profile__is_profile_public=True
            )
            .values("user")
            .annotate(points=Sum("amount"))
            .filter(points__gt=0)
            .order_by("-points")[:limit]
        )

    else:  # Global leaderboard
        # Get global leaderboard
        leaderboard_entries = (
            Points.objects.filter(user__profile__is_teacher=False, user__profile__is_profile_public=True)
            .values("user")
            .annotate(points=Sum("amount"))
            .filter(points__gt=0)
            .order_by("-points")[:limit]
        )

    # Get user IDs and fetch user data efficiently
    user_ids = [entry["user"] for entry in leaderboard_entries]
    users = {
        user.id: user
        for user in User.objects.filter(id__in=user_ids).annotate(
            challenge_count=Count("challengesubmission", distinct=True)
        )
    }

    # Prepare the final leaderboard with all necessary data
    leaderboard_data = []

    # Calculate ranks properly accounting for ties
    current_rank = 1
    prev_points = None

    for i, entry in enumerate(leaderboard_entries):
        user_id = entry["user"]
        points = entry["points"]
        user = users.get(user_id)

        if user:
            # Handle ties properly (same points = same rank)
            if prev_points is not None and points < prev_points:
                current_rank = i + 1

            # Build entry data
            entry_data = {
                "user": user,
                "rank": current_rank,  # Store calculated rank in entry
                "points": points,
                "weekly_points": calculate_user_weekly_points(user) if period != "weekly" else points,
                "monthly_points": calculate_user_monthly_points(user) if period != "monthly" else points,
                "total_points": calculate_user_total_points(user) if period is not None else points,
                "current_streak": calculate_user_streak(user),
                "challenge_count": getattr(user, "challenge_count", 0),
            }
            leaderboard_data.append(entry_data)
            prev_points = points

    # Calculate user's rank using the appropriate function
    user_rank = None
    if current_user and current_user.is_authenticated and not current_user.profile.is_teacher:
        if period == "weekly":
            user_rank = get_user_weekly_rank(current_user)
        elif period == "monthly":
            user_rank = get_user_monthly_rank(current_user)
        else:
            user_rank = get_user_global_rank(current_user)

    return leaderboard_data, user_rank


# Helper functions that would be defined elsewhere
def get_cached_leaderboard_data(user, period, limit, cache_key, cache_timeout):
    """Get leaderboard data from cache or fetch fresh data"""
    data = cache.get(cache_key)
    if data is None:
        entries, rank = get_leaderboard(user, period=period, limit=limit)
        cache.set(cache_key, (entries, rank), cache_timeout)
    else:
        entries, rank = data
    return entries, rank


def get_user_points(user):
    """Calculate points for a user with error handling"""
    try:
        return {
            "total": calculate_user_total_points(user),
            "weekly": calculate_user_weekly_points(user),
            "monthly": calculate_user_monthly_points(user),
        }
    except Exception as e:
        logger.error(f"Error calculating user points: {e}")
        return {"total": 0, "weekly": 0, "monthly": 0}


def get_cached_challenge_entries():
    """Get challenge entries from cache or fetch fresh data"""
    from web.models import ChallengeSubmission

    challenge_data = cache.get("challenge_leaderboard")
    if challenge_data is None:
        try:
            challenge_entries = (
                ChallengeSubmission.objects.select_related("user", "challenge")
                .filter(points_awarded__gt=0)
                .order_by("-points_awarded")[:10]
            )
            cache.set("challenge_leaderboard", challenge_entries, 60 * 15)
        except Exception as e:
            logger.error(f"Error retrieving challenge entries: {e}")
            challenge_entries = []
    else:
        challenge_entries = challenge_data
    return challenge_entries


def create_leaderboard_context(
    global_entries,
    weekly_entries,
    monthly_entries,
    challenge_entries,
    user_rank,
    user_weekly_rank,
    user_monthly_rank,
    user_total_points,
    user_weekly_points,
    user_monthly_points,
):
    """Create context dictionary for the leaderboard template"""
    return {
        "global_entries": global_entries,
        "weekly_entries": weekly_entries,
        "monthly_entries": monthly_entries,
        "challenge_entries": challenge_entries,
        "user_rank": user_rank,
        "user_weekly_rank": user_weekly_rank,
        "user_monthly_rank": user_monthly_rank,
        "user_total_points": user_total_points,
        "user_weekly_points": user_weekly_points,
        "user_monthly_points": user_monthly_points,
    }


def setup_stripe() -> None:
    """
    Initialize Stripe API with the secret key from settings.
    Verifies that the key is properly configured.

    Raises:
        ValueError: If STRIPE_SECRET_KEY is not configured
    """
    if not settings.STRIPE_SECRET_KEY:
        logger.warning("STRIPE_SECRET_KEY is not configured. Stripe functionality will not work properly.")
        raise ValueError("STRIPE_SECRET_KEY is not configured. Please set a valid key in settings.")

    stripe.api_key = settings.STRIPE_SECRET_KEY


def get_stripe_customer(user: "User") -> Optional["stripe.Customer"]:
    """
    Retrieve or create a Stripe customer for the given user.

    Args:
        user: The user to create or retrieve a Stripe customer for

    Returns:
        Optional[stripe.Customer]: The Stripe customer object, or None if an error occurs

    Raises:
        ValueError: If the user does not have a membership object
        stripe.error.StripeError: If there's an error with the Stripe API
    """
    try:
        setup_stripe()  # This may raise ValueError if STRIPE_SECRET_KEY is not configured

        if not user.membership.stripe_customer_id:
            # Create a new customer
            customer = stripe.Customer.create(
                email=user.email,
                name=f"{user.first_name} {user.last_name}".strip(),
                metadata={"user_id": user.id},
            )

            # Save the customer ID to the user membership
            if hasattr(user, "membership"):
                user.membership.stripe_customer_id = customer.id
                user.membership.save(update_fields=["stripe_customer_id"])
            else:
                raise ValueError(f"User {user.email} does not have a membership object")

            return customer

        # Get existing customer
        return stripe.Customer.retrieve(user.membership.stripe_customer_id)

    except stripe.error.StripeError:
        logger.exception(f"Error retrieving Stripe customer for user {user.email}")
        return None


def _attach_payment_method(customer_id: str, payment_method_id: str) -> bool:
    """
    Attach a payment method to a customer and set it as default.

    Args:
        customer_id: The Stripe customer ID
        payment_method_id: The Stripe payment method ID

    Returns:
        bool: True if successful, False otherwise

    Notes:
        - Centralizes payment method attachment logic to ensure consistency
        - Contains error handling to prevent exceptions from propagating upward
        - Logs errors for debugging purposes
    """
    try:
        # Attach payment method to customer
        stripe.PaymentMethod.attach(payment_method_id, customer=customer_id)

        # Set as default payment method
        stripe.Customer.modify(customer_id, invoice_settings={"default_payment_method": payment_method_id})

        # Log success for tracking purposes
        logger.info(f"Successfully attached payment method {payment_method_id} to customer {customer_id}")
        return True
    except stripe.error.StripeError:
        logger.exception(f"Error attaching payment method {payment_method_id} to customer {customer_id}")
        return False


def _create_new_subscription(
    customer_id: str, price_id: str, user_id: int, plan_id: int, billing_period: str
) -> "stripe.Subscription":
    """
    Create a new Stripe subscription.

    Args:
        customer_id: The Stripe customer ID
        price_id: The Stripe price ID
        user_id: The user's ID
        plan_id: The membership plan ID
        billing_period: Either "monthly" or "yearly"

    Returns:
        stripe.Subscription: The newly created subscription

    Notes:
        - Standardizes subscription creation with consistent parameters
        - Includes relevant metadata for subscription tracking
        - Uses "allow_incomplete" to handle payment issues gracefully
    """
    logger.info(f"Creating new subscription for user {user_id} with plan {plan_id} ({billing_period})")
    return stripe.Subscription.create(
        customer=customer_id,
        items=[{"price": price_id}],
        payment_behavior="allow_incomplete",
        metadata={"user_id": user_id, "plan_id": plan_id, "billing_period": billing_period},
    )


def _update_existing_subscription(subscription_id: str, price_id: str) -> "stripe.Subscription":
    """
    Update an existing Stripe subscription with a new price.

    Args:
        subscription_id: The Stripe subscription ID
        price_id: The new Stripe price ID

    Returns:
        stripe.Subscription: The updated subscription

    Notes:
        - Handles changing subscription plans without cancellation
        - Creates prorations for billing adjustments
        - Uses "allow_incomplete" to handle payment requirement scenarios
    """
    logger.info(f"Updating subscription {subscription_id} with new price {price_id}")
    return stripe.Subscription.modify(
        subscription_id,
        items=[{"price": price_id}],
        payment_behavior="allow_incomplete",
        proration_behavior="create_prorations",
    )


def create_subscription(user: "User", plan_id: int, payment_method_id: str, billing_period: str) -> dict[str, Any]:
    """
    Create a new subscription or update an existing one for the user.

    Args:
        user: The user to create/update a subscription for
        plan_id: The ID of the membership plan
        payment_method_id: The Stripe payment method ID
        billing_period: Either "monthly" or "yearly"

    Returns:
        dict: Contains 'success' (bool) and either 'error' (str) or 'subscription' (object)

    Notes:
        - This function orchestrates the entire subscription lifecycle
        - Input validation occurs early to fail fast before making API calls
        - Uses database transactions to maintain consistency across operations
        - Handles multiple subscription scenarios:
          1. User with no subscription -> create new
          2. User with active subscription -> update price
          3. User with canceled subscription -> create new
          4. User with subscription not found in Stripe -> create new
        - Error handling is comprehensive with specific error messages
        - Potential race conditions are mitigated through transaction isolation
        - The database is updated only after successful Stripe operations
    """
    from django.db import transaction

    from .models import MembershipPlan

    try:
        # Initialize Stripe API with secret key and verify configuration
        setup_stripe()

        # Validate membership plan existence
        try:
            plan = MembershipPlan.objects.get(id=plan_id)
        except MembershipPlan.DoesNotExist:
            logger.warning(f"Membership plan not found: {plan_id}")
            return {"success": False, "error": "Membership plan not found"}

        # Validate billing period option
        if billing_period not in ["monthly", "yearly"]:
            logger.warning(f"Invalid billing period: {billing_period}")
            return {"success": False, "error": "Invalid billing period"}

        # Determine appropriate price ID based on billing period
        if billing_period == "monthly":
            price_id = plan.stripe_monthly_price_id
        else:
            price_id = plan.stripe_yearly_price_id

        # Verify price configuration
        if not price_id:
            logger.warning(f"No price ID for {billing_period} billing on plan {plan_id}")
            return {"success": False, "error": f"No price ID configured for {billing_period} billing"}

        # Use transaction to maintain database consistency and prevent race conditions
        with transaction.atomic():
            # Get or create customer - this must succeed before proceeding
            customer = get_stripe_customer(user)
            if not customer:
                logger.error(f"Failed to create/retrieve Stripe customer for user {user.id}")
                return {"success": False, "error": "Failed to create or retrieve customer"}

            # Attach payment method to customer and set as default
            if not _attach_payment_method(customer.id, payment_method_id):
                logger.error(f"Failed to attach payment method {payment_method_id} for user {user.id}")
                return {"success": False, "error": "Failed to attach payment method"}

            # Handle existing subscription scenario with fresh state check
            if hasattr(user, "membership") and user.membership.stripe_subscription_id:
                # Verify subscription exists in Stripe to prevent errors
                try:
                    existing_sub = stripe.Subscription.retrieve(user.membership.stripe_subscription_id)

                    # Determine if we should update or create based on subscription status
                    if existing_sub.status not in ["canceled", "incomplete_expired"]:
                        # Update the existing subscription with new price
                        subscription = _update_existing_subscription(user.membership.stripe_subscription_id, price_id)
                        logger.info(f"Updated subscription {subscription.id} for user {user.id}")
                    else:
                        # Create new subscription for previously canceled subscription
                        subscription = _create_new_subscription(customer.id, price_id, user.id, plan.id, billing_period)
                        logger.info(
                            f"Created new subscription {subscription.id} for user {user.id} (replacing canceled sub)"
                        )
                except stripe.error.InvalidRequestError:
                    # Subscription not found in Stripe, create a new one
                    logger.warning(
                        f"Subscription {user.membership.stripe_subscription_id} not found in Stripe for user {user.id}"
                    )
                    subscription = _create_new_subscription(customer.id, price_id, user.id, plan.id, billing_period)
                    logger.info(f"Created new subscription {subscription.id} (previous not found)")
            else:
                # User has no existing subscription, create a new one
                subscription = _create_new_subscription(customer.id, price_id, user.id, plan.id, billing_period)
                logger.info(f"Created first subscription {subscription.id} for user {user.id}")

            # Update user membership with subscription details in database
            update_success = update_membership_from_subscription(user, subscription)
            if not update_success:
                logger.error(f"Failed to update membership from subscription {subscription.id} for user {user.id}")
                # We don't return an error here to avoid orphaned subscriptions
                # The subscription was created in Stripe but our DB update failed

            return {"success": True, "subscription": subscription}

    except stripe.error.CardError as e:
        # Card-specific errors have user-facing messages
        logger.exception(f"Card error for user {user.email}")
        return {"success": False, "error": str(e.user_message)}
    except stripe.error.StripeError:
        # Generic Stripe API errors
        logger.exception(f"Stripe error for user {user.email}")
        return {"success": False, "error": "An error occurred with our payment processor"}
    except Exception:
        # Catch-all for unexpected errors
        logger.exception(f"Error creating subscription for user {user.email}")
        return {"success": False, "error": "An unexpected error occurred"}


def cancel_subscription(user: "User") -> dict[str, Any]:
    """
    Cancels the user's active Stripe subscription at period end, if any.
    Return {'success': bool, 'error': str, 'subscription': stripe.Subscription?}.
    """
    from .models import MembershipSubscriptionEvent

    try:
        setup_stripe()

        if not hasattr(user, "membership") or not user.membership.stripe_subscription_id:
            return {"success": False, "error": "No active subscription found"}

        membership = user.membership

        # Cancel subscription at period end
        subscription = stripe.Subscription.modify(membership.stripe_subscription_id, cancel_at_period_end=True)

        # Update membership status
        membership.cancel_at_period_end = True
        membership.save(update_fields=["cancel_at_period_end"])

        # Record cancellation event
        MembershipSubscriptionEvent.objects.create(
            user=user,
            membership=membership,
            event_type="canceled",
            data={"subscription_id": subscription.id, "canceled_at": timezone.now().isoformat()},
        )

        return {"success": True, "subscription": subscription}

    except stripe.error.StripeError:
        logger.exception(f"Error canceling subscription for user {user.email}")
        return {"success": False, "error": "An error occurred with our payment processor"}
    except Exception:
        logger.exception(f"Error canceling subscription for user {user.email}")
        return {"success": False, "error": "An unexpected error occurred"}


def reactivate_subscription(user: "User") -> dict[str, Any]:
    """
    Reactivates a subscription that was previously scheduled for cancellation.
    Returns a dictionary with "success" and optional keys "error" or "subscription".

    Args:
        user: The user whose subscription to reactivate

    Returns:
        dict: A dictionary with 'success' (bool) and either 'error' (str) or 'subscription' (object)
    """
    from .models import MembershipSubscriptionEvent

    try:
        setup_stripe()

        if not hasattr(user, "membership") or not user.membership.stripe_subscription_id:
            return {"success": False, "error": "No subscription found"}

        membership = user.membership

        # Check if the subscription is scheduled to be canceled
        if not membership.cancel_at_period_end:
            return {"success": False, "error": "Subscription is not scheduled for cancellation"}

        # Retrieve the subscription to check its status
        subscription = stripe.Subscription.retrieve(membership.stripe_subscription_id)

        # Check if the subscription has already been fully canceled (not just scheduled for cancellation)
        if subscription.status == "canceled":
            return {"success": False, "error": "Subscription has already been fully canceled and cannot be reactivated"}

        # Reactivate subscription (only if it's still active but scheduled for cancellation)
        subscription = stripe.Subscription.modify(membership.stripe_subscription_id, cancel_at_period_end=False)

        # Update membership status
        membership.cancel_at_period_end = False
        membership.save(update_fields=["cancel_at_period_end"])

        # Record reactivation event
        MembershipSubscriptionEvent.objects.create(
            user=user,
            membership=membership,
            event_type="reactivated",
            data={"subscription_id": subscription.id, "reactivated_at": timezone.now().isoformat()},
        )

        return {"success": True, "subscription": subscription}

    except stripe.error.StripeError:
        logger.exception(f"Error reactivating subscription for user {user.email}")
        return {"success": False, "error": "An error occurred with our payment processor"}
    except Exception:
        logger.exception(f"Error reactivating subscription for user {user.email}")
        return {"success": False, "error": "An unexpected error occurred"}


def update_membership_from_subscription(user: "User", subscription: dict) -> bool:
    """
    Update the user's membership details based on the Stripe subscription.

    Args:
        user: The user whose membership is being updated
        subscription: The Stripe subscription object

    Returns:
        bool: True if update was successful, False otherwise
    """
    from .models import MembershipPlan, MembershipSubscriptionEvent, UserMembership

    try:
        # Get the subscription item
        subscription_item = subscription["items"]["data"][0]
        price_id = subscription_item["price"]["id"]

        # Find the plan based on price ID
        try:
            plan = MembershipPlan.objects.filter(
                models.Q(stripe_monthly_price_id=price_id) | models.Q(stripe_yearly_price_id=price_id)
            ).first()

            if not plan:
                logger.error(f"No plan found for price ID {price_id}")
                return False
        except Exception:
            logger.exception(f"Error finding plan for price ID {price_id}")
            return False

        # Determine billing period
        if price_id == plan.stripe_monthly_price_id:
            billing_period = "monthly"
        else:
            billing_period = "yearly"

        # Get or create user membership
        membership, created = UserMembership.objects.get_or_create(
            user=user,
            defaults={
                "plan": plan,
                "status": subscription["status"],
                "billing_period": billing_period,
                "stripe_subscription_id": subscription["id"],
                "stripe_customer_id": subscription["customer"],
            },
        )

        if not created:
            # Update existing membership
            membership.plan = plan
            membership.status = subscription["status"]
            membership.billing_period = billing_period
            membership.stripe_subscription_id = subscription["id"]
            membership.stripe_customer_id = subscription["customer"]

        # Update dates
        if subscription["status"] in ["active", "trialing"]:
            membership.start_date = timezone.datetime.fromtimestamp(
                subscription["current_period_start"], tz=timezone.utc
            )
            membership.end_date = timezone.datetime.fromtimestamp(subscription["current_period_end"], tz=timezone.utc)

        # Update cancellation status
        membership.cancel_at_period_end = subscription["cancel_at_period_end"]

        # Save changes
        membership.save()

        # Create subscription event
        event_type = "created" if created else "updated"
        MembershipSubscriptionEvent.objects.create(
            user=user,
            membership=membership,
            event_type=event_type,
            data={
                "subscription_id": subscription["id"],
                "status": subscription["status"],
                "billing_period": billing_period,
                "plan_id": plan.id,
            },
        )

        return True

    except Exception:
        logger.exception(f"Error updating membership for user {user.email}")
        return False


def geocode_address(address):
    """
    Convert a text address to latitude and longitude coordinates using Nominatim API.
    Returns a tuple of (latitude, longitude) or None if geocoding fails.
    Follows OpenStreetMap's Nominatim usage policy with built-in rate limiting.
    """
    # Rate limiting - ensure we don't exceed 1 request per second
    rate_limit_key = "nominatim_last_request"
    last_request_time = cache.get(rate_limit_key)

    if last_request_time:
        import time

        current_time = time.time()
        time_since_last_request = current_time - last_request_time

        if time_since_last_request < 1.0:
            # Sleep to maintain 1 request per second rate limit
            time.sleep(1.0 - time_since_last_request)

    if not address:
        logger.debug("Empty address provided to geocode_address")
        return None

    # Check cache first
    normalized_address = address.strip().lower()
    cache_key = f"geocode:{hash(normalized_address)}"
    cached_result = cache.get(cache_key)
    if cached_result:
        logger.debug(f"Using cached geocoding result for: {address}")
        return cached_result

    # Nominatim API URL with custom User-Agent as recommended
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": address, "format": "json", "limit": 1}

    # Headers to comply with Nominatim usage policy
    headers = {"User-Agent": "AlphaOneEducation/1.0 (support@alphaonelabs.com)"}

    try:
        # Update last request timestamp
        import time

        cache.set(rate_limit_key, time.time(), 60 * 5)  # Keep for 5 minutes
        # Use requests with custom headers and params
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()

        data = response.json()

        if data:
            # Get the first result
            first_result = data[0]
            result = (float(first_result["lat"]), float(first_result["lon"]))

            # Cache the result for 24 hours
            cache.set(cache_key, result, 60 * 60 * 24)

            return result

        logger.warning(f"No geocoding results found for address: {address}")
        return None

    except requests.exceptions.RequestException as e:
        logger.error(f"Request error during geocoding: {e}")
        return None
    except Exception as e:
        logger.error(f"Geocoding error: {e}")
        return None
