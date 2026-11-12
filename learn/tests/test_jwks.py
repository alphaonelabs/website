import base64
import json

from tests.helpers import MockRequest, make_env, load_worker

worker = load_worker()
URL = "http://localhost/.well-known/jwks.json"


def _jwk(kid="k1"):
    x = base64.urlsafe_b64encode(bytes(range(32))).decode("ascii").rstrip("=")
    return {"kty": "OKP", "crv": "Ed25519", "x": x, "kid": kid}


async def _get(raw):
    env = make_env()
    env.CREDENTIAL_PUBLIC_JWKS = raw
    return await worker.api_jwks(MockRequest(method="GET", url=URL), env)


async def test_jwks_endpoint_serves_keys():
    r = await _get(json.dumps([_jwk("k1")]))
    body = json.loads(r.body)
    assert r.status == 200
    assert body["keys"][0]["kid"] == "k1"
    assert r.headers["Cache-Control"].startswith("public")


async def test_jwks_endpoint_empty_when_unconfigured():
    r = await _get("")
    assert r.status == 200
    assert json.loads(r.body) == {"keys": []}


async def test_jwks_endpoint_500_on_invalid_config():
    r = await _get("not json")
    assert r.status == 500


async def test_jwks_endpoint_never_echoes_private_material():
    r = await _get(json.dumps([{**_jwk(), "d": "SECRET"}]))
    assert r.status == 500
    assert "SECRET" not in r.body