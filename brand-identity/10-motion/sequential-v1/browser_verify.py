"""Local browser playback qualification. Does not publish or retain images."""
from pathlib import Path
from io import BytesIO
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from threading import Thread
from time import monotonic
import json
from PIL import Image
from playwright.sync_api import sync_playwright

EXPORT=Path(__file__).resolve().parent/"build"/"exports"
W,H=960,720
RIMS=[(round((x+10)*W/1448),round((y+10)*H/1086)) for x,y in [(344,508),(700,428),(1104,508)]]
HOLES=[(round((x+52)*W/1448),round((y+52)*H/1086)) for x,y in [(344,508),(700,428),(1104,508)]]
THEMES={"light":((255,255,255),(17,24,39)),"dark":((13,17,23),(135,155,196))}
def require(value,message):
    if not value: raise ValueError(message)
def close(a,b,tol=3): return max(abs(x-y) for x,y in zip(a,b))<=tol
def run_theme(browser,engine,theme,origin):
    bg,accent=THEMES[theme]
    static=EXPORT/f"vib-sequential-{theme}-static.png"
    with Image.open(static) as im:
        require(all(im.getpixel(p)[3]==255 for p in RIMS),"reference rim sample not opaque")
        require(all(im.getpixel(p)[3]==0 for p in HOLES),"reference holes not transparent")
        rest=[im.getpixel(p)[:3] for p in RIMS]
    page=browser.new_page(viewport={"width":W,"height":H},device_scale_factor=1)
    try:
        page.goto(origin+"/preview-"+theme+".html")
        page.locator("#logo").evaluate("(e) => e.decode()")
        require(page.locator("#logo").evaluate("(e) => [e.naturalWidth,e.naturalHeight]")==[W,H],"image dimensions")
        seen=[]
        start=monotonic()
        while monotonic()-start<15:
            with Image.open(BytesIO(page.screenshot(type="png"))) as shot:
                im=shot.convert("RGB")
                require(all(close(im.getpixel(p),bg) for p in [(0,0),*HOLES]),f"{engine}/{theme} transparent region incorrect")
                values=[im.getpixel(p) for p in RIMS]
                active=[i for i,c in enumerate(values) if close(c,accent)]
                require(len(active)<=1,f"{engine}/{theme} concurrent active checkpoints")
                if active and (not seen or active[0]!=seen[-1]): seen.append(active[0])
                # Two complete cycles in actual displayed pixels, not just decode success.
                if any(seen[i:i+6]==[0,1,2,0,1,2] for i in range(len(seen)-5)): break
            page.wait_for_timeout(70)
        require(any(seen[i:i+6]==[0,1,2,0,1,2] for i in range(len(seen)-5)),f"{engine}/{theme}: looping sequence not observed: {seen}")
        # No custom player. Validate fallback independently by loading the static image.
        page.locator("#logo").evaluate("(e, src) => {e.src=src; return e.decode()}",static.name)
        with Image.open(BytesIO(page.screenshot(type="png"))) as shot:
            im=shot.convert("RGB")
            require(all(close(im.getpixel(p),c) for p,c in zip(RIMS,rest)),"static fallback mismatch")
        return {"engine":engine,"theme":theme,"observed_sequence":seen,"local_browser":"passed"}
    finally: page.close()
def main():
    for theme,(bg,_) in THEMES.items():
        (EXPORT/f"preview-{theme}.html").write_text(f'<!doctype html><meta charset="utf-8"><style>html,body{{margin:0;background:rgb{bg}}}img{{display:block;width:960px;height:720px}}</style><img id="logo" alt="VIB — Version-Issues-Hub" src="vib-sequential-{theme}.webp">',encoding="utf-8")
    server=ThreadingHTTPServer(("127.0.0.1",0),partial(SimpleHTTPRequestHandler,directory=str(EXPORT)))
    thread=Thread(target=server.serve_forever,daemon=True); thread.start()
    try:
        origin=f"http://127.0.0.1:{server.server_port}"
        results=[]
        with sync_playwright() as p:
            for engine in ("chromium","firefox","webkit"):
                with getattr(p,engine).launch(headless=True) as browser:
                    for theme in THEMES: results.append(run_theme(browser,engine,theme,origin))
        print(json.dumps({"local_browser_checks":results,"actual_github_readme":"pending","github_accessibility_preferences":"pending"},indent=2))
    finally:
        server.shutdown(); server.server_close()
if __name__=="__main__": main()
