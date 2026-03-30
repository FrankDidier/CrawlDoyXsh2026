"""
Live network smoke test — hits real sites with the same browser stack as the app.
Does NOT log in. Measures: block indicators, link counts usable by our extractors.

Usage:
  python test_live_platforms.py              # headless (CI / quick)
  LIVE_TEST_HEADED=1 python test_live_platforms.py   # visible Chrome (recommended once locally)

Exit code 0 always; writes live_report.json for CI artifacts. Human reads stdout.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from urllib.parse import quote

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)


async def probe_page(page, name: str, keyword: str) -> dict:
    snippet = await page.evaluate(
        """() => {
        const html = document.documentElement.innerHTML || '';
        return {
            title: document.title || '',
            href: location.href,
            aCount: document.querySelectorAll('a[href]').length,
            bodyLen: (document.body && document.body.innerHTML) ? document.body.innerHTML.length : 0,
            blocked: html.includes('rgv587') || html.includes('punish/deny') || html.includes('deny_h5'),
            jdLogin: location.href.includes('passport.jd.com'),
            jdItemLinks: document.querySelectorAll('a[href*="item.jd"]').length,
            hasItemTaobao: html.includes('item.taobao') || html.includes('detail.tmall'),
            hasStoreTaobao: html.includes('store.taobao') || html.includes('shop') && html.includes('taobao'),
            douyinVideoHref: Array.from(document.querySelectorAll('a[href*="/video/"]')).length,
            douyinLiveHint: Array.from(document.querySelectorAll('a[href]')).filter(a => {
              const h = a.getAttribute('href')||'';
              return /live\\.douyin\\.com\\/\\d+|\\/live\\/\\d+/.test(h);
            }).length,
            kuaishouVideo: Array.from(document.querySelectorAll('a[href]')).filter(a => {
              const h = a.getAttribute('href')||'';
              return /\\/(short-video|photo|video)\\//.test(h) || /\\/fw\\/photo\\//.test(h);
            }).length,
            htmlHasKsFeed: html.includes('short-video') || html.includes('/photo/') || html.includes('video'),
            kuaishouLive: Array.from(document.querySelectorAll('a[href]')).filter(a => {
              const h = a.getAttribute('href')||'';
              return /\\/u\\/[^\\/]+/.test(h) || /live\\.kuaishou/.test(h);
            }).length,
        };
    }"""
    )
    score = 0
    status = "weak"
    if name == "taobao_product":
        if snippet["blocked"]:
            status = "blocked"
        elif snippet["hasItemTaobao"] and snippet["aCount"] > 30:
            status, score = "ok", 2
        elif snippet["aCount"] > 80:
            status, score = "maybe", 1
    elif name == "taobao_shop":
        if snippet["blocked"]:
            status = "blocked"
        elif (snippet["hasStoreTaobao"] or snippet["hasItemTaobao"]) and snippet["aCount"] > 30:
            status, score = "ok", 2
        elif snippet["aCount"] > 50:
            status, score = "maybe", 1
    elif name == "jd":
        if snippet["jdLogin"]:
            status = "login"
        elif snippet.get("jdItemLinks", 0) >= 8:
            status, score = "ok", 2
        elif snippet.get("jdItemLinks", 0) >= 1:
            status, score = "maybe", 1
    elif name == "douyin_live":
        if snippet["douyinLiveHint"] >= 1:
            status, score = "ok", 2
        elif snippet["douyinVideoHref"] >= 3:
            status, score = "maybe", 1
    elif name == "douyin_video":
        if snippet["douyinVideoHref"] >= 3:
            status, score = "ok", 2
        elif snippet["aCount"] > 50:
            status, score = "maybe", 1
    elif name == "kuaishou_live":
        if snippet["kuaishouLive"] >= 2:
            status, score = "ok", 2
        elif snippet["aCount"] > 40:
            status, score = "maybe", 1
    elif name == "kuaishou_video":
        if snippet["kuaishouVideo"] >= 2:
            status, score = "ok", 2
        elif snippet.get("htmlHasKsFeed") and snippet["aCount"] >= 5:
            status, score = "maybe", 1
        elif snippet["aCount"] > 40:
            status, score = "maybe", 1

    snippet["status"] = status
    snippet["score"] = score
    snippet["platform_case"] = name
    snippet["keyword"] = keyword
    return snippet


async def run():
    from playwright.async_api import async_playwright
    from src.utils.browser_helper import create_browser_context

    headed = os.environ.get("LIVE_TEST_HEADED", "").strip() in ("1", "true", "yes")
    headless = not headed
    keyword = os.environ.get("LIVE_TEST_KEYWORD", "手机")
    kw_dy_ks = os.environ.get("LIVE_TEST_KEYWORD_SHORT", "美食")

    rows = []
    start = datetime.now(timezone.utc).isoformat()

    pw = await async_playwright().start()
    try:
        context, page, browser = await create_browser_context(
            pw, headless=headless, browser_type="自动"
        )

        # 淘宝：与爬虫一致先开首页再进搜索（直连搜索易被 rgv587）
        async def open_taobao_then(url: str):
            await page.goto("https://www.taobao.com", wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(3)
            await page.mouse.move(400, 400)
            await asyncio.sleep(0.5)
            await page.goto(url, wait_until="domcontentloaded", timeout=90000)
            await asyncio.sleep(5)

        async def open_jd_then(url: str):
            await page.goto("https://www.jd.com", wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(3)
            await page.mouse.move(300, 300)
            await asyncio.sleep(0.5)
            await page.goto(url, wait_until="domcontentloaded", timeout=90000)
            await asyncio.sleep(5)

        scenarios = [
            ("taobao_product", f"https://s.taobao.com/search?q={quote(keyword)}&s=0", open_taobao_then),
            ("taobao_shop", f"https://s.taobao.com/search?q={quote(keyword)}&tab=shop&s=0", open_taobao_then),
            ("jd", f"https://search.jd.com/Search?keyword={quote(keyword)}", open_jd_then),
            ("douyin_live", f"https://www.douyin.com/search/{quote(kw_dy_ks)}?type=live", None),
            ("douyin_video", f"https://www.douyin.com/search/{quote(kw_dy_ks)}?type=video", None),
            ("kuaishou_live", f"https://www.kuaishou.com/search/live?searchKey={quote(kw_dy_ks)}", None),
            ("kuaishou_video", f"https://www.kuaishou.com/search/video?searchKey={quote(kw_dy_ks)}", None),
        ]

        for entry in scenarios:
            name, url = entry[0], entry[1]
            pre_nav = entry[2] if len(entry) > 2 else None
            print(f"\n>>> {name}: {url[:90]}...")
            try:
                if pre_nav:
                    await pre_nav(url)
                else:
                    await page.goto(url, wait_until="domcontentloaded", timeout=90000)
                    await asyncio.sleep(5)
                row = await probe_page(page, name, kw_dy_ks if "douyin" in name or "kuaishou" in name else keyword)
                rows.append(row)
                print(
                    f"    status={row['status']} score={row['score']} a={row['aCount']} "
                    f"blocked={row['blocked']} title={row['title'][:40]!r}"
                )
            except Exception as e:
                rows.append(
                    {
                        "platform_case": name,
                        "status": "error",
                        "error": str(e)[:200],
                        "score": 0,
                    }
                )
                print(f"    ERROR: {e}")

        await context.close()
        if browser:
            await browser.close()
    finally:
        await pw.stop()

    okish = sum(1 for r in rows if r.get("score", 0) >= 2)
    maybe = sum(1 for r in rows if r.get("status") == "maybe")
    report = {
        "started_at": start,
        "headless": headless,
        "headed_note": "Set LIVE_TEST_HEADED=1 for a closer-to-GUI run (often fewer blocks).",
        "cases_ok_score2": okish,
        "cases_maybe": maybe,
        "rows": rows,
    }
    out_path = os.path.join(ROOT, "live_report.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n{'='*60}")
    print(f"Wrote {out_path}")
    print(f"Strong signals (score>=2): {okish} / {len(rows)}")
    print("Login or WAF without credentials is expected in headless — use LIVE_TEST_HEADED=1 locally.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(run())
