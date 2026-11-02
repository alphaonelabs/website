import asyncio
import json
import os
import re
import sys
import types
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

try:
    import workers  # noqa: F401
except ModuleNotFoundError as error:
    if error.name != "workers":
        raise

    workers = types.ModuleType("workers")

    class Response:
        def __init__(self, body="", headers=None, status=200):
            self.body = body
            self.headers = headers or {}
            self.status = status

    workers.WorkerEntrypoint = object
    workers.Response = Response
    sys.modules["workers"] = workers

import index


class FakeStatement:
    def __init__(self, database, sql):
        self.database = database
        self.sql = sql
        self.bindings = ()

    def bind(self, *bindings):
        self.bindings = bindings
        return self

    async def all(self):
        self.database.queries.append((self.sql, self.bindings))
        if "SELECT DISTINCT parameter" in self.sql:
            return SimpleNamespace(results=[{"parameter": "pm2_5"}])

        parameter, limit = self.bindings
        rows = [row for row in self.database.rows if row["parameter"] == parameter]
        rows = sorted(rows, key=lambda row: row["timestamp"], reverse=True)[:limit]
        return SimpleNamespace(
            results=sorted(rows, key=lambda row: row["timestamp"])
        )


class FakeDatabase:
    def __init__(self, rows):
        self.rows = rows
        self.queries = []

    def prepare(self, sql):
        return FakeStatement(self, sql)


@pytest.fixture
def env():
    rows = [
        {
            "parameter": "pm2_5",
            "timestamp": f"2024-01-0{day}T00:00:00Z",
            "value": day,
        }
        for day in range(1, 5)
    ]
    return SimpleNamespace(
        DB=FakeDatabase(rows),
        MAX_READINGS_PER_QUERY="3",
        ANOMALY_ZSCORE_THRESHOLD="3.75",
    )


def _analysis_values(monkeypatch):
    observed = []

    def analyze(values, *args, **kwargs):
        observed.append(list(values))
        return {"values": list(values)}

    monkeypatch.setattr(index, "analyze_trends", analyze)
    return observed


@pytest.mark.asyncio
async def test_all_analysis_handlers_use_latest_rows_in_chronological_order(
    env, monkeypatch
):
    observed = _analysis_values(monkeypatch)
    anomaly_thresholds = []

    def detect(values, timestamps, zscore_threshold=2.5):
        observed.append(list(values))
        anomaly_thresholds.append(zscore_threshold)
        return {"summary": [{"index": 0}], "zscore": []}

    async def ai_trends(_env, _parameter, _stats):
        return "trend"

    async def explain(_env, _parameter, _anomaly):
        return "explanation"

    async def summary(_env, _stats):
        return "summary"

    monkeypatch.setattr(index, "detect_anomalies", detect)
    monkeypatch.setattr(index, "analyze_trends_with_ai", ai_trends)
    monkeypatch.setattr(index, "explain_anomaly", explain)
    monkeypatch.setattr(index, "generate_dashboard_summary", summary)

    await index._get_anomalies(
        None, env, SimpleNamespace(query="parameter=pm2_5&limit=500")
    )
    await index._get_trends(
        None, env, SimpleNamespace(query="parameter=pm2_5&limit=500")
    )
    await index._analytics_trends(
        None, env, SimpleNamespace(query="parameter=pm2_5")
    )
    await index._analytics_explain_anomaly(
        None, env, SimpleNamespace(query="parameter=pm2_5")
    )
    await index._analytics_summary(None, env, SimpleNamespace(query=""))

    expected_values = [2, 3, 4]
    assert observed == [expected_values] * 5
    assert anomaly_thresholds == [3.75, 3.75]
    reading_queries = [
        query for query in env.DB.queries if "WHERE parameter = ?" in query[0]
    ]
    assert len(reading_queries) == 5
    for sql, bindings in reading_queries:
        assert re.search(
            r"FROM\s*\(\s*SELECT value, timestamp FROM readings "
            r"WHERE parameter = \? ORDER BY timestamp DESC LIMIT \?\s*"
            r"\) ORDER BY timestamp ASC",
            sql,
        )
        assert bindings[1] == 3


@pytest.mark.asyncio
async def test_anomaly_query_threshold_overrides_environment(env, monkeypatch):
    thresholds = []

    def detect(_values, _timestamps, zscore_threshold=2.5):
        thresholds.append(zscore_threshold)
        return {}

    monkeypatch.setattr(index, "detect_anomalies", detect)

    await index._get_anomalies(
        None,
        env,
        SimpleNamespace(query="parameter=pm2_5&zscore_threshold=4.25"),
    )

    assert thresholds == [4.25]


def test_invalid_config_uses_safe_defaults():
    env = SimpleNamespace(
        MAX_READINGS_PER_QUERY="0",
        ANOMALY_ZSCORE_THRESHOLD="nan",
    )

    assert index._max_readings(env) == 1000
    assert index._env_positive_float(env, "ANOMALY_ZSCORE_THRESHOLD", 2.5) == 2.5
