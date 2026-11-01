import logging
from datetime import timedelta

from django.apps import apps
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Case, Count, F, FloatField, Sum, When
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .admin_system import (
    get_available_commands,
    get_system_metrics,
    run_management_command_worker,
)
from .models import Goods, OrderItem, Storefront

logger = logging.getLogger(__name__)


@staff_member_required
def admin_dashboard(request):
    """Admin dashboard showing model statistics."""
    # Add admin site context
    context = dict(
        admin.site.each_context(request),
        title="Dashboard",
    )

    # Get the date range for historical data (last 30 days)
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30)

    # Function to get historical data for a model
    def get_model_history(model):
        date_field = next(
            (f.name for f in model._meta.fields if f.name in ["created_at", "date_joined"]),
            None,
        )
        if not date_field:
            return []

        filter_kwargs = {f"{date_field}__range": (start_date, end_date)}
        return (
            model.objects.filter(**filter_kwargs)
            .annotate(date=TruncDate(date_field))
            .values("date")
            .annotate(count=Count("id"))
            .order_by("date")
        )

    # Get all registered models
    models_to_track = []
    for app_config in apps.get_app_configs():
        for model in app_config.get_models():
            # Skip models without creation date fields
            if any(f.name in ["created_at", "date_joined"] for f in model._meta.fields):
                # Get admin URL if model is registered in admin
                admin_url = None
                if admin.site.is_registered(model):
                    admin_url = reverse(f"admin:{model._meta.app_label}_{model._meta.model_name}_changelist")

                models_to_track.append(
                    {"model": model, "title": model._meta.verbose_name_plural.title(), "admin_url": admin_url}
                )

    stats = []
    for model_info in models_to_track:
        model = model_info["model"]
        current_count = model.objects.count()

        # Get historical data
        history_data = get_model_history(model)
        history_list = [0] * 30  # Initialize with zeros

        # Fill in actual counts
        for entry in history_data:
            days_ago = (end_date.date() - entry["date"]).days
            if 0 <= days_ago < 30:
                history_list[days_ago] = entry["count"]

        stats.append(
            {
                "title": model_info["title"],
                "count": current_count,
                "history": list(reversed(history_list)),  # Reverse to show oldest to newest
                "admin_url": model_info["admin_url"],
            }
        )

    # Sort stats by total count descending
    stats.sort(key=lambda x: x["count"], reverse=True)

    context["stats"] = stats

    # Merchandise-specific analytics
    # Sales data with proper price handling (discounts vs regular)
    merchandise_sales = (
        OrderItem.objects.filter(order__status="completed", order__created_at__date__gte=start_date.date())
        .annotate(
            sale_date=TruncDate("order__created_at"),
            actual_price=Case(
                When(discounted_price_at_purchase__isnull=False, then=F("discounted_price_at_purchase")),
                default=F("price_at_purchase"),
                output_field=FloatField(),
            ),
        )
        .values("sale_date")
        .annotate(total_sales=Sum("actual_price"), total_items=Sum("quantity"))
        .order_by("sale_date")
    )

    # Top performing products
    top_products = (
        Goods.objects.filter(orderitem__order__status="completed", orderitem__order__created_at__gte=start_date)
        .annotate(
            total_sold=Sum("orderitem__quantity"),
            total_revenue=Sum(
                Case(
                    When(
                        orderitem__discounted_price_at_purchase__isnull=False,
                        then=F("orderitem__discounted_price_at_purchase"),
                    ),
                    default=F("orderitem__price_at_purchase"),
                    output_field=FloatField(),
                )
            ),
        )
        .order_by("-total_revenue")[:5]
    )

    # Top storefronts by sales
    top_storefronts = (
        Storefront.objects.filter(
            goods__orderitem__order__status="completed", goods__orderitem__order__created_at__gte=start_date
        )
        .annotate(
            total_sales=Sum(
                Case(
                    When(
                        goods__orderitem__discounted_price_at_purchase__isnull=False,
                        then=F("goods__orderitem__discounted_price_at_purchase"),
                    ),
                    default=F("goods__orderitem__price_at_purchase"),
                    output_field=FloatField(),
                )
            ),
            total_orders=Count("goods__orderitem__order", distinct=True),
        )
        .order_by("-total_sales")[:5]
    )

    # Sales data structure for charts
    sales_data = {
        "dates": [(start_date.date() + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(30)],
        "daily_sales": [0] * 30,
        "daily_items": [0] * 30,
    }

    for entry in merchandise_sales:
        days_ago = (end_date.date() - entry["sale_date"]).days
        if 0 <= days_ago < 30:
            sales_data["daily_sales"][days_ago] = float(entry["total_sales"] or 0)
            sales_data["daily_items"][days_ago] = entry["total_items"] or 0

    # Reverse to show chronological order
    sales_data["daily_sales"].reverse()
    sales_data["daily_items"].reverse()
    sales_data["dates"].reverse()

    # Top sellers (teachers) analytics
    top_sellers = (
        Storefront.objects.filter(goods__orderitem__order__status="completed")
        .annotate(
            seller=F("teacher__username"),
            total_sales=Sum(
                Case(
                    When(
                        goods__orderitem__discounted_price_at_purchase__isnull=False,
                        then=F("goods__orderitem__discounted_price_at_purchase"),
                    ),
                    default=F("goods__orderitem__price_at_purchase"),
                    output_field=FloatField(),
                )
            ),
        )
        .values("seller", "total_sales")
        .order_by("-total_sales")[:5]
    )

    context.update(
        {
            "stats": stats,
            "merchandise_sales": sales_data,
            "top_products": top_products,
            "top_storefronts": top_storefronts,
            "top_sellers": top_sellers,
            "total_revenue": sum(sales_data["daily_sales"]),
            "total_items_sold": sum(sales_data["daily_items"]),
            "start_date": start_date.date(),
            "end_date": end_date.date(),
        }
    )

    return render(request, "admin/dashboard.html", context)


def is_superuser(user):
    """Check if user is a superuser."""
    return user.is_superuser


@user_passes_test(is_superuser)
def system_dashboard(request):
    """Display system metrics and management commands dashboard."""
    metrics = get_system_metrics()
    commands = get_available_commands()

    return render(
        request,
        "admin/system_dashboard.html",
        {
            "metrics": metrics,
            "commands": commands,
            "title": "System Dashboard",
        },
    )


@user_passes_test(is_superuser)
@require_http_methods(["GET"])
def system_metrics_api(request):
    """API endpoint to get current system metrics as JSON."""
    metrics = get_system_metrics()
    return JsonResponse(metrics)


@user_passes_test(is_superuser)
@require_http_methods(["POST"])
def run_management_command(request):
    """Execute a whitelisted Django management command."""
    command_name = request.POST.get("command", "").strip()

    # Whitelist of allowed commands
    allowed_commands = {
        "migrate": "Run database migrations",
        "collectstatic": "Collect static files",
        "create_test_data": "Create sample data for testing",
        "createsuperuser": "Create a new superuser",
        "cleanup": "Clean up old data",
    }

    if not command_name or command_name not in allowed_commands:
        return JsonResponse(
            {"error": f"Command not allowed. Allowed commands: {', '.join(allowed_commands.keys())}"}, status=400
        )

    try:
        output = run_management_command_worker(command_name)
        return JsonResponse(
            {
                "output": output,
                "command": command_name,
                "status": "success",
            }
        )
    except Exception as e:
        logger.error(f"Error running management command {command_name}: {str(e)}")
        return JsonResponse(
            {
                "error": str(e),
                "command": command_name,
                "status": "error",
            },
            status=500,
        )
