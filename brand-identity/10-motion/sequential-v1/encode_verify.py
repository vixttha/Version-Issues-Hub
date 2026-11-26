from pathlib import Path
import hashlib, json, subprocess, shutil, re
from PIL import Image, ImageChops, ImageDraw

HERE=Path(__file__).resolve().parent
BUILD=HERE/"build"
EXPORT=BUILD/"exports"
W,H,N,FPS=960,720,144,24
STARTS=(0.5,1.4,2.3)
def check(ok,msg):
    if not ok: raise ValueError(msg)
def boundary(i): return (i*1000+FPS//2)//FPS
def canonical(im):
    im=im.convert("RGBA")
    im.paste((0,0,0,0),mask=im.getchannel("A").point(lambda x:255 if x==0 else 0))
    return im
def equal(a,b):
    return a.size==b.size and all(x.getbbox() is None for x in ImageChops.difference(a,b).split())
def ordered_files(folder,count):
    indexed=[]
    for p in folder.glob("*.png"):
        m=re.fullmatch(r"frame_(\d+)\.png",p.name)
        check(m is not None,f"unexpected frame filename {p.name}")
        indexed.append((int(m.group(1)),p))
    indexed.sort(key=lambda pair:pair[0])
    ids=[i for i,p in indexed]
    check(ids in [list(range(count)),list(range(1,count+1))],f"frame sequence not contiguous: {ids}")
    return [p for i,p in indexed]
def load_rgba(p):
    with Image.open(p) as im:
        check(im.size==(W,H) and "A" in im.getbands(),f"not RGBA: {p}")
        return canonical(im)
def active_checkpoint(i):
    # Exact integer arithmetic: each start and duration is specified in tenths of seconds.
    return next((j for j,s in enumerate((5,14,23)) if s*FPS<i*10<(s+9)*FPS),None)
def checkpoint_boxes():
    return [(int(x*W/1448)-2,int(y*H/1086)-2,int(X*W/1448)+3,int(Y*H/1086)+3)
            for x,y,X,Y in [(344,508,448,612),(700,428,804,532),(1104,508,1208,612)]]
def overlay_mask(base,overlay,box,accent):
    # Fail closed: no overlay pixels may touch the static logo outside its
    # fully opaque permitted checkpoint region, or use another accent color.
    check(base.size==overlay.size,"overlay dimensions")
    a=overlay.getchannel("A")
    if box is None:
        check(a.getbbox() is None,"unexpected nonempty resting overlay")
        return base.copy()
    allowed=Image.new("L",base.size,0)
    ImageDraw.Draw(allowed).rectangle((box[0],box[1],box[2]-1,box[3]-1),fill=255)
    check(ImageChops.multiply(a,ImageChops.invert(allowed)).getbbox() is None,"overlay outside active checkpoint")
    opaque=base.getchannel("A").point(lambda x:255 if x==255 else 0)
    check(ImageChops.multiply(a,ImageChops.invert(opaque)).getbbox() is None,"overlay changes alpha or hollow center")
    # HyperFrames emits a white opacity mask only. Use its verified alpha
    # and apply the exact approved palette after capture, avoiding browser
    # premultiplied RGB rounding in partially transparent mask pixels.
    bounds=a.getbbox()
    if bounds is None: return base.copy()
    cropped=overlay.crop(bounds)
    for red,green,blue,alpha in cropped.getdata():
        if alpha:
            check(max(red,green,blue)-min(red,green,blue)<=1,
                  f"unexpected colored mask pixel {red,green,blue,alpha}")
            check(alpha<255 or (red,green,blue)==(255,255,255),
                  f"non-white opaque mask pixel {red,green,blue,alpha}")
    colored=Image.new("RGBA",base.size,accent+(0,))
    colored.putalpha(a)
    result=Image.alpha_composite(base,colored)
    check(result.getchannel("A").tobytes()==base.getchannel("A").tobytes(),"composited alpha drift")
    return result
def verify_decoded(target,files):
    with Image.open(target) as im:
        check(im.size==(W,H) and im.info.get("loop")==0 and im.n_frames>1,"dimensions, loop or animation missing")
        elapsed=0
        source_i=0
        for i in range(im.n_frames):
            im.seek(i)
            decoded=canonical(im)
            duration=im.info.get("duration")
            check(isinstance(duration,int) and duration>0,"missing frame duration")
            end=elapsed+duration
            # Compare every overlap, not just samples at source-frame starts.
            while source_i<len(files) and boundary(source_i)<end:
                check(equal(decoded,load_rgba(files[source_i])),f"lossless/timing mismatch encoded {i}, source {source_i}")
                if boundary(source_i+1)>end: break
                source_i+=1
            elapsed=end
        check(elapsed==6000 and source_i==N,f"duration or coverage mismatch {elapsed}/{source_i}")
        return im.n_frames,elapsed
def verify(theme):
    refs=ordered_files(BUILD/(theme+"-reference")/"frames",24)
    base=load_rgba(refs[0])
    for p in refs:
        check(equal(base,load_rgba(p)),f"{theme}: static reference drift {p.name}")
    check(base.getchannel("A").getextrema()==(0,255),"missing true transparency")
    boxes=checkpoint_boxes()
    accent=(17,24,39) if theme=="light" else (135,155,196)
    # Render independent RGBA layers with HyperFrames, then assemble one
    # deterministic full-size RGBA sequence using an immutable static base.
    overlays=ordered_files(BUILD/theme/"frames",N)
    full=BUILD/theme/"composed"
    full.mkdir(exist_ok=True)
    files=[]
    peaks=set()
    for i,p in enumerate(overlays):
        overlay=load_rgba(p)
        active=active_checkpoint(i)
        try:
            frame=overlay_mask(base,overlay,None if active is None else boxes[active],accent)
        except ValueError as error:
            raise ValueError(f"{theme}: source frame {i} ({p.name}): {error}") from error
        if active is None: check(equal(base,frame),f"{theme}: rest state drift {i}")
        elif overlay.getchannel("A").getextrema()[1]==255: peaks.add(active)
        f=full/f"frame_{i:06d}.png"
        frame.save(f)
        files.append(f)
    check(peaks=={0,1,2},f"{theme}: missing full activation {peaks}")
    for j,t in enumerate((0.9,1.8,2.7)):
        frame=load_rgba(files[round(t*FPS)])
        check(not equal(base,frame),f"checkpoint {j+1} not activated")
    target=EXPORT/f"vib-sequential-{theme}.webp"
    cmd=["img2webp","-loop","0","-lossless"]
    for i,p in enumerate(files): cmd += ["-d",str(boundary(i+1)-boundary(i)),str(p)]
    subprocess.run(cmd+["-o",str(target)],check=True)
    count,elapsed=verify_decoded(target,files)
    base.save(EXPORT/f"vib-sequential-{theme}-static.png")
    meta=subprocess.check_output(["webpmux","-info",str(target)],text=True)
    (EXPORT/f"{theme}-webpmux.txt").write_text(meta)
    return {"theme":theme,"bytes":target.stat().st_size,"target_met":target.stat().st_size<=500000,"sha256":hashlib.sha256(target.read_bytes()).hexdigest(),"source_frames":N,"encoded_frames":count,"duration_ms":elapsed,"loop":0,"reference_sha256":hashlib.sha256(base.tobytes()).hexdigest()}
if __name__=="__main__":
    EXPORT.mkdir(exist_ok=True)
    result=[verify(t) for t in ("light","dark")]
    (EXPORT/"verification.json").write_text(json.dumps({"technical_checks":"passed","github_readme_playback":"pending","owner_acceptance":"pending","variants":result},indent=2)+"\n")
    shutil.copyfile(BUILD/"source-manifest.json",EXPORT/"source-manifest.json")
