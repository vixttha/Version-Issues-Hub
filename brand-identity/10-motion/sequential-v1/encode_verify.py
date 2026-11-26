from pathlib import Path
import hashlib, json, subprocess, shutil
from PIL import Image, ImageChops

HERE=Path(__file__).resolve().parent
BUILD=HERE/"build"
EXPORT=BUILD/"exports"
EXPORT.mkdir(exist_ok=True)
W,H,N,FPS=960,720,144,24
def check(ok,msg):
    if not ok: raise ValueError(msg)
def boundary(i): return (i*1000+FPS//2)//FPS
def canonical(im):
    im=im.convert("RGBA")
    # RGB under alpha=0 is not visible and may legally be discarded.
    im.paste((0,0,0,0),mask=im.getchannel("A").point(lambda x:255 if x==0 else 0))
    return im
def equal(a,b): return all(x.getbbox() is None for x in ImageChops.difference(a,b).split())
def verify(theme):
    files=sorted((BUILD/theme/"frames").glob("frame_*.png"))
    check(len(files)==N,f"{theme}: expected 144 source frames, got {len(files)}")
    frames=[]
    for p in files:
        with Image.open(p) as im:
            check(im.size==(W,H) and "A" in im.getbands(),f"not RGBA: {p}")
            frames.append(canonical(im))
    base=frames[0]
    alpha=base.getchannel("A")
    check(alpha.getextrema()==(0,255),"missing true transparency")
    check(all(equal(base,frames[i]) for i in [0,1,83,100,143]),"rest state drift")
    boxes=[(344,508,448,612),(700,428,804,532),(1104,508,1208,612)]
    boxes=[(int(x*W/1448)-2,int(y*H/1086)-2,int(X*W/1448)+3,int(Y*H/1086)+3) for x,y,X,Y in boxes]
    from PIL import ImageDraw
    mask=Image.new("L",(W,H),0)
    for box in boxes: ImageDraw.Draw(mask).rectangle(box,fill=255)
    # Every source frame retains all alpha and non-checkpoint pixels.
    for i,frame in enumerate(frames):
        check(ImageChops.difference(alpha,frame.getchannel("A")).getbbox() is None, f"alpha drift frame {i}")
        diff=ImageChops.difference(base,frame)
        for band in diff.split():
            check(ImageChops.multiply(band,ImageChops.invert(mask)).getbbox() is None,f"outside checkpoint region {i}")
    for i,t in enumerate([0.9,1.8,2.7]):
        frame=frames[round(t*FPS)]
        check(not equal(base,frame),f"checkpoint {i+1} not activated")
        for j,box in enumerate(boxes):
            check(equal(base.crop(box),frame.crop(box)) == (j!=i),f"incorrect checkpoint sequence {i+1}")
    target=EXPORT/f"vib-sequential-{theme}.webp"
    cmd=["img2webp","-loop","0","-lossless"]
    for i,p in enumerate(files): cmd += ["-d",str(boundary(i+1)-boundary(i)),str(p)]
    subprocess.run(cmd+["-o",str(target)],check=True)
    with Image.open(target) as im:
        check(im.info.get("loop")==0 and im.n_frames>1,"loop or animation missing")
        decoded=[]
        elapsed=0
        for i in range(im.n_frames):
            im.seek(i)
            frame=canonical(im)
            duration=im.info.get("duration")
            check(isinstance(duration,int) and duration>0,"missing frame duration")
            decoded.append((elapsed,elapsed+duration,frame))
            elapsed+=duration
        check(elapsed==6000,f"duration mismatch {elapsed}")
        for i,frame in enumerate(frames):
            t=boundary(i)
            matching=next((f for s,e,f in decoded if s<=t<e),None)
            check(matching is not None and equal(frame,matching),f"lossless mismatch at {i}")
    base.save(EXPORT/f"vib-sequential-{theme}-static.png")
    meta=subprocess.check_output(["webpmux","-info",str(target)],text=True)
    (EXPORT/f"{theme}-webpmux.txt").write_text(meta)
    return {"theme":theme,"bytes":target.stat().st_size,"target_met":target.stat().st_size<=500000,"sha256":hashlib.sha256(target.read_bytes()).hexdigest(),"source_frames":N,"encoded_frames":len(decoded),"duration_ms":elapsed,"loop":0}
if __name__=="__main__":
    result=[verify(t) for t in ("light","dark")]
    (EXPORT/"verification.json").write_text(json.dumps({"technical_checks":"passed","github_readme_playback":"pending","owner_acceptance":"pending","variants":result},indent=2)+"\n")
    shutil.copyfile(BUILD/"source-manifest.json",EXPORT/"source-manifest.json")
