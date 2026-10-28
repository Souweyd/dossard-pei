"""Record an HTML page whose CSS animations form a timeline into an mp4 (deterministic, frame by frame)."""
import asyncio, subprocess, pathlib
from playwright.async_api import async_playwright

SEEK = """(t)=>{document.getAnimations().forEach(a=>{a.pause();a.currentTime=t*1000})}"""


async def _rec(html_path, out_mp4, dur, fps=30, w=1080, h=1920, stills=()):
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width': w, 'height': h})
        await pg.goto(pathlib.Path(html_path).as_uri())
        await pg.evaluate('document.fonts.ready')
        await pg.evaluate("Promise.all([...document.images].map(i=>i.complete?1:new Promise(r=>{i.onload=i.onerror=r})))")
        await pg.wait_for_timeout(300)
        for t, path in stills:
            await pg.evaluate(SEEK, t); await pg.screenshot(path=str(path), type='jpeg', quality=92)
        ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', str(fps), '-i', '-',
                               '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '19', '-preset', 'medium', '-movflags', '+faststart', str(out_mp4)],
                              stdin=subprocess.PIPE)
        for i in range(int(dur * fps)):
            await pg.evaluate(SEEK, i / fps)
            ff.stdin.write(await pg.screenshot(type='jpeg', quality=90))
        ff.stdin.close(); ff.wait(); await b.close()


def record(html_path, out_mp4, dur, **kw):
    asyncio.run(_rec(html_path, out_mp4, dur, **kw))
