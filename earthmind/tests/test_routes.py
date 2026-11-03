import json
import os
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
        self.database.queries.append((self.sql, self.bindings, "all"))
        if "FROM alerts" in self.sql:
            return SimpleNamespace(results=self.database.alerts)
        return SimpleNamespace(results=self.database.readings)

    async def run(self):
        self.database.queries.append((self.sql, self.bindings, "run"))
        return SimpleNamespace(meta=SimpleNamespace(last_row_id=17))

    async def first(self):
        self.database.queries.append((self.sql, self.bindings, "first"))
        return None


class FakeDatabase:
    def __init__(self):
        self.readings = []
        self.alerts = [{"id": 1, "type": "threshold", "is_active": 1}]
        self.queries = []

    def prepare(self, sql):
        return FakeStatement(self, sql)


class FakeRequest:
    def __init__(self, url, method="GET", body=None):
        self.url = url
        self.method = method
        self.body = body

    async def json(self):
        return self.body


@pytest.fixture
def env():
    return SimpleNamespace(DB=FakeDatabase(), AI=SimpleNamespace(run=None))


async def fetch(env, url, method="GET", body=None):
    return await index.on_fetch(FakeRequest(url, method, body), env)


def response_json(response):
    return json.loads(response.body)


@pytest.mark.asyncio
async def test_health_route(env):
    response = await fetch(env, "https://earthmind.test/api/health")

    assert response.status == 200
    assert response_json(response) == {"status": "ok", "service": "earthmind"}


@pytest.mark.asyncio
async def test_get_data_route(env):
    env.DB.readings = [{"id": 2, "parameter": "humidity", "value": 50}]

    response = await fetch(env, "https://earthmind.test/api/data")

    assert response.status == 200
    assert response_json(response) == {
        "data": [{"id": 2, "parameter": "humidity", "value": 50}],
        "count": 1,
    }


@pytest.mark.asyncio
async def test_post_data_route(env):
    response = await fetch(
        env,
        "https://earthmind.test/api/data",
        method="POST",
        body={
            "source": "sensor-1",
            "source_type": "iot_sensor",
            "parameter": "humidity",
            "value": 50,
            "timestamp": "2026-01-01T00:00:00Z",
        },
    )

    assert response.status == 201
    assert response_json(response) == {"id": 17, "status": "created"}
    assert env.DB.queries[0][2] == "run"


@pytest.mark.asyncio
async def test_anomalies_requires_parameter(env):
    response = await fetch(env, "https://earthmind.test/api/anomalies")

    assert response.status == 400
    assert response_json(response) == {"error": "'parameter' query param is required"}


@pytest.mark.parametrize(
    "path",
    [
        "/api/data?limit=abc",
        "/api/anomalies?parameter=pm2_5&limit=abc",
        "/api/trends?parameter=pm2_5&limit=abc",
    ],
)
@pytest.mark.asyncio
async def test_non_integer_limit_returns_bad_request(env, path):
    response = await fetch(env, f"https://earthmind.test{path}")

    assert response.status == 400
    assert response_json(response) == {"error": "'limit' must be an integer"}
    assert env.DB.queries == []


@pytest.mark.parametrize(
    ("path", "expected_limit"),
    [
        ("api/data?limit=-1", 1),
        ("api/anomalies?parameter=pm2_5&limit=-1", 1),
        ("api/trends?parameter=pm2_5&limit=-1", 1),
    ],
)
@pytest.mark.asyncio
async def test_negative_limit_is_clamped_to_one(env, path, expected_limit):
    response = await fetch(env, f"https://earthmind.test/{path}")

    assert response.status == 200
    assert env.DB.queries[-1][1][-1] == expected_limit


@pytest.mark.asyncio
async def test_get_alerts_route(env):
    response = await fetch(env, "https://earthmind.test/api/alerts")

    assert response.status == 200
    assert response_json(response) == {
        "alerts": [{"id": 1, "type": "threshold", "is_active": 1}],
        "count": 1,
    }
    assert env.DB.queries[0][2] == "all"


@pytest.mark.asyncio
async def test_post_alert_route(env):
    response = await fetch(
        env,
        "https://earthmind.test/api/alerts",
        method="POST",
        body={"type": "manual", "severity": "low", "message": "Check sensor"},
    )

    assert response.status == 201
    assert response_json(response) == {"id": 17, "status": "created"}
    assert env.DB.queries[0][2] == "run"


@pytest.mark.asyncio
async def test_post_resolve_alert_route(env):
    response = await fetch(
        env, "https://earthmind.test/api/alerts/1/resolve", method="POST"
    )

    assert response.status == 200
    assert response_json(response) == {"id": 1, "status": "resolved"}
    assert env.DB.queries[0][2] == "run"


@pytest.mark.asyncio
async def test_put_resolve_alert_route(env):
    response = await fetch(
        env, "https://earthmind.test/api/alerts/1/resolve", method="PUT"
    )

    assert response.status == 200
    assert response_json(response) == {"id": 1, "status": "resolved"}
    assert env.DB.queries[0][2] == "run"


@pytest.mark.asyncio
async def test_get_resolve_alert_route_is_method_not_allowed(env):
    response = await fetch(env, "https://earthmind.test/api/alerts/1/resolve")

    assert response.status == 405
    assert response_json(response) == {"error": "Method not allowed"}
    assert env.DB.queries == []


@pytest.mark.asyncio
async def test_unknown_route_returns_not_found(env):
    response = await fetch(env, "https://earthmind.test/api/unknown")

    assert response.status == 404
    assert response_json(response) == {"error": "Not found"}
