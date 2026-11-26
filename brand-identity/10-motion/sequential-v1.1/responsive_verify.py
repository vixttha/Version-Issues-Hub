"""Measure real decoded frames at representative display sizes; no retained images."""
from PIL import Image, ImageChops
from pathlib import Path
import json
from geometry import PEAKS, checkpoint_boxes, W,H
EXPORT=Path(__file__).resolve().parent/"build"/"exports"
def sample(im,ms):
    elapsed=0
    for i in range(im.n_frames):
        im.seek(i); frame=im.convert("RGBA")
        elapsed+=im.info["duration"]
        if elapsed>ms:return frame
    raise ValueError("missing peak")
def main():
    results=[]
    for theme,bg in (("light",(255,255,255)),("dark",(13,17,23)),("dimmed",(34,39,46))):
        filetheme="dark" if theme=="dimmed" else theme
        with Image.open(EXPORT/f"vib-sequential-v1.1-{filetheme}.webp") as im:
            base=sample(im,0)
            peaks=[sample(im,round(t*1000)) for t in PEAKS]
        for width in (200,320,480,960):
            size=(width,width*3//4)
            def flatten(frame):
                return Image.alpha_composite(Image.new("RGBA",size,bg+(255,)),frame.resize(size,Image.Resampling.LANCZOS)).convert("RGB")
            rest=flatten(base)
            changes=[]
            for i,peak in enumerate(peaks):
                delta=ImageChops.difference(rest,flatten(peak))
                count=sum(1 for pixel in delta.getdata() if max(pixel)>=24)
                if count<8: raise ValueError(f"{theme}/{width}: checkpoint {i} lacks visible pixel change")
                changes.append(count)
            results.append({"theme":theme,"display_width":width,"changed_pixels_per_checkpoint":changes,"human_slogan_readability":"pending visual review"})
    print(json.dumps(results,indent=2))
if __name__=="__main__":main()
