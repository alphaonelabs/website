# web/virtual_lab/views.py

import json
import logging

import requests
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)


def build_virtual_lab_subjects() -> list[dict[str, object]]:
    """Return subject and lab metadata for virtual lab navigation and landing pages."""
    return [
        {
            "key": "physics",
            "label": _("Physics"),
            "url_name": "virtual_lab:physics_home",
            "labs": [
                {"label": _("Pendulum Motion"), "url_name": "virtual_lab:physics_pendulum"},
                {"label": _("Projectile Motion"), "url_name": "virtual_lab:physics_projectile"},
                {"label": _("Inclined Plane"), "url_name": "virtual_lab:physics_inclined"},
                {"label": _("Mass-Spring Oscillation"), "url_name": "virtual_lab:physics_mass_spring"},
                {"label": _("Basic Electrical Circuit"), "url_name": "virtual_lab:physics_electrical_circuit"},
            ],
        },
        {
            "key": "chemistry",
            "label": _("Chemistry"),
            "url_name": "virtual_lab:chemistry_home",
            "labs": [
                {"label": _("Acid-Base Titration"), "url_name": "virtual_lab:titration"},
                {"label": _("Reaction Rate"), "url_name": "virtual_lab:reaction_rate"},
                {"label": _("Solubility & Saturation"), "url_name": "virtual_lab:solubility"},
                {"label": _("Precipitation Reaction"), "url_name": "virtual_lab:precipitation"},
                {"label": _("pH Indicator"), "url_name": "virtual_lab:ph_indicator"},
            ],
        },
    ]


def render_virtual_lab_page(
    request: HttpRequest, template_name: str, extra_context: dict[str, object] | None = None
) -> HttpResponse:
    """Render a virtual lab template with common navigation context."""
    context = {
        "virtual_lab_subjects": build_virtual_lab_subjects(),
    }
    if extra_context:
        context.update(extra_context)
    return render(request, template_name, context)


def virtual_lab_home(request):
    """
    Renders the Virtual Lab home page (home.html).
    """
    return render_virtual_lab_page(request, "virtual_lab/home.html")


def physics_home(request):
    """Render the Physics lab overview page."""
    return render_virtual_lab_page(request, "virtual_lab/physics/index.html")


def physics_pendulum_view(request):
    """
    Renders the Pendulum Motion simulation page (physics/pendulum.html).
    """
    return render_virtual_lab_page(request, "virtual_lab/physics/pendulum.html")


def physics_projectile_view(request):
    """
    Renders the Projectile Motion simulation page (physics/projectile.html).
    """
    return render_virtual_lab_page(request, "virtual_lab/physics/projectile.html")


def physics_inclined_view(request):
    """
    Renders the Inclined Plane simulation page (physics/inclined.html).
    """
    return render_virtual_lab_page(request, "virtual_lab/physics/inclined.html")


def physics_mass_spring_view(request):
    """
    Renders the Mass-Spring Oscillation simulation page (physics/mass_spring.html).
    """
    return render_virtual_lab_page(request, "virtual_lab/physics/mass_spring.html")


def physics_electrical_circuit_view(request):
    """
    Renders the Electrical Circuit simulation page (physics/circuit.html).
    """
    return render_virtual_lab_page(request, "virtual_lab/physics/circuit.html")


def chemistry_home(request):
    """Render the Chemistry lab overview page."""
    return render_virtual_lab_page(request, "virtual_lab/chemistry/index.html")


def titration_view(request):
    """Render the Acid-Base Titration simulation page."""
    return render_virtual_lab_page(request, "virtual_lab/chemistry/titration.html")


def reaction_rate_view(request):
    """Render the Reaction Rate simulation page."""
    return render_virtual_lab_page(request, "virtual_lab/chemistry/reaction_rate.html")


def solubility_view(request):
    """Render the Solubility and Saturation simulation page."""
    return render_virtual_lab_page(request, "virtual_lab/chemistry/solubility.html")


def precipitation_view(request):
    """Render the Precipitation Reaction simulation page."""
    return render_virtual_lab_page(request, "virtual_lab/chemistry/precipitation.html")


def ph_indicator_view(request):
    """Render the pH Indicator simulation page."""
    return render_virtual_lab_page(request, "virtual_lab/chemistry/ph_indicator.html")


# Piston’s public execute endpoint (rate-limited to 5 req/s) :contentReference[oaicite:0]{index=0}
PISTON_EXECUTE_URL = "https://emkc.org/api/v2/piston/execute"

LANG_FILE_EXT = {
    "python": "py",
    "javascript": "js",
    "c": "c",
    "cpp": "cpp",
}


def code_editor_view(request):
    """Render the virtual lab code editor page."""
    return render_virtual_lab_page(request, "virtual_lab/code_editor/code_editor.html")


@require_POST
def evaluate_code(request):
    """
    Proxy code + stdin to Piston and return its JSON result.
    """
    data = json.loads(request.body)
    source_code = data.get("code", "")
    language = data.get("language", "python")  # e.g. "python","javascript","c","cpp"
    stdin_text = data.get("stdin", "")

    # Package content for Piston
    ext = LANG_FILE_EXT.get(language, "txt")
    files = [{"name": f"main.{ext}", "content": source_code}]
    payload = {
        "language": language,
        "version": "*",  # semver selector; '*' picks latest :contentReference[oaicite:1]{index=1}
        "files": files,
        "stdin": stdin_text,
        "args": [],
    }

    try:
        resp = requests.post(PISTON_EXECUTE_URL, json=payload, timeout=10)
        resp.raise_for_status()
    except requests.RequestException:
        # Log the full details for your own troubleshooting
        logger.exception("Failed to call Piston execute endpoint")
        # Return a safe, generic message to the user
        return JsonResponse(
            {"stderr": "Code execution service is currently unavailable. Please try again later."}, status=502
        )

    result = resp.json()
    # Piston returns a structure like:
    # { language, version, run: { stdout, stderr, code, signal, output } }
    run = result.get("run", {})
    return JsonResponse(
        {
            "stdout": run.get("stdout", run.get("output", "")),
            "stderr": run.get("stderr", ""),
        }
    )
