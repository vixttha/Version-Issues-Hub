from pathlib import Path
import hashlib, json, subprocess, shutil, re
from xml.etree import ElementTree as ET
from geometry import VIEWBOX, RINGS, crop_svg

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BASE = "388c6ef968aa15edf3caa34e9de6819dcda24e7f"
LOCK = "brand-identity/08-review/brand-lock.json"
def sha(b): return hashlib.sha256(b).hexdigest()
def git_show(path): return subprocess.check_output(["git", "-C", str(ROOT), "show", BASE + ":" + path])
def validate_canvas(svg):
    doc = ET.fromstring(svg)
    ns = "{http://www.w3.org/2000/svg}"
    divider = {"id":"divider","x":"220","y":"768","width":"1008","height":"12","fill":"#315BCD"}
    if doc.tag != ns+"svg" or doc.attrib.get("viewBox") != "0 0 1448 1086":
        raise ValueError("unexpected canvas dimensions")
    if [r.attrib for r in doc.iter(ns+"rect")] != [divider]:
        raise ValueError("unexpected background or divider")
    return doc
def prepare():
    # V1 is an immutable approved baseline, not an implementation target.
    baseline="aafbca6e6d742262b1508f965023a69b370fc8ba"
    for path in ("brand-identity/10-motion/sequential-v1","brand-identity/10-motion/approvals/sequential-v1.json",".github/workflows/brand-motion-experiment.yml"):
        subprocess.run(["git","-C",str(ROOT),"diff","--exit-code",baseline,"HEAD","--",path],check=True)
    lock_bytes = git_show(LOCK)
    if (ROOT/LOCK).read_bytes() != lock_bytes: raise ValueError("brand lock changed")
    lock = json.loads(lock_bytes)
    if lock["decision_id"] != "VIB-BRAND-LOCK-001" or len(lock["files"]) != 8: raise ValueError("unexpected lock")
    for f in lock["files"]:
        raw = git_show(f["path"])
        if sha(raw) != f["sha256"] or (ROOT/f["path"]).read_bytes() != raw: raise ValueError("locked artwork differs: "+f["path"])
    out = HERE/"build"
    out.mkdir(exist_ok=True)
    gsap = HERE/"node_modules/gsap/dist/gsap.min.js"
    template = (HERE/"template.html").read_text()
    records = []
    for theme,name,accent in [("light","vib-lockup-light.svg","#111827"),("dark","vib-lockup.svg","#879BC4")]:
        path = "brand-identity/08-review/circuit-industrial-v2/"+name
        raw = git_show(path)
        svg = raw.decode()
        if theme == "light":
            rect = '<rect width="1448" height="1086" fill="#F3F6FC"/>'
            if svg.count(rect) != 1: raise ValueError("unexpected light background")
            svg = svg.replace(rect,"",1)
        doc = validate_canvas(svg)
        if len([x for x in doc.iter() if x.get("id") == "checkpoint-circuit"]) != 1: raise ValueError("missing circuit")
        # Inset overlays inside the exact hollow rim bounds; avoid alpha edge drift.
        rings = []
        for i,(x,y) in enumerate(RINGS):
            d = f"M{x+2} {y+2}h100v100h-100Z M{x+18} {y+18}h68v68h-68Z"
            rings.append(f'<svg xmlns="http://www.w3.org/2000/svg" class="activation-layer" id="activation-{i}" viewBox="{VIEWBOX}" aria-hidden="true" style="opacity:0;visibility:hidden"><path d="{d}" fill="#FFFFFF" fill-rule="evenodd"/></svg>')
        if svg.count("</svg>") != 1: raise ValueError("unexpected SVG root")
        derived = "\n".join(rings)
        target = out/theme
        target.mkdir(exist_ok=True)
        shutil.copyfile(gsap,target/"gsap.min.js")
        (target/"index.html").write_text(template.replace("<!-- APPROVED SVG -->",derived))
        reference = out/(theme+"-reference")
        reference.mkdir(exist_ok=True)
        shutil.copyfile(gsap,reference/"gsap.min.js")
        # Reference is the unchanged transparent original SVG with no animation layer.
        baseline = template.replace("<!-- APPROVED SVG -->",crop_svg(svg)).replace('data-duration="6"','data-duration="1"')
        start = baseline.index("[0.4,1.45,2.5].forEach")
        end = baseline.index("window.__timelines.sequential = tl;",start)
        baseline = baseline[:start] + 'tl.to({}, {duration:1}, 0);\n' + baseline[end:]
        (reference/"index.html").write_text(baseline)
        uncropped=out/(theme+"-uncropped")
        uncropped.mkdir(exist_ok=True)
        shutil.copyfile(gsap,uncropped/"gsap.min.js")
        (uncropped/"index.html").write_text(baseline.replace(f'viewBox="{VIEWBOX}"','viewBox="0 0 1448 1086"',1))
        records.append({"theme":theme,"source":path,"source_sha256":sha(raw),"overlay_composition_sha256":sha((target/"index.html").read_bytes()),"reference_composition_sha256":sha((reference/"index.html").read_bytes())})
    (out/"source-manifest.json").write_text(json.dumps({"source_commit":BASE,"brand_lock":lock["decision_id"],"version":"V1.1","viewBox":VIEWBOX,"variants":records},indent=2)+"\n")
if __name__ == "__main__": prepare()
