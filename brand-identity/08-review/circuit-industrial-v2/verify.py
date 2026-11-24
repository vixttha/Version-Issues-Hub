"""Static validation for the draft SVG candidate; no renderer dependency."""
from pathlib import Path
import xml.etree.ElementTree as ET
import re
ROOT=Path(__file__).parent
NS="{http://www.w3.org/2000/svg}"
names={"vib-logo","vib-logo-light","vib-monochrome","vib-monochrome-white","vib-lockup","vib-lockup-dark","vib-lockup-light","vib-avatar"}
assert {p.stem for p in ROOT.glob("*.svg")} == names
colors={"#111827","#315BCD","#879BC4","#F3F6FC"}
canonical=None
for name in sorted(names):
    r=ET.parse(ROOT/(name+".svg")).getroot()
    assert r.tag==NS+"svg"
    assert {e.tag[len(NS):] for e in r.iter()} <= {"svg","title","desc","path","rect","g"}
    assert all(e.get("fill") in colors|{None} and not any(k.endswith("href") for k in e.attrib) for e in r.iter())
    marks=[r.find(NS+"path[@id='"+i+"']") for i in ["letter-v","letter-i","letter-b","checkpoint-circuit"]]
    assert all(e is not None and e.get("fill-rule")=="evenodd" for e in marks)
    geometry=[e.get("d") for e in marks]
    if canonical is None: canonical=geometry
    assert geometry==canonical
    assert geometry[2].count("M")==3 and geometry[3].count("M")==4
    holes=geometry[3].split(" M")[1:]
    for hole in holes:
        xy=[tuple(map(float,p)) for p in re.findall(r"([0-9.]+),([0-9.]+)",hole)]
        assert len(xy)==4
        assert max(x for x,y in xy)-min(x for x,y in xy)==64
        assert max(y for x,y in xy)-min(y for x,y in xy)==64
    if "lockup" in name:
        for id,label in [("product-name","Version-Issues-Hub-Branch"),("primary-slogan","Every issue. A checkpoint."),("secondary-slogan","Build. Verify. Advance.")]:
            g=r.find(NS+"g[@id='"+id+"']")
            assert g is not None and g.get("aria-label")==label and len(g)>0
    elif "avatar" not in name:
        assert r.find(NS+"rect") is None
    print(name+": static SVG checks passed")
