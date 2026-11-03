import json
import struct
from pathlib import Path


LEARN_ROOT = Path(__file__).resolve().parents[1]


def test_manifest_has_required_pwa_metadata():
    manifest_path = LEARN_ROOT / "public" / "manifest.webmanifest"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["name"] == "Alpha One Labs Learn"
    assert manifest["short_name"] == "Learn"
    assert manifest["id"] == "/"
    assert manifest["start_url"] == "/"
    assert manifest["scope"] == "/"
    assert manifest["display"] == "standalone"
    assert manifest["theme_color"] == "#D4AF37"
    assert manifest["background_color"] == "#FFFFFF"


def test_manifest_icons_exist_at_declared_sizes():
    manifest_path = LEARN_ROOT / "public" / "manifest.webmanifest"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert {icon["sizes"] for icon in manifest["icons"]} == {"192x192", "512x512"}

    for icon in manifest["icons"]:
        icon_path = LEARN_ROOT / "public" / icon["src"].lstrip("/")
        assert icon_path.is_file(), icon["src"]

        with icon_path.open("rb") as image:
            assert image.read(8) == b"\x89PNG\r\n\x1a\n"
            length = struct.unpack(">I", image.read(4))[0]
            assert image.read(4) == b"IHDR"
            width, height = struct.unpack(">II", image.read(8))
        assert f"{width}x{height}" == icon["sizes"]


def test_base_links_manifest_and_theme_colors():
    base_path = LEARN_ROOT / "public" / "base.html"
    base = base_path.read_text(encoding="utf-8")

    assert 'rel="manifest"' in base
    assert 'href="/manifest.webmanifest"' in base
    assert base.count('name="theme-color"') == 2
