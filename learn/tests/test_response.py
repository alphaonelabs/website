"""
Tests for response-building helpers: json_resp(), ok(), err().
"""

import json
from tests.helpers import load_worker

worker = load_worker()


def _parse(resp):
    return json.loads(resp.body)


class TestJsonResp:
    def test_default_status_200(self):
        r = worker.json_resp({"key": "val"})
        assert r.status == 200

    def test_custom_status(self):
        r = worker.json_resp({"error": "bad"}, 422)
        assert r.status == 422

    def test_content_type_header(self):
        r = worker.json_resp({})
        assert r.headers.get("Content-Type") == "application/json"

    def test_cors_origin_header(self):
        r = worker.json_resp({})
        assert r.headers.get("Access-Control-Allow-Origin") == "*"

    def test_cors_methods_header(self):
        r = worker.json_resp({})
        assert "GET" in r.headers.get("Access-Control-Allow-Methods", "")

    def test_body_is_valid_json(self):
        r = worker.json_resp({"a": 1, "b": [1, 2]})
        parsed = _parse(r)
        assert parsed == {"a": 1, "b": [1, 2]}

    def test_list_body(self):
        r = worker.json_resp([1, 2, 3])
        assert _parse(r) == [1, 2, 3]

    def test_nested_dict(self):
        r = worker.json_resp({"outer": {"inner": True}})
        assert _parse(r)["outer"]["inner"] is True


class TestOk:
    def test_status_200(self):
        assert worker.ok().status == 200

    def test_success_true(self):
        assert _parse(worker.ok())["success"] is True

    def test_default_message(self):
        assert _parse(worker.ok())["message"] == "OK"

    def test_custom_message(self):
        assert _parse(worker.ok(msg="Done"))["message"] == "Done"

    def test_no_data_key_when_none(self):
        assert "data" not in _parse(worker.ok())

    def test_data_included(self):
        r = worker.ok({"token": "abc"})
        assert _parse(r)["data"] == {"token": "abc"}

    def test_data_and_message(self):
        r = worker.ok({"id": "1"}, "Created")
        parsed = _parse(r)
        assert parsed["data"] == {"id": "1"}
        assert parsed["message"] == "Created"


class TestErr:
    def test_default_status_400(self):
        assert worker.err("bad request").status == 400

    def test_custom_status(self):
        assert worker.err("not found", 404).status == 404

    def test_error_field_in_body(self):
        assert _parse(worker.err("something wrong"))["error"] == "something wrong"

    def test_no_success_key(self):
        assert "success" not in _parse(worker.err("fail"))

    def test_401_status(self):
        assert worker.err("unauth", 401).status == 401

    def test_500_status(self):
        assert worker.err("server error", 500).status == 500

    def test_cors_headers_present(self):
        r = worker.err("oops")
        assert r.headers.get("Access-Control-Allow-Origin") == "*"
