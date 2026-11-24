"""Check the portable brand kit and its registered PNG exports."""

import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit
import re

from png_integrity import inspect_png

KIT = Path(__file__).resolve().parent
ASSETS = KIT / "09-assets"
DECISION = KIT / "01-strategy" / "creative-decision.json"
WEIGHTS = {"brand_fit": 35, "artistic_character": 25,
           "distinctiveness": 25, "versatility": 15}
REQUIRED_DOCS = (
    "README.md", "01-strategy/brief.md", "01-strategy/creative-direction.md",
    "02-naming/naming.md",
    "03-messaging/voice.md", "04-logo/logo.md", "05-wordmark/wordmark.md",
    "06-visual-system/system.md", "07-applications/applications.md",
    "08-review/review.md", "09-assets/README.md",
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_license():
    license_file = KIT / "LICENSE"
    require(license_file.is_file() and not license_file.is_symlink(),
            "Missing regular brand identity LICENSE file")
    require(bool(license_file.read_text(encoding="utf-8").strip()),
            "Brand identity LICENSE file is empty")


def check_docs():
    project_root = KIT.parent
    for relative in REQUIRED_DOCS:
        source = KIT / relative
        content = source.read_text(encoding="utf-8")
        require(content.startswith("# "), f"{relative}: missing title")
        for reference in re.findall(r"\[[^\]\n]+\]\(([^)\n]+)\)", content):
            target = urlsplit(reference)
            if target.scheme or target.netloc or not target.path:
                continue
            destination = (source.parent / unquote(target.path)).resolve()
            require(destination.is_relative_to(project_root) and destination.exists(),
                    f"{relative}: missing or external local path {target.path}")


def check_inventory(assets):
    names = {asset["file"] for asset in assets}
    require(len(names) == len(assets), "Duplicate manifest filename")
    discovered = set()
    for path in ASSETS.rglob("*"):
        if path.is_dir() or not path.name.lower().endswith(".png"):
            continue
        relative = path.relative_to(ASSETS)
        require(path.parent == ASSETS and path.name.endswith(".png"),
                f"PNG exports must use lowercase .png in the asset directory: {relative}")
        discovered.add(path.name)
    unexpected = sorted(discovered - names)
    missing = sorted(names - discovered)
    require(not (unexpected or missing),
            f"PNG directory and manifest differ (unregistered: {unexpected}, missing: {missing})")


def check_png(asset):
    name = asset["file"]
    require(name == Path(name).name and name.endswith(".png"), f"Invalid asset path: {name}")
    file = ASSETS / name
    require(file.is_file() and not file.is_symlink(), f"Missing regular PNG: {name}")
    payload = file.read_bytes()
    try:
        width, height, has_alpha = inspect_png(payload)
    except ValueError as error:
        raise ValueError(f"{name}: {error}") from error
    manifest_width, manifest_height = asset.get("width"), asset.get("height")
    require(type(manifest_width) is int and type(manifest_height) is int,
            f"{name}: PNG dimensions must be integers")
    require((width, height) == (manifest_width, manifest_height),
            f"{name}: unexpected dimensions {width}x{height}")
    require(isinstance(asset["alpha"], bool) and asset["alpha"] == has_alpha,
            f"{name}: unexpected PNG alpha channel metadata")
    require(hashlib.sha256(payload).hexdigest() == asset["sha256"], f"{name}: wrong SHA-256")
    require(asset["generated_with"] == "@Images", f"{name}: must record @Images generation")
    for key in ("role", "alt", "source", "status"):
        require(isinstance(asset[key], str) and asset[key].strip(), f"{name}: missing {key}")
    print(f"{name}: {width}x{height}, alpha channel {asset['alpha']}, SHA-256 verified")


def require_text(value, label):
    require(isinstance(value, str) and bool(value.strip()), f"Missing {label}")


def check_artwork_gate(decision):
    initial = decision.get("initial_category")
    require_text(initial, "initial logo category")
    require_text(decision.get("art_style"), "lead art style")

    category_fit = decision.get("category_fit", {})
    require(isinstance(category_fit, dict) and initial in category_fit and len(category_fit) >= 2,
            "Screen the initial category and at least one alternative")
    for category, assessment in category_fit.items():
        require_text(category, "screened category")
        require(isinstance(assessment, dict) and type(assessment.get("fits")) is bool,
                f"{category}: record the fit decision")
        require_text(assessment.get("reason"), f"{category} fit rationale")

    concepts = decision.get("concepts", [])
    require(isinstance(concepts, list) and len(concepts) >= 3, "Record at least three concept examples")
    totals = {}
    examples = set()
    for concept in concepts:
        require(isinstance(concept, dict), "Each concept must be a record")
        identity = concept.get("id")
        require_text(identity, "concept ID")
        require(identity not in totals, f"Duplicate concept ID: {identity}")
        category = concept.get("category")
        require_text(category, f"{identity} category")
        require(category_fit.get(category, {}).get("fits"), f"{identity}: category must fit the brief")
        for field in ("art_style", "example", "rationale"):
            require_text(concept.get(field), f"{identity} {field}")
        example = " ".join(concept["example"].casefold().split())
        require(example not in examples, f"{identity}: concept example must be distinct")
        examples.add(example)

        scores = concept.get("scores", {})
        require(isinstance(scores, dict) and set(scores) == set(WEIGHTS) and all(
            type(score) is int and 1 <= score <= 5 for score in scores.values()
        ), f"{identity}: score each criterion with an integer from 1 through 5")
        totals[identity] = sum(scores[key] * weight for key, weight in WEIGHTS.items())

    selected = decision.get("selected_concept")
    require_text(selected, "selected concept")
    require(totals.get(selected) == max(totals.values()), "Select a highest-scoring concept")
    require_text(decision.get("selection_reason"), "selection rationale")

    names = decision.get("names", {})
    require(isinstance(names, dict), "Record proposed product and wordmark names")
    confirmation = decision.get("confirmation")
    require(isinstance(confirmation, dict), "Owner name confirmation is required before artwork")
    for key in ("product", "wordmark"):
        require_text(names.get(key), f"proposed {key} name")
        require(names[key] == confirmation.get(key), f"Confirm the exact {key} name before artwork")
    require_text(confirmation.get("reference"), "owner confirmation reference")


def validate_production(kind, assets, ready_for_artwork, decision):
    if kind == "template":
        require(not assets and not ready_for_artwork, "Start a project kit before adding brand artwork")
    if assets or ready_for_artwork or decision.get("confirmation") is not None:
        check_artwork_gate(decision)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ready-for-artwork", action="store_true",
                        help="require a scored direction and explicit owner name confirmation")
    parser.add_argument("--ready-for-handoff", action="store_true",
                        help="require approved logo and wordmark PNGs in the project inventory")
    args = parser.parse_args()
    check_license()
    check_docs()
    inventory = json.loads((ASSETS / "manifest.json").read_text(encoding="utf-8"))
    require(inventory["kit_version"] == "v0.0.1", "Unexpected kit version")
    kind = inventory["kind"]
    require(kind in {"template", "project"}, f"Invalid kit kind: {kind}")
    assets = inventory["assets"]
    check_inventory(assets)
    decision = json.loads(DECISION.read_text(encoding="utf-8"))
    require(isinstance(decision, dict), "The creative decision must be a record")
    validate_production(kind, assets, args.ready_for_artwork, decision)
    if args.ready_for_handoff:
        require(kind == "project", "Start a project kit before checking handoff")
        approved_roles = {asset["role"] for asset in assets if asset.get("status") == "approved"}
        require({"logo", "wordmark"} <= approved_roles,
                "Project handoff needs both logo and wordmark PNGs with status 'approved'")
    if args.ready_for_artwork:
        print("Creative decision and owner name confirmation recorded")
    for asset in assets:
        check_png(asset)
    print(f"Verified {kind} kit: {len(REQUIRED_DOCS)} documents and {len(assets)} PNGs")


if __name__ == "__main__":
    main()
