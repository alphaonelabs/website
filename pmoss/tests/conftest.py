import sys
import types
from pathlib import Path


PMOSS_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PMOSS_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


class Headers:
    def __init__(self, values=None):
        self._values = dict(values or {})

    @classmethod
    def new(cls, values=None):
        return cls(values)

    def get(self, name):
        return self._values.get(name.lower()) or self._values.get(name)

    def set(self, name, value):
        self._values[name.lower()] = value


class URL:
    def __init__(self, url):
        self.url = url
        self.searchParams = self
        self._params = {}
        if "?" in url:
            for pair in url.split("?", 1)[1].split("&"):
                if "=" in pair:
                    key, value = pair.split("=", 1)
                    self._params[key] = value

    @classmethod
    def new(cls, url):
        return cls(url)

    def get(self, name):
        return self._params.get(name)


class Response:
    def __init__(self, body="", *, status=200, headers=None):
        self.body = body
        self.status = status
        self.ok = 200 <= status < 300
        self.headers = headers or Headers.new()

    @classmethod
    def new(cls, body="", **kwargs):
        return cls(body, **kwargs)

    async def text(self):
        return self.body


class _CryptoSubtle:
    async def digest(self, *_args):
        return b"\x00" * 32


class _Crypto:
    subtle = _CryptoSubtle()


async def fetch(*_args, **_kwargs):
    return Response.new("{}", status=404)


js = types.ModuleType("js")
js.Response = Response
js.Headers = Headers
js.URL = URL
js.fetch = fetch
js.crypto = _Crypto()
sys.modules["js"] = js
