"""
Tests for scanner short-circuiting, whiteboard persistence and the cached activity list.
"""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from tests.helpers import load_worker, MockRequest, MockDB, make_env, make_stmt

worker = load_worker()


class TestScannerProbe:
    def test_flags_common_probes(self):
        for path in ("/.env", "/backend/.env.local", "/wp-admin/x.php", "/wp/v2/templates",
                     "/phpinfo.php", "/.git/config", "/api/config.env"):
            assert worker._is_scanner_probe(path), path

    def test_leaves_real_paths_alone(self):
        for path in ("/", "/activity/gsoc-2027", "/.well-known/security.txt", "/environment",
                     "/css/a1-site.css", "/media/x.webp", "/api/activities", "/blog/wp-tips"):
            assert not worker._is_scanner_probe(path), path

    async def test_on_fetch_returns_404_without_touching_db(self):
        db = MagicMock()
        env = make_env(db=db)
        r = await worker.on_fetch(MockRequest(url="https://alphaonelabs.com/.env"), env)
        assert r.status == 404
        db.prepare.assert_not_called()


class TestWhiteboardStorage:
    def _do(self, stored):
        do = worker.ClassroomDO.__new__(worker.ClassroomDO)
        storage = SimpleNamespace(get=AsyncMock(return_value=stored), put=AsyncMock())
        do.ctx = SimpleNamespace(storage=storage)
        return do, storage

    async def test_saves_json_string(self):
        do, storage = self._do(None)
        await do._save_whiteboard_events([{"a": 1}])
        key, value = storage.put.call_args[0]
        assert key == "whiteboard_events" and json.loads(value) == [{"a": 1}]

    async def test_loads_json_string_and_tolerates_junk(self):
        do, _ = self._do(json.dumps([{"a": 1}]))
        assert await do._load_whiteboard_events() == [{"a": 1}]
        do, _ = self._do("not json")
        assert await do._load_whiteboard_events() == []
        do, _ = self._do(None)
        assert await do._load_whiteboard_events() == []

    async def test_keeps_last_1000(self):
        do, storage = self._do(None)
        await do._save_whiteboard_events([{"i": i} for i in range(1500)])
        saved = json.loads(storage.put.call_args[0][1])
        assert len(saved) == 1000 and saved[0] == {"i": 500}


class TestCachedActivityList:
    async def test_falls_back_to_live_query_without_cache(self):
        env = make_env(db=MockDB([make_stmt(all_results=[])]))
        r = await worker.api_list_activities_cached(MockRequest(url="http://localhost/api/activities"), env)
        assert r.status == 200
        assert json.loads(r.body)["activities"] == []
