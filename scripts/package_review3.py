"""Build a local Review 3 snapshot with a SHA-256 inventory.

Run verification first. This archive includes the audit's unresolved items;
it is not certification that academic evidence or document corrections are complete.
"""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "submission"
DEST.mkdir(exist_ok=True)
allowed_dirs = {"docs", "evidence", "samples", "scripts", "tests", "static", "templates"}
allowed_suffixes = {".py", ".md", ".txt", ".docx", ".pptx", ".html", ".css", ".js", ".lang", ".ebnf", ".json", ".dot", ".png", ".pdf"}
files = []
for path in sorted(ROOT.rglob("*")):
    if not path.is_file():
        continue
    rel = path.relative_to(ROOT)
    if any(p.startswith(".") or p == "__pycache__" for p in rel.parts):
        continue
    if len(rel.parts) > 1 and rel.parts[0] not in allowed_dirs:
        continue
    if path.suffix.lower() not in allowed_suffixes and path.name != "LICENSE":
        continue
    files.append((path, rel.as_posix()))
manifest = {name: hashlib.sha256(path.read_bytes()).hexdigest() for path, name in files}
manifest_text = json.dumps(manifest, indent=2)
(DEST / "SHA256_MANIFEST.json").write_text(manifest_text, encoding="utf-8")
archive = DEST / "Review3_Package.zip"
with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
    for path, name in files:
        z.write(path, "Review3/" + name)
    z.writestr("Review3/SHA256_MANIFEST.json", manifest_text)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for name, expected in manifest.items():
        assert hashlib.sha256(z.read("Review3/" + name)).hexdigest() == expected
print(f"Packaged and hash-verified {len(files)} files: {archive}")
