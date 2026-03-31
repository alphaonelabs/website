from django.urls import path

from . import views

app_name = "ai_discovery"

urlpatterns = [
    # Home and project management
    path("", views.discovery_home, name="home"),
    path("projects/", views.project_list, name="project_list"),
    path("projects/create/", views.project_create, name="project_create"),
    path("projects/<slug:slug>/", views.project_detail, name="project_detail"),
    # Hypothesis management
    path("projects/<slug:slug>/generate-hypothesis/", views.generate_hypothesis, name="generate_hypothesis"),
    path("hypothesis/<int:pk>/", views.hypothesis_detail, name="hypothesis_detail"),
    # Experiment management
    path("hypothesis/<int:hypothesis_pk>/create-experiment/", views.create_experiment, name="create_experiment"),
    path("experiment/<int:experiment_pk>/run/", views.run_experiment, name="run_experiment"),
    # Discovery management
    path("discoveries/", views.discovery_list, name="discovery_list"),
    path("discovery/<int:pk>/", views.discovery_detail, name="discovery_detail"),
    path("hypothesis/<int:hypothesis_pk>/synthesize/", views.synthesize_discovery, name="synthesize_discovery"),
    # Knowledge base
    path("knowledge/", views.knowledge_base, name="knowledge_base"),
]
