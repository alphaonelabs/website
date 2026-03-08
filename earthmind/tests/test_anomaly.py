"""
Tests for the EarthMind anomaly detection service.
"""

import math
import sys
import os

# Allow importing from src/ without installing the package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from services.anomaly import (
    _mean,
    _std,
    _percentile,
    zscore_anomalies,
    iqr_anomalies,
    rolling_avg_anomalies,
    detect_anomalies,
)


# ---------------------------------------------------------------------------
# Helper / private function tests
# ---------------------------------------------------------------------------

class TestMean:
    def test_basic(self):
        assert _mean([1, 2, 3, 4, 5]) == 3.0

    def test_empty(self):
        assert _mean([]) == 0.0

    def test_single(self):
        assert _mean([7.5]) == 7.5

    def test_negatives(self):
        assert _mean([-4.0, 4.0]) == 0.0


class TestStd:
    def test_constant_series(self):
        assert _std([5.0, 5.0, 5.0]) == 0.0

    def test_known_std(self):
        # Population std of [2, 4, 4, 4, 5, 5, 7, 9] = 2.0
        result = _std([2, 4, 4, 4, 5, 5, 7, 9])
        assert abs(result - 2.0) < 1e-9

    def test_short_series(self):
        assert _std([1.0]) == 0.0


class TestPercentile:
    def test_median(self):
        vals = sorted([1.0, 2.0, 3.0, 4.0, 5.0])
        assert _percentile(vals, 50) == 3.0

    def test_q1(self):
        vals = sorted(range(1, 11))  # [1..10]
        result = _percentile([float(v) for v in vals], 25)
        assert 2.0 <= result <= 4.0

    def test_min(self):
        vals = [1.0, 2.0, 3.0]
        assert _percentile(vals, 0) == 1.0

    def test_max(self):
        vals = [1.0, 2.0, 3.0]
        assert _percentile(vals, 100) == 3.0


# ---------------------------------------------------------------------------
# Z-score anomaly detection
# ---------------------------------------------------------------------------

class TestZscoreAnomalies:
    def test_detects_obvious_spike(self):
        # 18 normal values + one 10× spike
        values = [10.0] * 18 + [100.0]
        anomalies = zscore_anomalies(values, threshold=2.5)
        indices = [a["index"] for a in anomalies]
        assert 18 in indices

    def test_no_anomalies_in_uniform_series(self):
        values = [5.0] * 20
        assert zscore_anomalies(values, threshold=2.5) == []

    def test_returns_empty_for_short_series(self):
        assert zscore_anomalies([1.0, 2.0]) == []

    def test_returns_empty_when_std_zero(self):
        assert zscore_anomalies([3.0] * 10) == []

    def test_timestamps_attached(self):
        values = [10.0] * 18 + [100.0]
        timestamps = [f"2024-01-01T{i:02d}:00:00" for i in range(19)]
        anomalies = zscore_anomalies(values, timestamps=timestamps)
        for a in anomalies:
            assert "timestamp" in a

    def test_severity_levels(self):
        # Very large spike relative to a larger baseline pool should be 'high'.
        # With 50 normal values at 10.0 and one outlier at 1000.0 the z-score is
        # ≈7, which exceeds 2× the default threshold (5.0) → severity == 'high'.
        values = [10.0] * 50 + [1000.0]
        anomalies = zscore_anomalies(values, threshold=2.5)
        assert anomalies[0]["severity"] == "high"

    def test_sorted_by_deviation_descending(self):
        values = [10.0] * 15 + [50.0, 100.0, 200.0]
        anomalies = zscore_anomalies(values, threshold=2.0)
        deviations = [a["deviation"] for a in anomalies]
        assert deviations == sorted(deviations, reverse=True)


# ---------------------------------------------------------------------------
# IQR anomaly detection
# ---------------------------------------------------------------------------

class TestIqrAnomalies:
    def test_detects_outlier(self):
        values = list(range(10, 30)) + [200]  # 200 is a clear outlier
        anomalies = iqr_anomalies(values)
        indices = [a["index"] for a in anomalies]
        assert len(values) - 1 in indices

    def test_no_anomalies_in_uniform_series(self):
        values = [5.0] * 20
        assert iqr_anomalies(values) == []

    def test_short_series_returns_empty(self):
        assert iqr_anomalies([1.0, 2.0, 3.0]) == []

    def test_method_label(self):
        values = list(range(10, 30)) + [200]
        anomalies = iqr_anomalies(values)
        for a in anomalies:
            assert a["method"] == "iqr"

    def test_negative_outlier(self):
        values = list(range(50, 70)) + [-200]
        anomalies = iqr_anomalies(values)
        indices = [a["index"] for a in anomalies]
        assert len(values) - 1 in indices


# ---------------------------------------------------------------------------
# Rolling average anomaly detection
# ---------------------------------------------------------------------------

class TestRollingAvgAnomalies:
    def test_detects_sudden_spike(self):
        values = [10.0] * 10 + [80.0]  # 700% spike
        anomalies = rolling_avg_anomalies(values, window=5, threshold_pct=30.0)
        indices = [a["index"] for a in anomalies]
        assert 10 in indices

    def test_no_anomalies_in_stable_series(self):
        values = [10.0] * 20
        assert rolling_avg_anomalies(values, window=5, threshold_pct=30.0) == []

    def test_short_series_returns_empty(self):
        assert rolling_avg_anomalies([1.0, 2.0, 3.0, 4.0], window=5) == []

    def test_method_label(self):
        values = [10.0] * 10 + [80.0]
        anomalies = rolling_avg_anomalies(values)
        for a in anomalies:
            assert a["method"] == "rolling_avg"


# ---------------------------------------------------------------------------
# Combined detect_anomalies
# ---------------------------------------------------------------------------

class TestDetectAnomalies:
    def test_returns_expected_keys(self):
        values = [10.0] * 18 + [100.0]
        result = detect_anomalies(values)
        assert "zscore" in result
        assert "iqr" in result
        assert "rolling_avg" in result
        assert "summary" in result
        assert "total_anomalies" in result
        assert "high_severity_count" in result

    def test_summary_union_has_no_duplicate_indices(self):
        values = [10.0] * 18 + [100.0]
        result = detect_anomalies(values)
        indices = [a["index"] for a in result["summary"]]
        assert len(indices) == len(set(indices))

    def test_summary_sorted_by_index(self):
        values = [10.0] * 15 + [100.0, 10.0, 10.0, 200.0]
        result = detect_anomalies(values)
        indices = [a["index"] for a in result["summary"]]
        assert indices == sorted(indices)

    def test_total_matches_summary_length(self):
        values = [10.0] * 18 + [100.0]
        result = detect_anomalies(values)
        assert result["total_anomalies"] == len(result["summary"])

    def test_high_severity_count(self):
        values = [10.0] * 18 + [10000.0]
        result = detect_anomalies(values)
        high_count = sum(1 for a in result["summary"] if a["severity"] == "high")
        assert result["high_severity_count"] == high_count

    def test_empty_values_returns_empty_summary(self):
        result = detect_anomalies([])
        assert result["summary"] == []
        assert result["total_anomalies"] == 0

    def test_takes_highest_severity_for_duplicate_index(self):
        # Use a value that triggers both zscore and iqr with different severities
        values = [10.0] * 18 + [10000.0]
        result = detect_anomalies(values, zscore_threshold=2.0, iqr_multiplier=1.5)
        # The single outlier should appear once in summary
        indices = [a["index"] for a in result["summary"]]
        assert indices.count(18) == 1
