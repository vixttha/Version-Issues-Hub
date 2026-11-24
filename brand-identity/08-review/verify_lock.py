"""Verify exact approved VIB SVGs and approved foundation on the dedicated branch."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
lock = json.loads((ROOT / "brand-identity/08-review/brand-lock.json").read_text(encoding="utf-8"))
decision = json.loads((ROOT / "brand-identity/01-strategy/creative-decision.json").read_text(encoding="utf-8"))
assert lock["status"] == "OWNER_APPROVED_VISUAL_BASELINE"
assert lock["logo"] == "Circuit Industrial v2"
assert decision["names"] == {"product": lock["product"], "wordmark": lock["wordmark"]}
assert decision["slogans"] == {"primary": lock["primary_slogan"], "secondary": lock["secondary_slogan"]}
assert all(decision["palette"][k] == v for k, v in lock["palette"].items())
expected = {"vib-avatar.svg", "vib-lockup-dark.svg", "vib-lockup-light.svg", "vib-lockup.svg", "vib-logo-light.svg", "vib-logo.svg", "vib-monochrome-white.svg", "vib-monochrome.svg"}
prefix = "brand-identity/08-review/circuit-industrial-v2/"
assert {entry["path"] for entry in lock["files"]} == {prefix + name for name in expected}
assert len(lock["files"]) == 8
for entry in lock["files"]:
    path = ROOT / entry["path"]
    assert path.is_file() and not path.is_symlink()
    data = path.read_bytes()
    assert hashlib.sha256(data).hexdigest() == entry["sha256"], entry["path"]
    assert hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest() == entry["git_blob"], entry["path"]
    print("LOCK verified:", entry["path"])
assert lock["limits"]["commercial_clearance"] == "pending"
print("8/8 exact locked SVGs and approved foundation verified")
