from django.urls import path

from .views import (
    chemistry_home,
    code_editor_view,
    evaluate_code,
    ph_indicator_view,
    physics_electrical_circuit_view,
    physics_home,
    physics_inclined_view,
    physics_mass_spring_view,
    physics_pendulum_view,
    physics_projectile_view,
    precipitation_view,
    reaction_rate_view,
    solubility_view,
    titration_view,
    virtual_lab_home,
)

app_name = "virtual_lab"

urlpatterns = [
    path("", virtual_lab_home, name="virtual_lab_home"),
    path("physics/", physics_home, name="physics_home"),
    path("physics/pendulum/", physics_pendulum_view, name="physics_pendulum"),
    path("physics/projectile/", physics_projectile_view, name="physics_projectile"),
    path("physics/inclined/", physics_inclined_view, name="physics_inclined"),
    path("physics/mass_spring/", physics_mass_spring_view, name="physics_mass_spring"),
    path("physics/circuit/", physics_electrical_circuit_view, name="physics_electrical_circuit"),
    path("chemistry/", chemistry_home, name="chemistry_home"),
    path("chemistry/titration/", titration_view, name="titration"),
    path("chemistry/reaction-rate/", reaction_rate_view, name="reaction_rate"),
    path("chemistry/solubility/", solubility_view, name="solubility"),
    path("chemistry/precipitation/", precipitation_view, name="precipitation"),
    path("chemistry/ph-indicator/", ph_indicator_view, name="ph_indicator"),
    path("code-editor/", code_editor_view, name="code_editor"),
    path("evaluate-code/", evaluate_code, name="evaluate_code"),
]
