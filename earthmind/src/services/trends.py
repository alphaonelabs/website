"""
EarthMind Trend Analysis Service

Implements time-series trend analysis for environmental sensor data using
linear regression, moving averages, and rate-of-change metrics.
No external dependencies required — uses Python standard library only.
"""

import math
from typing import Optional


# ---------------------------------------------------------------------------
# Core statistics helpers
# ---------------------------------------------------------------------------

def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _linear_regression(x: list[float], y: list[float]) -> tuple[float, float, float]:
    """
    Ordinary least-squares regression: y = slope * x + intercept.

    Returns (slope, intercept, r_squared).
    """
    n = len(x)
    if n < 2:
        return 0.0, _mean(y), 0.0

    x_mean = _mean(x)
    y_mean = _mean(y)

    ss_xy = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y))
    ss_xx = sum((xi - x_mean) ** 2 for xi in x)
    ss_yy = sum((yi - y_mean) ** 2 for yi in y)

    if ss_xx == 0:
        return 0.0, y_mean, 0.0

    slope = ss_xy / ss_xx
    intercept = y_mean - slope * x_mean

    r_squared = (ss_xy ** 2 / (ss_xx * ss_yy)) if ss_yy != 0 else 0.0

    return slope, intercept, r_squared


def simple_moving_average(values: list[float], window: int) -> list[Optional[float]]:
    """
    Return a list of SMA values. The first (window-1) entries are None.
    """
    result: list[Optional[float]] = [None] * (window - 1)
    for i in range(window - 1, len(values)):
        result.append(_mean(values[i - window + 1 : i + 1]))
    return result


def exponential_moving_average(values: list[float], alpha: float = 0.3) -> list[float]:
    """
    Return EMA values.  alpha is the smoothing factor (0 < alpha <= 1).
    """
    if not values:
        return []
    ema = [values[0]]
    for v in values[1:]:
        ema.append(alpha * v + (1 - alpha) * ema[-1])
    return ema


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def linear_trend(values: list[float]) -> dict:
    """
    Fit a linear regression to the value series.

    Returns:
        slope        – rate of change per step (positive = increasing)
        intercept    – fitted value at index 0
        r_squared    – goodness-of-fit (0–1)
        direction    – 'increasing', 'decreasing', or 'stable'
        strength     – 'strong', 'moderate', or 'weak'
        projected_next – value forecasted for the next step
    """
    if len(values) < 2:
        return {
            "slope": 0.0,
            "intercept": _mean(values),
            "r_squared": 0.0,
            "direction": "stable",
            "strength": "weak",
            "projected_next": _mean(values),
        }

    x = list(range(len(values)))
    slope, intercept, r_squared = _linear_regression(x, values)

    if abs(slope) < 1e-9:
        direction = "stable"
    elif slope > 0:
        direction = "increasing"
    else:
        direction = "decreasing"

    if r_squared >= 0.7:
        strength = "strong"
    elif r_squared >= 0.4:
        strength = "moderate"
    else:
        strength = "weak"

    projected_next = slope * len(values) + intercept

    return {
        "slope": round(slope, 6),
        "intercept": round(intercept, 6),
        "r_squared": round(r_squared, 4),
        "direction": direction,
        "strength": strength,
        "projected_next": round(projected_next, 4),
    }


def moving_average_trend(
    values: list[float],
    short_window: int = 5,
    long_window: int = 20,
) -> dict:
    """
    Compare short-term vs long-term moving averages to identify momentum.

    Returns the most recent SMA values and a signal:
        'bullish'  – short MA > long MA (parameter rising relative to trend)
        'bearish'  – short MA < long MA (parameter falling)
        'neutral'  – insufficient data or averages are equal
    """
    sma_short = simple_moving_average(values, short_window)
    sma_long = simple_moving_average(values, long_window)
    ema = exponential_moving_average(values)

    last_short = next((v for v in reversed(sma_short) if v is not None), None)
    last_long = next((v for v in reversed(sma_long) if v is not None), None)

    if last_short is None or last_long is None:
        signal = "neutral"
    elif last_short > last_long:
        signal = "bullish"
    elif last_short < last_long:
        signal = "bearish"
    else:
        signal = "neutral"

    return {
        "short_ma": round(last_short, 4) if last_short is not None else None,
        "long_ma": round(last_long, 4) if last_long is not None else None,
        "ema": round(ema[-1], 4) if ema else None,
        "signal": signal,
        "sma_short_series": [round(v, 4) if v is not None else None for v in sma_short],
        "sma_long_series": [round(v, 4) if v is not None else None for v in sma_long],
    }


