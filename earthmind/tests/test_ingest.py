"""Ingestion route tests with a local Worker shim and an in-memory D1 fake."""

import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


@pytest.fixture
def worker(monkeypatch):
    class Response:
        def __init__(self, body, *, status=200, headers=None):
            self.body = json.loads(body)
            self.status = status
            self.headers = headers

    monkeypatch.setitem(sys.modules, "workers", SimpleNamespace(
        WorkerEntrypoint=object, Response=Response,
    ))
    source = Path(__file__).parents[1] / "src"
    monkeypatch.syspath_prepend(str(source))
    spec = importlib.util.spec_from_file_location("earthmind_index", source / "index.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.EarthMind()


class Database:
    def __init__(self):
        self.bindings = []

    def prepare(self, sql):
        assert sql.startswith("INSERT INTO readings ")
        return self

    def bind(self, *values):
        self.bindings.append(values)
        return self

    async def run(self):
        return SimpleNamespace(meta=SimpleNamespace(last_row_id=42))


async def ingest(worker, body):
    async def request_json():
        return body

    database = Database()
    worker.env = SimpleNamespace(DB=database)
    request = SimpleNamespace(url="https://example.test/api/data", method="POST", json=request_json)
    response = await worker.fetch(request)
    return response, database


@pytest.fixture
def reading():
    return {
        "source": "test-sensor", "source_type": "sensor", "parameter": "rainfall",
        "value": 0, "timestamp": "2026-11-02T00:00:00Z",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("value", [0, 0.0, "0", 12.5])
async def test_valid_values_are_inserted(worker, reading, value):
    reading["value"] = value
    response, database = await ingest(worker, reading)
    assert response.status == 201
    assert response.body == {"id": 42, "status": "created"}
    assert database.bindings[0][6] == float(value)


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["source", "source_type", "parameter", "value", "timestamp"])
@pytest.mark.parametrize("missing", ["absent", None, ""])
async def test_missing_fields_are_rejected(worker, reading, field, missing):
    if missing == "absent":
        del reading[field]
    else:
        reading[field] = missing
    response, database = await ingest(worker, reading)
    assert response.status == 400
    assert field in response.body["error"]
    assert database.bindings == []


@pytest.mark.asyncio
@pytest.mark.parametrize("value", ["nan", "inf", "-inf", "1e400", float("nan"), float("inf"), "bad", {}, [], True, False, 10**400])
async def test_invalid_values_are_rejected(worker, reading, value):
    reading["value"] = value
    response, database = await ingest(worker, reading)
    assert response.status == 400
    assert "value" in response.body["error"]
    assert database.bindings == []


@pytest.mark.asyncio
@pytest.mark.parametrize("latitude,longitude", [(0, 0), (-90, -180), (90, 180), ("12.5", "-45.5"), (None, None)])
async def test_valid_coordinates(worker, reading, latitude, longitude):
    reading.update(latitude=latitude, longitude=longitude)
    response, database = await ingest(worker, reading)
    assert response.status == 201
    assert database.bindings[0][3:5] == tuple(
        None if value is None else float(value) for value in (latitude, longitude)
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("field,value", [
    ("latitude", -90.1), ("latitude", 90.1), ("longitude", -180.1), ("longitude", 180.1),
    ("latitude", "nan"), ("longitude", "inf"), ("latitude", ""), ("longitude", "bad"),
    ("latitude", {}), ("longitude", 10**400),
    ("latitude", True), ("latitude", False), ("longitude", True), ("longitude", False),
])
async def test_invalid_coordinates_are_rejected(worker, reading, field, value):
    reading[field] = value
    response, database = await ingest(worker, reading)
    assert response.status == 400
    assert field in response.body["error"]
    assert database.bindings == []


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["source", "source_type", "parameter", "timestamp"])
@pytest.mark.parametrize("value", [[], {}, ["unexpected"], {"unexpected": 1}])
async def test_container_fields_are_rejected(worker, reading, field, value):
    reading[field] = value
    response, database = await ingest(worker, reading)
    assert response.status == 400
    assert field in response.body["error"]
    assert database.bindings == []


@pytest.mark.asyncio
@pytest.mark.parametrize("body", [None, [], "text", 0, True])
async def test_non_object_body_is_rejected(worker, body):
    response, database = await ingest(worker, body)
    assert response.status == 400
    assert database.bindings == []
