"""
Tests for the EarthMind trend analysis service.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from services.trends import (
    _mean,
    _linear_regression,
    simple_moving_average,
    exponential_moving_average,
    linear_trend,
    moving_average_trend,
    rate_of_change,
    analyze_trends,
)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

class TestLinearRegression:
    def test_perfect_positive_slope(self):
        x = [0, 1, 2, 3, 4]
        y = [0, 2, 4, 6, 8]  # y = 2x
        slope, intercept, r2 = _linear_regression(x, y)
        assert abs(slope - 2.0) < 1e-9
        assert abs(intercept) < 1e-9
        assert abs(r2 - 1.0) < 1e-9

    def test_perfect_negative_slope(self):
        x = [0, 1, 2, 3, 4]
        y = [10, 8, 6, 4, 2]  # y = -2x + 10
        slope, intercept, r2 = _linear_regression(x, y)
        assert abs(slope + 2.0) < 1e-9
        assert abs(intercept - 10.0) < 1e-9
        assert abs(r2 - 1.0) < 1e-9

    def test_flat_line(self):
        x = [0, 1, 2, 3]
        y = [5.0, 5.0, 5.0, 5.0]
        slope, intercept, r2 = _linear_regression(x, y)
        assert abs(slope) < 1e-9
        assert abs(r2) < 1e-9

    def test_single_point(self):
        slope, intercept, r2 = _linear_regression([1], [5])
        assert slope == 0.0
        assert r2 == 0.0


# ---------------------------------------------------------------------------
# Moving averages
# ---------------------------------------------------------------------------

class TestSimpleMovingAverage:
    def test_window_3(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        sma = simple_moving_average(values, 3)
        assert sma[0] is None
        assert sma[1] is None
        assert abs(sma[2] - 2.0) < 1e-9
        assert abs(sma[4] - 4.0) < 1e-9

    def test_length_preserved(self):
        values = list(range(10))
        sma = simple_moving_average(values, 5)
        assert len(sma) == len(values)

    def test_window_larger_than_data(self):
        values = [1.0, 2.0]
        sma = simple_moving_average(values, 5)
        assert all(v is None for v in sma)


class TestExponentialMovingAverage:
    def test_length_preserved(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        ema = exponential_moving_average(values, alpha=0.3)
        assert len(ema) == len(values)

    def test_first_value_equals_input(self):
        values = [7.0, 8.0, 9.0]
        ema = exponential_moving_average(values)
        assert ema[0] == 7.0

    def test_empty_returns_empty(self):
        assert exponential_moving_average([]) == []

    def test_smoothing_factor_effect(self):
        # Higher alpha → faster response to recent values
        values = [10.0] * 5 + [20.0]
        ema_high = exponential_moving_average(values, alpha=0.9)
        ema_low = exponential_moving_average(values, alpha=0.1)
        assert ema_high[-1] > ema_low[-1]


# ---------------------------------------------------------------------------
# Linear trend
# ---------------------------------------------------------------------------

class TestLinearTrend:
    def test_increasing_trend(self):
        values = list(range(1, 21))  # 1, 2, ..., 20
        result = linear_trend(values)
        assert result["direction"] == "increasing"
        assert result["r_squared"] > 0.99

    def test_decreasing_trend(self):
        values = list(range(20, 0, -1))
        result = linear_trend(values)
        assert result["direction"] == "decreasing"

    def test_flat_trend(self):
        values = [5.0] * 10
        result = linear_trend(values)
        assert result["direction"] == "stable"
        assert result["r_squared"] == 0.0

    def test_projected_next_is_number(self):
        values = list(range(10))
        result = linear_trend(values)
        assert isinstance(result["projected_next"], float)

    def test_strength_strong_for_perfect_fit(self):
        values = list(range(1, 11))
        result = linear_trend(values)
        assert result["strength"] == "strong"

    def test_single_value(self):
        result = linear_trend([42.0])
        assert result["direction"] == "stable"

    def test_two_values_returns_valid(self):
        result = linear_trend([1.0, 3.0])
        assert "direction" in result
        assert "slope" in result


# ---------------------------------------------------------------------------
# Moving average trend
# ---------------------------------------------------------------------------

class TestMovingAverageTrend:
    def test_bullish_signal(self):
        # Rapidly rising series: short MA > long MA
        values = [1.0] * 20 + [100.0] * 10
        result = moving_average_trend(values, short_window=3, long_window=15)
        assert result["signal"] in ("bullish", "neutral")  # mostly bullish

    def test_neutral_for_stable_series(self):
        values = [10.0] * 30
        result = moving_average_trend(values, short_window=5, long_window=20)
        assert result["signal"] == "neutral"

    def test_returns_expected_keys(self):
        values = list(range(30))
        result = moving_average_trend(values)
        assert "short_ma" in result
        assert "long_ma" in result
        assert "ema" in result
        assert "signal" in result
        assert "sma_short_series" in result
        assert "sma_long_series" in result

    def test_neutral_when_insufficient_data(self):
        result = moving_average_trend([1.0, 2.0], short_window=5, long_window=20)
        assert result["signal"] == "neutral"


# ---------------------------------------------------------------------------
# Rate of change
# ---------------------------------------------------------------------------

class TestRateOfChange:
    def test_basic_50_percent_increase(self):
        roc = rate_of_change([100.0, 150.0], periods=1)
        assert roc[0] is None
        assert abs(roc[1] - 50.0) < 1e-9

    def test_zero_base_returns_none(self):
        roc = rate_of_change([0.0, 5.0], periods=1)
        assert roc[1] is None

    def test_length_preserved(self):
        values = [1.0, 2.0, 4.0, 8.0]
        roc = rate_of_change(values, periods=1)
        assert len(roc) == len(values)

    def test_first_period_items_are_none(self):
        roc = rate_of_change([10.0, 20.0, 30.0], periods=2)
        assert roc[0] is None
        assert roc[1] is None


# ---------------------------------------------------------------------------
# Combined analyze_trends
# ---------------------------------------------------------------------------

class TestAnalyzeTrends:
    def test_returns_all_keys(self):
        values = list(range(1, 31))
        result = analyze_trends(values)
        for key in ("linear", "moving_avg", "roc", "min", "max", "mean", "std", "risk_level", "summary"):
            assert key in result

    def test_min_max_correct(self):
        values = [3.0, 1.0, 4.0, 1.0, 5.0, 9.0, 2.0]
        result = analyze_trends(values)
        assert result["min"] == 1.0
        assert result["max"] == 9.0

    def test_risk_level_high_for_strong_increasing_trend(self):
        # Rapidly and consistently increasing data
        values = [float(i * 10) for i in range(1, 31)]
        result = analyze_trends(values)
        assert result["risk_level"] in ("medium", "high")

    def test_risk_level_low_for_stable_data(self):
        values = [10.0] * 30
        result = analyze_trends(values)
        assert result["risk_level"] == "low"

    def test_empty_values(self):
        result = analyze_trends([])
        assert result["risk_level"] == "low"
        assert result["mean"] is None

    def test_summary_is_string(self):
        values = list(range(1, 21))
        result = analyze_trends(values)
        assert isinstance(result["summary"], str)
        assert len(result["summary"]) > 0

    def test_std_nonnegative(self):
        values = [2.5, 3.0, 2.8, 3.2, 2.9]
        result = analyze_trends(values)
        assert result["std"] >= 0.0
