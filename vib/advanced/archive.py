"""Read ZIP members without extraction; fixed-size bounds, strict inventory."""
import hashlib
import io
import json
from pathlib import Path
import zipfile
def inspect_zip(path,expected,digest):
    if path.stat().st_size>32*1024*1024:raise ValueError("Archive too large")
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=digest:raise ValueError("Archive digest mismatch")
    result={};folded=set()
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        if len(z.infolist())>200 or sum(i.file_size for i in z.infolist())>64*1024*1024:raise ValueError("Archive bounds")
        for info in z.infolist():
            n=info.filename
            if not n or "/" in n or "\\" in n or ":" in n or n in (".","..") or info.is_dir() or (info.external_attr>>16)&0o170000==0o120000:raise ValueError("Unsafe member")
            if n.casefold() in folded:raise ValueError("Duplicate member")
            folded.add(n.casefold())
            result[n]=z.read(info)
    if set(result)!=expected:raise ValueError("Archive inventory mismatch")
    return result
