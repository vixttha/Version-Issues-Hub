"""Verify the branded README against its immutable brand/product sources."""
import hashlib, json, re, subprocess
from pathlib import Path
from html.parser import HTMLParser

ROOT=Path(__file__).resolve().parents[1]
W=ROOT/"workspace/v0.0.1"
record=json.loads((W/"asset-lock.json").read_text())
assert record["decision"]=="VIB-BRAND-LOCK-001"
assert record["brand_commit"]=="388c6ef968aa15edf3caa34e9de6819dcda24e7f"
assert record["source_commit"]=="114a22196eab578b3053002f8eb7af935b26fe89"
def git(*args):
    return subprocess.check_output(["git",*args],cwd=ROOT)
lock=json.loads(git("show",record["brand_commit"]+":brand-identity/08-review/brand-lock.json"))
assert lock["status"]=="OWNER_APPROVED_VISUAL_BASELINE"
approved={e["path"]:e for e in lock["files"]}
expected={"assets/vib-logo.svg","assets/vib-logo-light.svg","assets/vib-lockup-dark.svg","assets/vib-lockup-light.svg"}
assert {e["file"] for e in record["files"]}==expected and len(record["files"])==4
for e in record["files"]:
    assert e["source_path"] in approved
    a=approved[e["source_path"]]
    assert e["sha256"]==a["sha256"] and e["git_blob"]==a["git_blob"]
    data=(W/e["file"]).read_bytes()
    assert hashlib.sha256(data).hexdigest()==a["sha256"]
    assert data==git("show",record["brand_commit"]+":"+e["source_path"])
    print("Exact locked asset:",e["file"])
draft=(W/"DRAFT.md").read_text()
assert draft.count("\n# ")==0 and draft.startswith("# "+lock["product"]+" (VIB)\n")
assert lock["primary_slogan"] in draft and lock["secondary_slogan"] in draft
assert "not released" in draft and "no LICENSE file" in draft
class Header(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag in ("source","img"): self.images.append((tag,a))
h=Header(); h.feed(draft)
assert h.images==[("source",{"media":"(prefers-color-scheme: dark)","srcset":"assets/vib-logo.svg"}),("img",{"alt":"VIB — angular lettermark joined by a three-checkpoint circuit","src":"assets/vib-logo-light.svg","width":"380"})]
for _,a in h.images:
    assert (W/(a.get("srcset") or a["src"])).is_file()
prefix="https://github.com/vixttha/Version-Issues-Hub/blob/"+record["source_commit"]+"/"
paths=re.findall(re.escape(prefix)+r"([^\s)#]+)",draft)
assert paths
for path in sorted(set(paths)):
    git("cat-file","-e",record["source_commit"]+":"+path)
print("Verified",len(set(paths)),"pinned product paths and both theme assets")
commands=re.findall(r"```sh\n(.*?)\n```",draft,re.S)
assert commands[0]=="git clone https://github.com/vixttha/Version-Issues-Hub.git\ncd Version-Issues-Hub\ngit checkout --detach 114a22196eab578b3053002f8eb7af935b26fe89\npython -m tools.session --target vixttha/Version-Issues-Hub inspect"
assert commands[-1]=="python -B -m unittest discover -s tests -v"
print("Exact documented quickstart and test commands verified")
