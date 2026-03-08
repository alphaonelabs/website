"""
Unit tests for the QuantaLab experiment catalogue and AI mentor module.
Tests run locally using pytest (no Cloudflare runtime required).
"""

import json
import sys
import os

import pytest

# Make src importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from experiments import (
    get_all_experiments,
    get_experiment,
    list_domains,
    EXPERIMENTS,
)


# ── Experiment catalogue tests ────────────────────────────────────────────


class TestListDomains:
    def test_returns_three_domains(self):
        domains = list_domains()
        assert len(domains) == 3

    def test_expected_domains_present(self):
        domains = list_domains()
        assert "physics" in domains
        assert "chemistry" in domains
        assert "biology" in domains

    def test_returns_list(self):
        assert isinstance(list_domains(), list)


class TestGetAllExperiments:
    def test_returns_dict(self):
        data = get_all_experiments()
        assert isinstance(data, dict)

    def test_all_domains_present(self):
        data = get_all_experiments()
        for domain in ("physics", "chemistry", "biology"):
            assert domain in data

    def test_each_domain_has_experiments(self):
        data = get_all_experiments()
        for domain, exps in data.items():
            assert len(exps) > 0, f"{domain} has no experiments"

    def test_experiments_have_required_fields(self):
        required = {"id", "title", "description", "parameters", "learning_objectives"}
        data = get_all_experiments()
        for domain, exps in data.items():
            for exp in exps:
                missing = required - set(exp.keys())
                assert not missing, f"Experiment {exp.get('id')} in {domain} missing: {missing}"

    def test_parameters_have_required_fields(self):
        param_required = {"id", "label", "min", "max", "default", "step"}
        data = get_all_experiments()
        for domain, exps in data.items():
            for exp in exps:
                for param in exp["parameters"]:
                    missing = param_required - set(param.keys())
                    assert not missing, (
                        f"Param {param.get('id')} in {exp['id']} missing: {missing}"
                    )

    def test_parameter_defaults_within_range(self):
        data = get_all_experiments()
        for domain, exps in data.items():
            for exp in exps:
                for param in exp["parameters"]:
                    assert param["min"] <= param["default"] <= param["max"], (
                        f"Default out of range for param {param['id']} in {exp['id']}"
                    )

    def test_json_serialisable(self):
        """All experiment data must serialise cleanly to JSON."""
        data = get_all_experiments()
        serialised = json.dumps(data)
        reloaded = json.loads(serialised)
        assert reloaded.keys() == data.keys()


class TestGetExperiment:
    def test_known_experiment_found(self):
        exp = get_experiment("physics", "pendulum")
        assert exp is not None
        assert exp["id"] == "pendulum"

    def test_unknown_experiment_returns_none(self):
        assert get_experiment("physics", "does_not_exist") is None

    def test_unknown_domain_returns_none(self):
        assert get_experiment("astrology", "pendulum") is None

    def test_experiment_across_domains(self):
        pairs = [
            ("physics",   "projectile"),
            ("physics",   "ohms_law"),
            ("chemistry", "acid_base"),
            ("chemistry", "boyles_law"),
            ("chemistry", "titration"),
            ("biology",   "mitosis"),
            ("biology",   "natural_selection"),
            ("biology",   "photosynthesis"),
        ]
        for domain, eid in pairs:
            exp = get_experiment(domain, eid)
            assert exp is not None, f"Could not find {domain}/{eid}"
            assert exp["id"] == eid

    def test_returns_correct_title(self):
        exp = get_experiment("chemistry", "acid_base")
        assert "Acid" in exp["title"]

    def test_learning_objectives_non_empty(self):
        exp = get_experiment("biology", "mitosis")
        assert len(exp["learning_objectives"]) > 0


class TestExperimentsStructure:
    """Sanity-checks on the raw EXPERIMENTS constant."""

    def test_physics_experiments_count(self):
        assert len(EXPERIMENTS["physics"]) >= 3

    def test_chemistry_experiments_count(self):
        assert len(EXPERIMENTS["chemistry"]) >= 3

    def test_biology_experiments_count(self):
        assert len(EXPERIMENTS["biology"]) >= 3

    def test_all_ids_are_strings(self):
        for domain, exps in EXPERIMENTS.items():
            for exp in exps:
                assert isinstance(exp["id"], str), f"Non-string id in {domain}"

    def test_unique_ids_per_domain(self):
        for domain, exps in EXPERIMENTS.items():
            ids = [e["id"] for e in exps]
            assert len(ids) == len(set(ids)), f"Duplicate ids in {domain}"

    def test_descriptions_are_non_empty_strings(self):
        for domain, exps in EXPERIMENTS.items():
            for exp in exps:
                assert isinstance(exp["description"], str)
                assert len(exp["description"]) > 10
