"""Build downloads/alpha-one-labs-design-system.zip from the design system files."""
import pathlib, zipfile

ROOT = pathlib.Path(__file__).parent
FILES = ["brand.css", "tokens.json", "chrome.js", "index.html", "README.md"]
out = ROOT / "downloads" / "alpha-one-labs-design-system.zip"
out.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for name in FILES:
        z.write(ROOT / name, f"alpha-one-labs-design-system/{name}")
    for f in sorted((ROOT / "assets").rglob("*")):
        if f.is_file():
            z.write(f, f"alpha-one-labs-design-system/{f.relative_to(ROOT)}")
print(out, out.stat().st_size // 1024, "KB")