def rate_of_change(values: list[float], periods: int = 1) -> list[Optional[float]]:
    """
    Calculate the percentage rate of change over *periods* steps.
    Returns a list where the first *periods* entries are None.
    """
    result: list[Optional[float]] = [None] * periods
    for i in range(periods, len(values)):
        base = values[i - periods]
        if base == 0:
            result.append(None)
        else:
            result.append(round((values[i] - base) / abs(base) * 100, 4))
    return result


def analyze_trends(
    values: list[float],
    timestamps: Optional[list[str]] = None,
    short_window: int = 5,
    long_window: int = 20,
) -> dict:
    """
    Comprehensive trend analysis combining linear regression, moving averages,
    and rate-of-change metrics.

    Returns a dict with:
        'linear'       – linear_trend result
        'moving_avg'   – moving_average_trend result
        'roc'          – most recent rate-of-change (%)
        'min'          – series minimum
        'max'          – series maximum
        'mean'         – series mean
        'std'          – series standard deviation
        'risk_level'   – estimated ecological risk: 'low', 'medium', 'high'
        'summary'      – human-readable summary string
    """
    if not values:
        return {
            "linear": {},
            "moving_avg": {},
            "roc": None,
            "min": None,
            "max": None,
            "mean": None,
            "std": None,
            "risk_level": "low",
            "summary": "No data available.",
        }

    lin = linear_trend(values)
    ma = moving_average_trend(values, short_window, long_window)
    roc_series = rate_of_change(values, periods=1)
    last_roc = next((v for v in reversed(roc_series) if v is not None), None)

    n = len(values)
    mu = _mean(values)
    sigma = math.sqrt(sum((v - mu) ** 2 for v in values) / n) if n > 1 else 0.0

    risk_level = _estimate_risk(lin, ma, last_roc)
    summary = _build_summary(lin, ma, last_roc, risk_level)

    return {
        "linear": lin,
        "moving_avg": ma,
        "roc": last_roc,
        "min": min(values),
        "max": max(values),
        "mean": round(mu, 4),
        "std": round(sigma, 4),
        "risk_level": risk_level,
        "summary": summary,
    }


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _estimate_risk(lin: dict, ma: dict, roc: Optional[float]) -> str:
    """Heuristic risk scoring based on trend characteristics."""
    score = 0

    if lin.get("direction") == "increasing" and lin.get("strength") == "strong":
        score += 3
    elif lin.get("direction") == "increasing" and lin.get("strength") == "moderate":
        score += 2
    elif lin.get("direction") == "increasing":
        score += 1

    if ma.get("signal") == "bullish":
        score += 1

    if roc is not None and abs(roc) > 20:
        score += 2
    elif roc is not None and abs(roc) > 10:
        score += 1

    if lin.get("r_squared", 0) >= 0.7:
        score += 1

    if score >= 5:
        return "high"
    if score >= 3:
        return "medium"
    return "low"


def _build_summary(lin: dict, ma: dict, roc: Optional[float], risk_level: str) -> str:
    direction = lin.get("direction", "stable")
    strength = lin.get("strength", "weak")
    r2 = lin.get("r_squared", 0)
    signal = ma.get("signal", "neutral")

    parts = [f"Trend is {direction} ({strength}, R²={r2:.2f})."]

    if signal != "neutral":
        parts.append(f"Short-term momentum is {signal}.")

    if roc is not None:
        parts.append(f"Latest rate of change: {roc:+.1f}%.")

    parts.append(f"Estimated ecological risk: {risk_level.upper()}.")
    return " ".join(parts)
