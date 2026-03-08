"""
EarthMind Anomaly Detection Service

Implements statistical anomaly detection for environmental sensor readings
using Z-score, IQR (Interquartile Range), and rolling-average methods.
No external dependencies required — uses Python standard library only.
"""

import math
from typing import Optional


def _mean(values: list[float]) -> float:
    """Return the arithmetic mean of a list of numbers."""
    if not values:
        return 0.0
    return sum(values) / len(values)


def _std(values: list[float]) -> float:
    """Return the population standard deviation."""
    if len(values) < 2:
        return 0.0
    mu = _mean(values)
    variance = sum((v - mu) ** 2 for v in values) / len(values)
    return math.sqrt(variance)


def _percentile(sorted_values: list[float], pct: float) -> float:
    """
    Return the value at the given percentile (0–100) of a sorted list
    using linear interpolation.
    """
    n = len(sorted_values)
    if n == 0:
        return 0.0
    index = (pct / 100) * (n - 1)
    lower = int(index)
    upper = min(lower + 1, n - 1)
    fraction = index - lower
    return sorted_values[lower] + fraction * (sorted_values[upper] - sorted_values[lower])


def zscore_anomalies(
    values: list[float],
    timestamps: Optional[list[str]] = None,
    threshold: float = 2.5,
) -> list[dict]:
    """
    Detect anomalies using the Z-score method.

    A point is flagged as an anomaly when |z| > threshold.
    Returns a list of anomaly dicts sorted by descending |z|.
    """
    if len(values) < 3:
        return []

    mu = _mean(values)
    sigma = _std(values)
    if sigma == 0:
        return []

    anomalies = []
    for i, v in enumerate(values):
        z = (v - mu) / sigma
        if abs(z) > threshold:
            deviation = abs(z)
            severity = _zscore_severity(deviation, threshold)
            entry = {
                "index": i,
                "actual_value": v,
                "expected_value": round(mu, 4),
                "deviation": round(deviation, 4),
                "method": "zscore",
                "severity": severity,
            }
            if timestamps and i < len(timestamps):
                entry["timestamp"] = timestamps[i]
            anomalies.append(entry)

    anomalies.sort(key=lambda x: x["deviation"], reverse=True)
    return anomalies


def iqr_anomalies(
    values: list[float],
    timestamps: Optional[list[str]] = None,
    multiplier: float = 1.5,
) -> list[dict]:
    """
    Detect anomalies using the IQR (Tukey fences) method.

    Lower fence = Q1 - multiplier * IQR
    Upper fence = Q3 + multiplier * IQR
    """
    if len(values) < 4:
        return []

    sorted_vals = sorted(values)
    q1 = _percentile(sorted_vals, 25)
    q3 = _percentile(sorted_vals, 75)
    iqr = q3 - q1
    if iqr == 0:
        return []

    lower_fence = q1 - multiplier * iqr
    upper_fence = q3 + multiplier * iqr
    midpoint = (q1 + q3) / 2

    anomalies = []
    for i, v in enumerate(values):
        if v < lower_fence or v > upper_fence:
            distance = max(v - upper_fence, lower_fence - v)
            deviation = round(distance / iqr, 4)
            severity = _iqr_severity(deviation)
            entry = {
                "index": i,
                "actual_value": v,
                "expected_value": round(midpoint, 4),
                "deviation": deviation,
                "method": "iqr",
                "severity": severity,
            }
            if timestamps and i < len(timestamps):
                entry["timestamp"] = timestamps[i]
            anomalies.append(entry)

    anomalies.sort(key=lambda x: x["deviation"], reverse=True)
    return anomalies


def rolling_avg_anomalies(
    values: list[float],
    timestamps: Optional[list[str]] = None,
    window: int = 5,
    threshold_pct: float = 30.0,
) -> list[dict]:
    """
    Detect anomalies by comparing each point against the rolling (simple)
    moving average of the preceding *window* observations.

    A point is flagged when |value - rolling_avg| / rolling_avg > threshold_pct/100.
    """
    if len(values) <= window:
        return []

    anomalies = []
    for i in range(window, len(values)):
        window_vals = values[i - window : i]
        avg = _mean(window_vals)
        if avg == 0:
            continue
        pct_deviation = abs(values[i] - avg) / abs(avg) * 100
        if pct_deviation > threshold_pct:
            severity = _pct_severity(pct_deviation, threshold_pct)
            entry = {
                "index": i,
                "actual_value": values[i],
                "expected_value": round(avg, 4),
                "deviation": round(pct_deviation, 2),
                "method": "rolling_avg",
                "severity": severity,
            }
            if timestamps and i < len(timestamps):
                entry["timestamp"] = timestamps[i]
            anomalies.append(entry)

    anomalies.sort(key=lambda x: x["deviation"], reverse=True)
    return anomalies


def detect_anomalies(
    values: list[float],
    timestamps: Optional[list[str]] = None,
    zscore_threshold: float = 2.5,
    iqr_multiplier: float = 1.5,
    rolling_window: int = 5,
    rolling_threshold_pct: float = 30.0,
) -> dict:
    """
    Run all three anomaly detection methods and return a combined report.

    Returns a dict with keys:
        'zscore'      – anomalies from Z-score method
        'iqr'         – anomalies from IQR method
        'rolling_avg' – anomalies from rolling-average method
        'summary'     – union of unique anomalous indices with highest severity
    """
    z_results = zscore_anomalies(values, timestamps, zscore_threshold)
    iqr_results = iqr_anomalies(values, timestamps, iqr_multiplier)
    roll_results = rolling_avg_anomalies(values, timestamps, rolling_window, rolling_threshold_pct)

    severity_rank = {"low": 1, "medium": 2, "high": 3}
    combined: dict[int, dict] = {}
    for entry in z_results + iqr_results + roll_results:
        idx = entry["index"]
        if idx not in combined:
            combined[idx] = entry
        else:
            existing_rank = severity_rank.get(combined[idx]["severity"], 0)
            new_rank = severity_rank.get(entry["severity"], 0)
            if new_rank > existing_rank:
                combined[idx]["severity"] = entry["severity"]

    summary = sorted(combined.values(), key=lambda x: x["index"])

    return {
        "zscore": z_results,
        "iqr": iqr_results,
        "rolling_avg": roll_results,
        "summary": summary,
        "total_anomalies": len(summary),
        "high_severity_count": sum(1 for a in summary if a["severity"] == "high"),
    }


# ---------------------------------------------------------------------------
# Private severity helpers
# ---------------------------------------------------------------------------

def _zscore_severity(deviation: float, threshold: float) -> str:
    if deviation >= threshold * 2:
        return "high"
    if deviation >= threshold * 1.4:
        return "medium"
    return "low"


def _iqr_severity(deviation_iqr_multiples: float) -> str:
    if deviation_iqr_multiples >= 3.0:
        return "high"
    if deviation_iqr_multiples >= 1.5:
        return "medium"
    return "low"


def _pct_severity(pct: float, base_threshold: float) -> str:
    if pct >= base_threshold * 3:
        return "high"
    if pct >= base_threshold * 1.75:
        return "medium"
    return "low"
