"""Shared experimental geometry and timing; original source is never modified."""
from math import floor, ceil
W,H,N,FPS=960,720,144,24
CROP=(94,70.5,1260,945)
VIEWBOX="94 70.5 1260 945"
RINGS=((344,508),(700,428),(1104,508))
STARTS=(0.4,1.45,2.5)
PEAKS=(0.9,1.95,3.0)
def xy(x,y):
    return (round((x-CROP[0])*W/CROP[2]),round((y-CROP[1])*H/CROP[3]))
def checkpoint_boxes():
    return [(floor((x-CROP[0])*W/CROP[2])-2,floor((y-CROP[1])*H/CROP[3])-2,
             ceil((x+104-CROP[0])*W/CROP[2])+2,ceil((y+104-CROP[1])*H/CROP[3])+2) for x,y in RINGS]
def active_checkpoint(i):
    return next((j for j,s in enumerate((8,29,50)) if s*FPS<i*20<(s+21)*FPS),None)
def crop_svg(svg):
    source='viewBox="0 0 1448 1086"'
    if svg.count(source)!=1: raise ValueError("unexpected source viewBox")
    return svg.replace(source,f'viewBox="{VIEWBOX}"',1)
