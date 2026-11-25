"""Deterministic single-file distribution, no third-party dependencies."""
import base64
import hashlib
import json
from pathlib import Path
import sys

root=Path(__file__).resolve().parent
names=("executor.py","challenger.sh","auditor.ps1","contract.json")
raw={n:(root/n).read_bytes() for n in names}
if any(b"\r\n" in value for value in raw.values()):raise RuntimeError("Noncanonical source checkout; expected LF")
payload={n:base64.b64encode(v).decode("ascii") for n,v in raw.items()}
hashes={n:hashlib.sha256(base64.b64decode(v)).hexdigest() for n,v in payload.items()}
header="PAYLOAD="+repr(payload)+"\nHASHES="+repr(hashes)+"\n"
launcher="""import base64,hashlib,subprocess,sys,tempfile
from pathlib import Path
with tempfile.TemporaryDirectory(prefix='tri-package-') as d:
    root=Path(d)
    for name,value in PAYLOAD.items():
        raw=base64.b64decode(value,validate=True)
        if hashlib.sha256(raw).hexdigest()!=HASHES[name]:raise RuntimeError('package integrity')
        (root/name).write_bytes(raw)
    raise SystemExit(subprocess.call([sys.executable,'-B',str(root/'executor.py')]))
"""
Path(sys.argv[1]).write_bytes((header+launcher).encode("utf-8"))
