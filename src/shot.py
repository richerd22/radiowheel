import asyncio, sys
from playwright.async_api import async_playwright
OUT="/tmp/claude-0/-home-claude/6aad4c76-dd60-593b-862f-e20aa51cf482/scratchpad/"
S=[("r1",1400,"light","/",0),("r2",1400,"dark","/",950),("r3",1400,"light","/stations/gta5-non-stop-pop-fm/",0),("r4",390,"dark","/",0),("r5",1400,"dark","/songs/",0),("r6",390,"light","/licensing/",0)]
if len(sys.argv)>1: S=[x for x in S if x[0] in sys.argv[1:]]
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch()
        for n,w,sc,path,y in S:
            pg=await b.new_page(viewport={"width":w,"height":950},color_scheme=sc); errs=[]
            pg.on("pageerror",lambda e: errs.append(str(e)))
            await pg.goto("http://127.0.0.1:8796"+path); await pg.wait_for_timeout(700)
            if n=="r2":
                await pg.hover(".wheel:not([hidden]) .wedge >> nth=3")
            if n=="r5":
                await pg.fill("#sf-q","hall"); await pg.wait_for_timeout(300)
            await pg.evaluate(f"window.scrollTo(0,{y})"); await pg.wait_for_timeout(250)
            await pg.screenshot(path=OUT+n+".png"); print(n,errs,await pg.evaluate("document.documentElement.scrollWidth"))
        await b.close()
asyncio.run(main())
