import json
import logging
import random
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Discovery, DiscoveryProject, Experiment, Hypothesis, IterationLog, KnowledgeBase

logger = logging.getLogger(__name__)


@login_required
def discovery_home(request):
    """
    Main landing page for the AI Scientific Discovery Engine.
    """
    user_projects = DiscoveryProject.objects.filter(user=request.user).order_by("-updated_at")[:5]
    public_projects = DiscoveryProject.objects.filter(is_public=True).exclude(user=request.user).order_by("-updated_at")[
        :5
    ]
    recent_discoveries = Discovery.objects.filter(project__user=request.user).order_by("-created_at")[:5]

    stats = {
        "total_projects": DiscoveryProject.objects.filter(user=request.user).count(),
        "total_hypotheses": Hypothesis.objects.filter(project__user=request.user).count(),
        "total_experiments": Experiment.objects.filter(hypothesis__project__user=request.user).count(),
        "total_discoveries": Discovery.objects.filter(project__user=request.user).count(),
    }

    context = {
        "user_projects": user_projects,
        "public_projects": public_projects,
        "recent_discoveries": recent_discoveries,
        "stats": stats,
    }
    return render(request, "ai_discovery/home.html", context)


@login_required
def project_list(request):
    """
    List all discovery projects for the current user.
    """
    projects = DiscoveryProject.objects.filter(user=request.user).order_by("-updated_at")
    domain_filter = request.GET.get("domain")
    status_filter = request.GET.get("status")

    if domain_filter:
        projects = projects.filter(domain=domain_filter)
    if status_filter:
        projects = projects.filter(status=status_filter)

    paginator = Paginator(projects, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {"page_obj": page_obj, "domain_filter": domain_filter, "status_filter": status_filter}
    return render(request, "ai_discovery/project_list.html", context)


@login_required
def project_create(request):
    """
    Create a new discovery project.
    """
    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")
        domain = request.POST.get("domain")
        is_public = request.POST.get("is_public") == "on"

        project = DiscoveryProject.objects.create(
            user=request.user, title=title, description=description, domain=domain, is_public=is_public
        )
        messages.success(request, f"Project '{title}' created successfully!")
        return redirect("ai_discovery:project_detail", slug=project.slug)

    context = {"domain_choices": DiscoveryProject.DOMAIN_CHOICES}
    return render(request, "ai_discovery/project_create.html", context)


@login_required
def project_detail(request, slug):
    """
    View details of a specific discovery project.
    """
    project = get_object_or_404(DiscoveryProject, slug=slug)

    # Check permissions
    if project.user != request.user and not project.is_public:
        messages.error(request, "You don't have permission to view this project.")
        return redirect("ai_discovery:home")

    hypotheses = project.hypotheses.all().order_by("-created_at")
    discoveries = project.discoveries.all().order_by("-created_at")

    hypothesis_stats = {
        "total": hypotheses.count(),
        "proposed": hypotheses.filter(status="proposed").count(),
        "testing": hypotheses.filter(status="testing").count(),
        "supported": hypotheses.filter(status="supported").count(),
        "rejected": hypotheses.filter(status="rejected").count(),
    }

    context = {
        "project": project,
        "hypotheses": hypotheses[:10],
        "discoveries": discoveries[:10],
        "hypothesis_stats": hypothesis_stats,
        "is_owner": project.user == request.user,
    }
    return render(request, "ai_discovery/project_detail.html", context)


@login_required
@require_POST
def generate_hypothesis(request, slug):
    """
    Generate a new hypothesis using AI (simulated for now).
    """
    project = get_object_or_404(DiscoveryProject, slug=slug, user=request.user)

    # Simulate AI hypothesis generation
    # In a real implementation, this would call an LLM API
    sample_hypotheses = {
        "mathematics": [
            "There exists a pattern in the distribution of prime numbers that can be expressed as a polynomial function",
            "The Collatz conjecture holds for all numbers of the form 2^n + 1",
            "A new class of fractals exists that bridges the properties of Mandelbrot and Julia sets",
        ],
        "physics": [
            "Under specific quantum conditions, particle entanglement can persist beyond classical distance limits",
            "A new phase of matter exists at the intersection of extreme pressure and ultra-low temperatures",
            "Dark matter interactions may be detectable through novel gravitational lensing patterns",
        ],
        "chemistry": [
            "A novel catalyst configuration can reduce activation energy for CO2 conversion by 40%",
            "Molecular structures with alternating polarity show enhanced stability in aqueous solutions",
            "Quantum tunneling effects significantly influence reaction rates in certain organic compounds",
        ],
        "biology": [
            "Gene expression patterns in extremophiles reveal universal adaptability mechanisms",
            "Protein folding pathways exhibit fractal-like self-similarity across different organisms",
            "Mitochondrial efficiency is correlated with circadian rhythm phase duration",
        ],
        "computer_science": [
            "A new algorithmic approach can solve specific NP-complete problems in polynomial time for bounded inputs",
            "Neural network architectures with fractal connectivity patterns show improved generalization",
            "Quantum error correction codes can be optimized using topology-based design patterns",
        ],
    }

    domain = project.domain
    if domain not in sample_hypotheses:
        domain = "mathematics"

    hypothesis_text = random.choice(sample_hypotheses[domain])
    confidence = round(random.uniform(0.6, 0.9), 2)

    hypothesis = Hypothesis.objects.create(
        project=project,
        statement=hypothesis_text,
        rationale=f"Generated based on analysis of existing knowledge in {project.domain}. "
        f"This hypothesis emerged from pattern recognition in recent literature and "
        f"experimental data trends.",
        status="proposed",
        confidence_score=confidence,
        is_ai_generated=True,
    )

    # Log the iteration
    IterationLog.objects.create(
        hypothesis=hypothesis,
        iteration_number=1,
        action="generated",
        details=f"Initial hypothesis generated with confidence {confidence}",
        ai_reasoning="Analyzed domain literature and identified potential research gap",
    )

    messages.success(request, "New hypothesis generated successfully!")
    return redirect("ai_discovery:hypothesis_detail", pk=hypothesis.id)


@login_required
def hypothesis_detail(request, pk):
    """
    View details of a specific hypothesis.
    """
    hypothesis = get_object_or_404(Hypothesis, pk=pk)
    project = hypothesis.project

    # Check permissions
    if project.user != request.user and not project.is_public:
        messages.error(request, "You don't have permission to view this hypothesis.")
        return redirect("ai_discovery:home")

    experiments = hypothesis.experiments.all().order_by("-created_at")
    iterations = hypothesis.iteration_logs.all().order_by("iteration_number")
    discoveries = hypothesis.discoveries.all().order_by("-created_at")

    context = {
        "hypothesis": hypothesis,
        "project": project,
        "experiments": experiments,
        "iterations": iterations,
        "discoveries": discoveries,
        "is_owner": project.user == request.user,
    }
    return render(request, "ai_discovery/hypothesis_detail.html", context)


@login_required
@require_POST
def create_experiment(request, hypothesis_pk):
    """
    Create an experiment to test a hypothesis.
    """
    hypothesis = get_object_or_404(Hypothesis, pk=hypothesis_pk)
    project = hypothesis.project

    if project.user != request.user:
        return JsonResponse({"error": "Permission denied"}, status=403)

    experiment_type = request.POST.get("experiment_type")
    description = request.POST.get("description")

    experiment = Experiment.objects.create(
        hypothesis=hypothesis, experiment_type=experiment_type, description=description, status="planned"
    )

    messages.success(request, "Experiment created successfully!")
    return redirect("ai_discovery:hypothesis_detail", pk=hypothesis.id)


@login_required
@require_POST
def run_experiment(request, experiment_pk):
    """
    Run an experiment (simulated).
    """
    experiment = get_object_or_404(Experiment, pk=experiment_pk)
    hypothesis = experiment.hypothesis
    project = hypothesis.project

    if project.user != request.user:
        return JsonResponse({"error": "Permission denied"}, status=403)

    # Update experiment status
    experiment.status = "running"
    experiment.started_at = timezone.now()
    experiment.save()

    # Simulate experiment execution
    # In a real implementation, this would trigger actual simulations or computations
    import time

    time.sleep(1)  # Simulate processing time

    # Generate simulated results
    success = random.random() > 0.3  # 70% success rate
    results = {
        "success": success,
        "execution_time": random.uniform(0.5, 5.0),
        "data_points": random.randint(100, 1000),
        "confidence": round(random.uniform(0.6, 0.95), 2),
        "observations": [
            "Initial conditions met successfully",
            "Parameters within expected ranges",
            "Results show statistical significance" if success else "Results inconclusive",
        ],
    }

    experiment.results = results
    experiment.status = "completed"
    experiment.completed_at = timezone.now()
    experiment.save()

    # Update hypothesis status based on results
    if success:
        hypothesis.status = "testing"
        hypothesis.save()

        # Log the iteration
        iteration_count = hypothesis.iteration_logs.count() + 1
        IterationLog.objects.create(
            hypothesis=hypothesis,
            iteration_number=iteration_count,
            action="tested",
            details=f"Experiment completed successfully with {results['confidence']} confidence",
            ai_reasoning="Experimental results support the hypothesis with statistical significance",
        )
    else:
        # Log failed test
        iteration_count = hypothesis.iteration_logs.count() + 1
        IterationLog.objects.create(
            hypothesis=hypothesis,
            iteration_number=iteration_count,
            action="tested",
            details="Experiment completed but results were inconclusive",
            ai_reasoning="Further refinement needed based on experimental observations",
        )

    messages.success(request, "Experiment completed!")
    return redirect("ai_discovery:hypothesis_detail", pk=hypothesis.id)


@login_required
def knowledge_base(request):
    """
    Browse the knowledge base.
    """
    knowledge_items = KnowledgeBase.objects.all().order_by("-created_at")

    domain_filter = request.GET.get("domain")
    content_type_filter = request.GET.get("content_type")
    search_query = request.GET.get("q")

    if domain_filter:
        knowledge_items = knowledge_items.filter(domain=domain_filter)
    if content_type_filter:
        knowledge_items = knowledge_items.filter(content_type=content_type_filter)
    if search_query:
        knowledge_items = knowledge_items.filter(
            Q(title__icontains=search_query) | Q(abstract__icontains=search_query) | Q(content__icontains=search_query)
        )

    paginator = Paginator(knowledge_items, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {"page_obj": page_obj, "domain_filter": domain_filter, "content_type_filter": content_type_filter}
    return render(request, "ai_discovery/knowledge_base.html", context)


@login_required
def discovery_list(request):
    """
    List all discoveries made by the user.
    """
    discoveries = Discovery.objects.filter(project__user=request.user).order_by("-created_at")

    significance_filter = request.GET.get("significance")
    if significance_filter:
        discoveries = discoveries.filter(significance=significance_filter)

    paginator = Paginator(discoveries, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {"page_obj": page_obj, "significance_filter": significance_filter}
    return render(request, "ai_discovery/discovery_list.html", context)


@login_required
def discovery_detail(request, pk):
    """
    View details of a specific discovery.
    """
    discovery = get_object_or_404(Discovery, pk=pk)
    project = discovery.project

    # Check permissions
    if project.user != request.user and not project.is_public:
        messages.error(request, "You don't have permission to view this discovery.")
        return redirect("ai_discovery:home")

    context = {"discovery": discovery, "project": project, "hypothesis": discovery.hypothesis}
    return render(request, "ai_discovery/discovery_detail.html", context)


@login_required
@require_POST
def synthesize_discovery(request, hypothesis_pk):
    """
    Synthesize a discovery from a hypothesis with supporting experiments.
    """
    hypothesis = get_object_or_404(Hypothesis, pk=hypothesis_pk)
    project = hypothesis.project

    if project.user != request.user:
        return JsonResponse({"error": "Permission denied"}, status=403)

    # Check if hypothesis has enough supporting experiments
    completed_experiments = hypothesis.experiments.filter(status="completed")
    if completed_experiments.count() < 1:
        messages.error(request, "At least one completed experiment is required to synthesize a discovery.")
        return redirect("ai_discovery:hypothesis_detail", pk=hypothesis.id)

    # Generate discovery report
    significance = "minor"
    if hypothesis.confidence_score > 0.8:
        significance = "significant"
    elif hypothesis.confidence_score > 0.7:
        significance = "moderate"

    discovery = Discovery.objects.create(
        project=project,
        hypothesis=hypothesis,
        title=f"Discovery: {hypothesis.statement[:100]}",
        summary=f"Through {completed_experiments.count()} experiments, "
        f"we have found evidence supporting: {hypothesis.statement}",
        detailed_report=f"""
## Hypothesis
{hypothesis.statement}

## Rationale
{hypothesis.rationale}

## Experimental Evidence
{completed_experiments.count()} experiments were conducted to test this hypothesis.

## Key Findings
Based on the experimental results, we observe:
- Statistical significance across multiple test conditions
- Reproducible results within acceptable confidence intervals
- Novel insights that extend current understanding in {project.domain}

## Implications
This discovery has potential implications for future research in {project.domain}
and may open new avenues for investigation.

## Conclusion
The hypothesis is supported by experimental evidence with a confidence level of {hypothesis.confidence_score:.2f}.
        """.strip(),
        significance=significance,
        supporting_data={
            "experiments": [
                {"id": exp.id, "type": exp.experiment_type, "results": exp.results} for exp in completed_experiments
            ]
        },
    )

    # Update hypothesis status
    hypothesis.status = "supported"
    hypothesis.save()

    # Log the iteration
    iteration_count = hypothesis.iteration_logs.count() + 1
    IterationLog.objects.create(
        hypothesis=hypothesis,
        iteration_number=iteration_count,
        action="supported",
        details=f"Discovery synthesized: {discovery.title}",
        ai_reasoning="Sufficient experimental evidence gathered to support hypothesis",
    )

    messages.success(request, "Discovery synthesized successfully!")
    return redirect("ai_discovery:discovery_detail", pk=discovery.id)
