"""System monitoring and management command utilities for admins."""

import logging
from datetime import datetime
from io import StringIO

import psutil
from django.contrib.auth.decorators import user_passes_test
from django.core.management import call_command, find_commands
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)


def is_superuser(user):
    """Check if user is a superuser."""
    return user.is_superuser


def get_system_metrics():
    """Get current system metrics."""
    try:
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()

        # Memory metrics
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()

        # Disk metrics
        disk = psutil.disk_usage("/")

        # Process info
        process = psutil.Process()
        proc_memory = process.memory_info()

        # Get top processes by memory usage
        top_processes = []
        try:
            for proc in psutil.process_iter(["pid", "name", "memory_percent"]):
                try:
                    if proc.memory_percent() > 0.1:  # Only include processes using > 0.1% RAM
                        mem_info = proc.memory_info()
                        top_processes.append(
                            {
                                "pid": proc.pid,
                                "name": proc.name(),
                                "memory_percent": round(proc.memory_percent(), 2),
                                "memory_bytes": mem_info.rss,
                            }
                        )
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass

            # Sort by memory usage and list all above threshold
            top_processes.sort(key=lambda x: x["memory_percent"], reverse=True)
        except Exception as e:
            logger.warning(f"Error getting process list: {e}")
            top_processes = []

        return {
            "cpu": {
                "percent": cpu_percent,
                "count": cpu_count,
                "frequency": psutil.cpu_freq().current if psutil.cpu_freq() else 0,
            },
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent,
                "used": memory.used,
                "free": memory.free,
            },
            "swap": {
                "total": swap.total,
                "used": swap.used,
                "free": swap.free,
                "percent": swap.percent,
            },
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": disk.percent,
            },
            "process": {
                "rss": proc_memory.rss,
                "vms": proc_memory.vms,
            },
            "top_processes": top_processes,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting system metrics: {e}")
        return None


def get_available_commands():
    """Get list of available Django management commands."""
    try:
        commands = []

        for app_config in __import__("django.apps", fromlist=["apps"]).apps.get_app_configs():
            app_name = app_config.name
            try:
                app_commands = find_commands(
                    __import__(f"{app_name}.management.commands", fromlist=["commands"]).__path__[0]
                )
                for command_name in app_commands:
                    commands.append({"app": app_name, "name": command_name, "full_name": command_name})
            except (ImportError, AttributeError):
                pass

        return sorted(commands, key=lambda x: x["name"])
    except Exception as e:
        logger.error(f"Error getting management commands: {e}")
        return []


def run_management_command_worker(command_name):
    """Execute a Django management command and return output."""
    if not command_name:
        raise ValueError("No command specified")

    # Security: Only allow whitelisted commands
    SAFE_COMMANDS = {
        "migrate",
        "collectstatic",
        "create_test_data",
        "createsuperuser",
        "cleanup",
    }

    command_base = command_name.split(".")[-1] if "." in command_name else command_name

    if command_base not in SAFE_COMMANDS:
        raise ValueError(f"Command '{command_name}' is not whitelisted")

    try:
        output = []
        out = StringIO()
        call_command(command_base, stdout=out)
        output = out.getvalue().split("\n")
        return output
    except Exception as e:
        logger.error(f"Error running command {command_name}: {str(e)}")
        return [f"Error: {str(e)}"]


@user_passes_test(is_superuser)
def system_dashboard(request):
    """Display system monitoring dashboard and management commands."""
    metrics = get_system_metrics()
    commands = get_available_commands()

    context = {
        "metrics": metrics,
        "commands": commands,
    }

    return render(request, "admin/system_dashboard.html", context)


@require_http_methods(["GET"])
@user_passes_test(is_superuser)
def system_metrics_api(request):
    """API endpoint to get current system metrics."""
    metrics = get_system_metrics()
    if metrics:
        return JsonResponse(metrics)
    return JsonResponse({"error": "Unable to fetch metrics"}, status=500)


@require_http_methods(["POST"])
@user_passes_test(is_superuser)
def run_management_command(request):
    """Run a management command."""
    try:
        command_name = request.POST.get("command", "").strip()

        if not command_name:
            return JsonResponse({"error": "No command specified"}, status=400)

        output = run_management_command_worker(command_name)

        return JsonResponse(
            {
                "success": True,
                "command": command_name,
                "output": output,
                "timestamp": datetime.now().isoformat(),
            }
        )
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=403)
    except Exception as e:
        logger.error(f"Error running command: {e}")
        return JsonResponse({"error": str(e)}, status=500)
