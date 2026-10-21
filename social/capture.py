"""Captures of the live site (dossardpei.re) in a phone viewport, for the 'Sur le site' slides.
Every function returns (path, info) or (None, None) if the site changed and the capture failed."""
import asyncio, json, pathlib
from playwright.async_api import async_playwright

URL = 'https://dossardpei.re/'
VIEW = dict(viewport={'width': 390, 'height': 844}, device_scale_factor=3, is_mobile=True, has_touch=True, locale='fr-FR')


async def _ctx(p, height=844):
    b = await p.chromium.launch()
    ctx = await b.new_context(**{**VIEW, 'viewport': {'width': 390, 'height': height}})
    pg = await ctx.new_page()
    await pg.goto(URL, wait_until='networkidle')
    await pg.wait_for_timeout(1200)
    return b, pg


async def _view(pg, name):
    """Switch to Liste / Calendrier whatever the current mode (overlay or toolbar)."""
    loc = pg.locator(f'.reels button:has-text("{name}")')
    if await loc.count() and await loc.first.is_visible():
        await loc.first.click()
    else:
        await pg.locator(f'#v-{"liste" if name == "Liste" else "calendrier"}').click()
    await pg.wait_for_timeout(1200)


async def _rect(pg, js):
    return await pg.evaluate(js)


async def cal_month(out, ym):
    """Calendar view of month ym ('2026-11'). Returns crop box (css) of month card."""
    async with async_playwright() as p:
        b, pg = await _ctx(p, 1000)
        try:
            await _view(pg, 'Calendrier')
            for _ in range(14):
                cell = pg.locator(f'[data-cell^="{ym}-15"]')
                if await cell.count():
                    break
                await pg.click('#c-next'); await pg.wait_for_timeout(500)
            await pg.add_style_tag(content='#mapfab{display:none!important}')
            await pg.evaluate("()=>{const e=document.getElementById('c-prev');scrollTo(0,e.getBoundingClientRect().top+scrollY-110)}")
            await pg.wait_for_timeout(600)
            box = await pg.evaluate("""()=>{const g=document.querySelector('[data-cell]').parentElement.getBoundingClientRect();
               const t=document.getElementById('c-prev').getBoundingClientRect();return [Math.max(0,g.left-12),t.top-20,g.right+12,g.bottom+12]}""")
            await pg.screenshot(path=str(out))
            return out, box
        except Exception as e:
            print('capture cal_month:', e); return None, None
        finally:
            await b.close()


async def cal_weekend(out, day):
    """Calendar with day selected (YYYY-MM-DD) and its list. Returns boxes grid/list/cell."""
    async with async_playwright() as p:
        b, pg = await _ctx(p, 1000)
        try:
            await _view(pg, 'Calendrier')
            for _ in range(14):
                if await pg.locator(f'[data-cell="{day}"]').count():
                    break
                await pg.click('#c-next'); await pg.wait_for_timeout(500)
            await pg.locator(f'[data-cell="{day}"]').click(); await pg.wait_for_timeout(1000)
            await pg.add_style_tag(content='#mapfab{display:none!important}')
            await pg.evaluate("()=>{const e=document.getElementById('c-prev');scrollTo(0,e.getBoundingClientRect().top+scrollY-110)}")
            await pg.wait_for_timeout(600)
            info = await pg.evaluate("""(day)=>{const c=document.querySelector(`[data-cell="${day}"]`);const g=c.parentElement.getBoundingClientRect();
               const t=document.getElementById('c-prev').getBoundingClientRect();
               const hs=[...document.querySelectorAll('h2,h3,h4,div,strong,p')].filter(x=>x.children.length<3&&/^(lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche) \\d/.test(x.textContent.trim()));
               let L=null;if(hs.length){L=hs[0].parentElement.getBoundingClientRect()}
               const cr=c.getBoundingClientRect();
               return {grid:[Math.max(0,g.left-12),t.top-20,g.right+12,g.bottom+12],list:L?[L.left-8,L.top-8,L.right+8,Math.min(L.bottom+8,995)]:null,cell:[cr.left,cr.top,cr.width,cr.height]}}""", day)
            await pg.screenshot(path=str(out))
            return out, info
        except Exception as e:
            print('capture cal_weekend:', e); return None, None
        finally:
            await b.close()


async def filters(out, values):
    """Filters panel with some selects set, e.g. {'f-dist':'court'}. Returns box of the panel."""
    async with async_playwright() as p:
        b, pg = await _ctx(p, 844)
        try:
            await _view(pg, 'Liste')
            await pg.click('#f-toggle'); await pg.wait_for_timeout(900)
            for k, v in values.items():
                await pg.select_option(f'#{k}', v); await pg.wait_for_timeout(300)
            await pg.wait_for_timeout(700)
            box = await pg.evaluate("""()=>{const x=document.querySelector('[aria-label="Fermer les filtres"]');let p=x.parentElement;
                while(p&&p.getBoundingClientRect().height<300)p=p.parentElement;const r=p.getBoundingClientRect();return [r.left,r.top,r.right,Math.min(r.bottom,844)]}""")
            n = await pg.evaluate("()=>document.getElementById('fs-go')?.textContent.trim()")
            await pg.screenshot(path=str(out))
            return out, {'box': box, 'go': n}
        except Exception as e:
            print('capture filters:', e); return None, None
        finally:
            await b.close()


async def map_commune(out, commune):
    """Full-screen map (wide phone) with the commune popup open."""
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(**{**VIEW, 'viewport': {'width': 470, 'height': 700}})
        pg = await ctx.new_page()
        try:
            await pg.goto(URL, wait_until='networkidle'); await pg.wait_for_timeout(1200)
            await _view(pg, 'Liste')
            await pg.click('#mapfab'); await pg.wait_for_timeout(1800)
            await pg.click('#map-full'); await pg.wait_for_timeout(2200)
            await pg.screenshot(path=str(out).replace('.png', '_ile.png'))
            await pg.locator(f'g[aria-label^="{commune} :"]').first.click(); await pg.wait_for_timeout(2200)
            pop = await pg.evaluate("""()=>{const x=document.getElementById('mpop-x');let p=x.parentElement;while(p&&p.getBoundingClientRect().height<120)p=p.parentElement;const r=p.getBoundingClientRect();return [r.left,r.top,r.right,r.bottom]}""")
            await pg.screenshot(path=str(out))
            return out, {'pop': pop, 'ile': str(out).replace('.png', '_ile.png')}
        except Exception as e:
            print('capture map_commune:', e); return None, None
        finally:
            await b.close()


def run(coro):
    return asyncio.run(coro)
