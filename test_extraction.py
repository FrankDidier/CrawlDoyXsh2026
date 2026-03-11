"""
Functional test: Verify JS extraction patterns work against realistic page HTML.
Creates mock HTML pages simulating each platform's search results, loads them in 
a real browser, and verifies the extraction JS returns correct data.
"""
import asyncio
import sys
import os
import tempfile
import traceback

sys.path.insert(0, os.path.dirname(__file__))

passed = 0
failed = 0

def check(desc, cond):
    global passed, failed
    if cond:
        print(f"  ✓ {desc}")
        passed += 1
    else:
        print(f"  ✗ FAIL: {desc}")
        failed += 1


# =============================================================
# Mock HTML pages that simulate real platform search results
# =============================================================

TAOBAO_MOCK_HTML = """<!DOCTYPE html>
<html><head><title>连衣裙 - 淘宝搜索</title></head><body>
<div id="search-results">
  <!-- Item 1: store.taobao.com link -->
  <div class="Card--doubleCard">
    <a href="//store.taobao.com/shop/view_shop.htm?appUid=abc123&spm=a1z10">梦幻时尚旗舰店</a>
    <a href="//item.taobao.com/item.htm?id=111">碎花连衣裙2024新款</a>
    <span class="price">¥128.00</span>
  </div>
  <!-- Item 2: shopXXX.taobao.com pattern -->
  <div class="Card--doubleCard">
    <a href="//shop12345.taobao.com/">韩都衣舍旗舰店</a>
    <a href="//item.taobao.com/item.htm?id=222">夏季雪纺连衣裙</a>
    <span class="price">¥89.00</span>
  </div>
  <!-- Item 3: tmall.com store -->
  <div class="Card--doubleCard">
    <a href="//uniqlo.tmall.com/">优衣库官方旗舰店</a>
    <a href="//detail.tmall.com/item.htm?id=333">UNIQLO 连衣裙</a>
  </div>
  <!-- Item 4: Another store.taobao format -->
  <div class="Card--doubleCard">
    <a href="//store.taobao.com/shop/view_shop.htm?appUid=def456">春风女装专卖店</a>
    <a href="//item.taobao.com/item.htm?id=444">显瘦A字连衣裙</a>
  </div>
  <!-- Item 5: view_shop format -->
  <div class="content--content">
    <a href="//store.taobao.com/shop/view_shop.htm?appUid=ghi789">花间集旗舰店</a>
    <a href="//item.taobao.com/item.htm?id=555">法式复古连衣裙</a>
  </div>
  <!-- Item 6: shop URL pattern -->
  <div class="Card--doubleCard">
    <a href="//shop67890.taobao.com/search.htm">优雅女装店</a>
    <a href="//item.taobao.com/item.htm?id=666">气质名媛连衣裙</a>
  </div>
  <!-- Item 7: tmall store pattern -->
  <div class="Card--doubleCard">
    <a href="//hm.tmall.com/shop/view.htm">HM官方旗舰店</a>
    <a href="//detail.tmall.com/item.htm?id=777">H&M 波点连衣裙</a>
  </div>
  <!-- Noise: should NOT be extracted as stores -->
  <a href="//detail.tmall.com/item.htm?id=999">This is a product, not store</a>
  <a href="//login.taobao.com/member/login.jhtml">登录</a>
  <a href="//www.tmall.com/">天猫首页</a>
  <a href="//pages.tmall.com/wow/z/tmall/discovery">天猫发现</a>
</div>
</body></html>"""

JD_MOCK_HTML = """<!DOCTYPE html>
<html><head><title>手机 - 京东搜索</title></head><body>
<div id="J_goodsList">
  <ul class="gl-warp">
    <li class="gl-item" data-sku="100001">
      <div class="gl-i-wrap">
        <div class="p-name"><em><a href="//item.jd.com/100001.html">Apple iPhone 15 Pro Max 256GB</a></em></div>
        <div class="p-price"><i>8999.00</i></div>
        <div class="p-shop"><a href="//mall.jd.com/index-1000000.html" class="curr-shop">Apple产品京东自营旗舰店</a></div>
      </div>
    </li>
    <li class="gl-item" data-sku="100002">
      <div class="gl-i-wrap">
        <div class="p-name"><em><a href="//item.jd.com/100002.html">华为 Mate 60 Pro 512GB</a></em></div>
        <div class="p-price"><i>6999.00</i></div>
        <div class="p-shop"><a href="//mall.jd.com/index-1000001.html" class="curr-shop">华为京东自营旗舰店</a></div>
      </div>
    </li>
    <li class="gl-item" data-sku="100003">
      <div class="gl-i-wrap">
        <div class="p-name"><em><a href="//item.jd.com/100003.html">小米14 Ultra 骁龙8Gen3</a></em></div>
        <div class="p-price"><i>5999.00</i></div>
        <div class="p-shop"><a href="//shop.jd.com/shop-100123.html" class="curr-shop">小米京东自营旗舰店</a></div>
      </div>
    </li>
    <li class="gl-item" data-sku="100004">
      <div class="gl-i-wrap">
        <div class="p-name"><em><a href="//item.jd.com/100004.html">OPPO Find X7 Ultra</a></em></div>
        <div class="p-price"><i>5499.00</i></div>
        <div class="p-shop"><a href="//mall.jd.com/index-1000003.html" class="hd-shopname">OPPO京东自营旗舰店</a></div>
      </div>
    </li>
    <li class="gl-item" data-sku="100005">
      <div class="gl-i-wrap">
        <div class="p-name"><em><a href="//item.jd.com/100005.html">vivo X100 Pro 天玑9300</a></em></div>
        <div class="p-price"><i>4999.00</i></div>
        <div class="p-shop"><a href="//mall.jd.com/index-1000004.html" class="curr-shop">vivo京东自营旗舰店</a></div>
      </div>
    </li>
  </ul>
</div>
<!-- Pagination -->
<div class="p-wrap">
  <span class="p-num"><a class="curr">1</a><a href="?page=2">2</a><a href="?page=3">3</a></span>
  <a class="pn-next" href="?page=2">下一页<em>&gt;</em></a>
</div>
</body></html>"""

DOUYIN_MOCK_HTML = """<!DOCTYPE html>
<html><head><title>美食 - 抖音搜索</title></head><body>
<div id="search-content-area">
  <!-- Live streams -->
  <div class="Card--live">
    <a href="https://live.douyin.com/123456789">
      <div class="title">美食直播间</div>
    </a>
    <div class="author">@美食大王</div>
    <span class="count">1.2万人正在看</span>
  </div>
  <div class="Card--live">
    <a href="https://live.douyin.com/987654321">
      <div class="title">深夜食堂直播</div>
    </a>
    <div class="author">@厨神小陈</div>
  </div>
  <div class="Card--live">
    <a href="/live/555666777">
      <div class="title">吃播挑战</div>
    </a>
    <div class="nickname">@大胃王</div>
  </div>
  <!-- Videos -->
  <div data-e2e="search-video-card">
    <a href="/video/7300000000000000001"><span class="title">超简单的家常菜教程</span></a>
    <span class="author">@小美厨房</span>
  </div>
  <div data-e2e="search-video-card">
    <a href="//www.douyin.com/video/7300000000000000002"><span>街头美食探店vlog</span></a>
    <span class="name">@探店达人</span>
  </div>
  <div class="item">
    <a href="/video/7300000000000000003">烘焙入门教程</a>
    <div class="nickname">@烘焙小白</div>
  </div>
</div>
</body></html>"""

KUAISHOU_MOCK_HTML = """<!DOCTYPE html>
<html><head><title>美食 - 快手搜索</title></head><body>
<div id="search-results">
  <!-- Live users -->
  <div class="card">
    <a href="/u/user001"><span class="author">美食博主小李</span></a>
    <span>正在直播</span>
  </div>
  <div class="card">
    <a href="https://live.kuaishou.com/u/user002"><span class="nickname">厨艺大师</span></a>
  </div>
  <div class="Card">
    <a href="/profile/user003"><span class="name">街头小吃达人</span></a>
  </div>
  <!-- Videos -->
  <div class="feed-item">
    <a href="/short-video/vid001"><span>自制火锅底料教程</span></a>
    <span class="author">@美食制作人</span>
  </div>
  <div class="card">
    <a href="/photo/vid002"><span>炸鸡配方大公开</span></a>
    <span class="nickname">@炸鸡大王</span>
  </div>
  <div class="item">
    <a href="/video/vid003"><span>减脂餐一周食谱</span></a>
    <span>@健康饮食</span>
  </div>
</div>
</body></html>"""


async def run_tests():
    from playwright.async_api import async_playwright
    from src.utils.browser_helper import create_browser_context
    
    pw = await async_playwright().start()
    context, page, browser = await create_browser_context(pw, headless=True, browser_type="自动")
    
    # =========================================================
    # TEST 1: Taobao Store Extraction
    # =========================================================
    print("\n" + "="*60)
    print("  TEST 1: Taobao Store Extraction (mock page)")
    print("="*60)
    
    with tempfile.NamedTemporaryFile(suffix='.html', mode='w', delete=False, encoding='utf-8') as f:
        f.write(TAOBAO_MOCK_HTML)
        taobao_path = f.name
    
    await page.goto(f'file://{taobao_path}')
    await asyncio.sleep(1)
    
    # Run our EXACT store extraction JS from taobao.py
    store_data = await page.evaluate('''() => {
        const results = [];
        const seen = new Set();
        const allLinks = document.querySelectorAll('a');
        for (const link of allLinks) {
            const href = link.getAttribute('href') || '';
            if (!href) continue;
            let isStore = false;
            if (href.includes('store.taobao.com')) isStore = true;
            else if (/shop\\d+\\.taobao\\.com/.test(href)) isStore = true;
            else if (/\\/\\/[a-z][a-z0-9-]+\\.tmall\\.com/.test(href) &&
                     !href.includes('detail.tmall') && !href.includes('login') &&
                     !href.includes('pages.tmall') && !href.includes('www.tmall')) isStore = true;
            else if (href.includes('view_shop') || href.includes('appUid=')) isStore = true;
            else if (href.includes('shop.m.taobao.com')) isStore = true;
            if (!isStore) continue;
            if (href.includes('item.htm') || href.includes('detail.tmall') || 
                href.includes('item.taobao') || href.includes('ishop.taobao') ||
                href.includes('zhaoshang.tmall') || href.includes('login') ||
                href.includes('member') || href.includes('cart') ||
                href.includes('favorite') || href.includes('rate')) continue;
            const cleanHref = href.split('&spm')[0].split('&scm')[0];
            if (seen.has(cleanHref)) continue;
            seen.add(cleanHref);
            let storeName = link.innerText.trim();
            if (!storeName || storeName.length < 2) {
                const parent = link.parentElement;
                if (parent) {
                    const nameEl = parent.querySelector('[class*="shopname"], [class*="shop-name"], [class*="store"]');
                    if (nameEl) storeName = nameEl.innerText.trim();
                    if (!storeName || storeName.length < 2) {
                        storeName = parent.innerText.split('\\n')[0].trim();
                    }
                }
            }
            results.push({ href: href, cleanHref: cleanHref, storeName: storeName || '' });
        }
        return results;
    }''')
    
    print(f"  Stores extracted: {len(store_data)}")
    for s in store_data:
        print(f"    {s['storeName'][:30]} -> {s['href'][:60]}")
    
    check("Extracted 7 stores (not noise)", len(store_data) == 7)
    
    store_names = [s['storeName'] for s in store_data]
    check("Found 梦幻时尚旗舰店 (store.taobao.com)", "梦幻时尚旗舰店" in store_names)
    check("Found 韩都衣舍旗舰店 (shopXXX.taobao.com)", "韩都衣舍旗舰店" in store_names)
    check("Found 优衣库官方旗舰店 (xxx.tmall.com)", "优衣库官方旗舰店" in store_names)
    check("Found 花间集旗舰店 (view_shop)", "花间集旗舰店" in store_names)
    check("Found HM官方旗舰店 (tmall)", "HM官方旗舰店" in store_names)
    
    # Verify noise was filtered out
    store_hrefs_flat = ' '.join(s['href'] for s in store_data)
    check("Filtered out detail.tmall (product link)", "detail.tmall" not in store_hrefs_flat)
    check("Filtered out login.taobao", "login.taobao" not in store_hrefs_flat)
    check("Filtered out www.tmall (homepage)", "www.tmall.com" not in store_hrefs_flat)
    check("Filtered out pages.tmall", "pages.tmall" not in store_hrefs_flat)
    
    # Test product extraction too
    product_data = await page.evaluate('''() => {
        const results = [];
        const seen = new Set();
        const links = document.querySelectorAll('a[href*="item.taobao"], a[href*="detail.tmall"], a[href*="item.htm"]');
        for (const link of links) {
            const href = link.getAttribute('href') || '';
            if (!href) continue;
            if (!href.includes('item.taobao') && !href.includes('detail.tmall') && !href.includes('item.htm')) continue;
            const ch = href.split('&spm')[0];
            if (seen.has(ch)) continue;
            seen.add(ch);
            const title = link.innerText.trim();
            if (title && title.length > 2)
                results.push({ href: href, title: title });
        }
        return results;
    }''')
    print(f"\n  Products extracted: {len(product_data)}")
    for p in product_data:
        print(f"    {p['title'][:40]} -> {p['href'][:50]}")
    check("Extracted product links", len(product_data) >= 5)
    
    # Test URL normalization with real extracted URLs
    from src.crawlers.taobao import TaobaoCrawler
    tc = TaobaoCrawler()
    print("\n  URL normalization test:")
    for s in store_data:
        norm = tc._normalize_store_url(s['href'])
        print(f"    {s['href'][:50]} -> {norm}")
    check("URL normalization produces results", all(tc._normalize_store_url(s['href']) for s in store_data))
    
    os.unlink(taobao_path)
    
    # =========================================================
    # TEST 2: JD Store & Product Extraction
    # =========================================================
    print("\n" + "="*60)
    print("  TEST 2: JD Store & Product Extraction (mock page)")
    print("="*60)
    
    with tempfile.NamedTemporaryFile(suffix='.html', mode='w', delete=False, encoding='utf-8') as f:
        f.write(JD_MOCK_HTML)
        jd_path = f.name
    
    await page.goto(f'file://{jd_path}')
    await asyncio.sleep(1)
    
    # Run our EXACT JD product extraction JS
    product_data = await page.evaluate('''() => {
        const results = [];
        const seen = new Set();
        const items = document.querySelectorAll('li.gl-item, .gl-i-wrap, div[data-sku], [class*="gl-item"]');
        for (const item of items) {
            const productLink = item.querySelector('a[href*="item.jd.com"]');
            if (!productLink) continue;
            let productUrl = productLink.getAttribute('href') || '';
            if (productUrl.startsWith('//')) productUrl = 'https:' + productUrl;
            const cleanUrl = productUrl.split('?')[0];
            if (seen.has(cleanUrl)) continue;
            seen.add(cleanUrl);
            let title = '';
            const titleEl = item.querySelector('.p-name em, .p-name a, [class*="title"] em');
            if (titleEl) title = titleEl.innerText.trim();
            let storeName = '';
            const storeEl = item.querySelector('a.curr-shop, a.hd-shopname, [class*="shop"] a, .p-shop a');
            if (storeEl) storeName = storeEl.innerText.trim();
            let price = '';
            const priceEl = item.querySelector('.p-price i, [class*="price"] i');
            if (priceEl) price = priceEl.innerText.trim();
            results.push({ url: productUrl, title: title, storeName: storeName, price: price });
        }
        return results;
    }''')
    
    print(f"  Products extracted: {len(product_data)}")
    for p in product_data:
        print(f"    {p['title'][:35]} | ¥{p['price']} | {p['storeName'][:20]} | {p['url'][:40]}")
    
    check("Extracted 5 JD products", len(product_data) == 5)
    check("Products have titles", all(p['title'] for p in product_data))
    check("Products have prices", all(p['price'] for p in product_data))
    check("Products have store names", all(p['storeName'] for p in product_data))
    check("Products have URLs", all('item.jd.com' in p['url'] for p in product_data))
    check("First product is iPhone", 'iPhone' in product_data[0]['title'])
    check("Price format correct", product_data[0]['price'] == '8999.00')
    
    # Test JD store extraction
    store_data = await page.evaluate('''() => {
        const results = [];
        const seen = new Set();
        const items = document.querySelectorAll('li.gl-item, .gl-i-wrap, div[data-sku], [class*="gl-item"]');
        for (const item of items) {
            const storeLink = item.querySelector(
                'a.curr-shop, a.hd-shopname, a[href*="mall.jd.com"], a[href*="shop.jd.com"], ' +
                '[class*="shop"] a, [class*="store"] a, .p-shop a, .shop-name a'
            );
            if (!storeLink) continue;
            let storeName = storeLink.innerText.trim();
            let storeUrl = storeLink.getAttribute('href') || '';
            if (!storeName || storeName.length < 2 || seen.has(storeName)) continue;
            seen.add(storeName);
            if (storeUrl.startsWith('//')) storeUrl = 'https:' + storeUrl;
            results.push({ name: storeName, url: storeUrl });
        }
        return results;
    }''')
    
    print(f"\n  Unique stores extracted: {len(store_data)}")
    for s in store_data:
        print(f"    {s['name'][:30]} -> {s['url'][:50]}")
    
    check("Extracted JD stores (unique)", len(store_data) >= 4)
    store_names = [s['name'] for s in store_data]
    check("Found Apple store", any('Apple' in n for n in store_names))
    check("Found 华为 store", any('华为' in n for n in store_names))
    check("Found OPPO store (hd-shopname selector)", any('OPPO' in n for n in store_names))
    check("Store URLs are https", all(s['url'].startswith('https://') for s in store_data))
    
    os.unlink(jd_path)
    
    # =========================================================
    # TEST 3: Douyin Live & Video Extraction
    # =========================================================
    print("\n" + "="*60)
    print("  TEST 3: Douyin Live & Video Extraction (mock page)")
    print("="*60)
    
    with tempfile.NamedTemporaryFile(suffix='.html', mode='w', delete=False, encoding='utf-8') as f:
        f.write(DOUYIN_MOCK_HTML)
        dy_path = f.name
    
    await page.goto(f'file://{dy_path}')
    await asyncio.sleep(1)
    
    # Test live stream extraction JS
    live_data = await page.evaluate('''() => {
        const results = [];
        const seen = new Set();
        const links = document.querySelectorAll('a');
        for (const link of links) {
            const href = link.getAttribute('href') || '';
            let isLive = false;
            if (/live\\.douyin\\.com\\/\\d+/.test(href)) isLive = true;
            else if (/\\/live\\/\\d+/.test(href)) isLive = true;
            else if (href.includes('webcast') && /\\d{10,}/.test(href)) isLive = true;
            if (isLive) {
                const ch = href.split('?')[0];
                if (seen.has(ch)) continue;
                seen.add(ch);
                let parent = link.closest('[class*="Card"]') || link.closest('[class*="card"]') ||
                             link.closest('[class*="item"]') || link.closest('li') ||
                             link.parentElement?.parentElement?.parentElement;
                let parentText = '';
                try { parentText = parent ? parent.innerText : ''; } catch(e) {}
                results.push({ href: href, parentText: parentText });
            }
        }
        return results;
    }''')
    
    print(f"  Live streams extracted: {len(live_data)}")
    for l in live_data:
        print(f"    {l['href'][:60]} | text: {l['parentText'][:40]}")
    
    check("Extracted 3 Douyin live streams", len(live_data) == 3)
    check("Found live.douyin.com pattern", any('live.douyin.com' in l['href'] for l in live_data))
    check("Found /live/ pattern", any('/live/' in l['href'] for l in live_data))
    check("Parent text has author info", any('美食' in l['parentText'] or '厨神' in l['parentText'] for l in live_data))
    
    # Test video extraction JS
    video_data = await page.evaluate('''() => {
        const results = [];
        const seen = new Set();
        const links = document.querySelectorAll('a[href*="/video/"]');
        for (const link of links) {
            const href = link.getAttribute('href') || '';
            const match = href.match(/\\/video\\/(\\d+)/);
            if (!match) continue;
            const videoId = match[1];
            if (seen.has(videoId)) continue;
            seen.add(videoId);
            let parent = link.closest('[data-e2e]') || link.closest('[class*="Card"]') ||
                         link.closest('[class*="card"]') || link.closest('[class*="item"]') ||
                         link.closest('li') || link.parentElement?.parentElement?.parentElement;
            let parentText = '';
            try { parentText = parent ? parent.innerText : link.innerText; } catch(e) {}
            let fullHref = href;
            if (href.startsWith('//')) fullHref = 'https:' + href;
            else if (href.startsWith('/')) fullHref = 'https://www.douyin.com' + href;
            results.push({ href: fullHref, videoId: videoId, parentText: parentText });
        }
        return results;
    }''')
    
    print(f"\n  Videos extracted: {len(video_data)}")
    for v in video_data:
        print(f"    id={v['videoId'][:15]} | {v['href'][:50]} | {v['parentText'][:30]}")
    
    check("Extracted 3 Douyin videos", len(video_data) == 3)
    check("Video IDs extracted", all(v['videoId'] for v in video_data))
    check("URLs built correctly", all(v['href'].startswith('https://') for v in video_data))
    check("Parent text has content", any('家常菜' in v['parentText'] or '探店' in v['parentText'] or '烘焙' in v['parentText'] for v in video_data))
    
    os.unlink(dy_path)
    
    # =========================================================
    # TEST 4: Kuaishou Live & Video Extraction
    # =========================================================
    print("\n" + "="*60)
    print("  TEST 4: Kuaishou Live & Video Extraction (mock page)")
    print("="*60)
    
    with tempfile.NamedTemporaryFile(suffix='.html', mode='w', delete=False, encoding='utf-8') as f:
        f.write(KUAISHOU_MOCK_HTML)
        ks_path = f.name
    
    await page.goto(f'file://{ks_path}')
    await asyncio.sleep(1)
    
    # Test live/user extraction
    live_data = await page.evaluate('''() => {
        const results = [];
        const seen = new Set();
        const links = document.querySelectorAll('a');
        for (const link of links) {
            const href = link.getAttribute('href') || '';
            let isLive = false;
            if (/\\/u\\/[^\\/?]+/.test(href)) isLive = true;
            else if (href.includes('live.kuaishou')) isLive = true;
            else if (/\\/live\\/[^\\/?]+/.test(href)) isLive = true;
            else if (/\\/profile\\/[^\\/?]+/.test(href)) isLive = true;
            if (isLive) {
                let ch = href.split('?')[0];
                if (ch.startsWith('/')) ch = 'https://live.kuaishou.com' + ch;
                else if (ch.startsWith('//')) ch = 'https:' + ch;
                if (seen.has(ch)) continue;
                seen.add(ch);
                let parent = link.closest('[class*="card"]') || link.closest('[class*="Card"]') ||
                             link.closest('[class*="item"]') || link.closest('li') ||
                             link.parentElement?.parentElement?.parentElement;
                let parentText = '';
                try { parentText = parent ? parent.innerText : link.innerText; } catch(e) {}
                results.push({ href: ch, parentText: parentText });
            }
        }
        return results;
    }''')
    
    print(f"  Live/user links extracted: {len(live_data)}")
    for l in live_data:
        print(f"    {l['href'][:60]} | {l['parentText'][:30]}")
    
    check("Extracted 3 Kuaishou live links", len(live_data) == 3)
    check("Found /u/ pattern", any('/u/' in l['href'] for l in live_data))
    check("Found live.kuaishou pattern", any('live.kuaishou' in l['href'] for l in live_data))
    check("Found /profile/ pattern", any('/profile/' in l['href'] for l in live_data))
    
    # Test video extraction
    video_data = await page.evaluate('''() => {
        const results = [];
        const seen = new Set();
        const links = document.querySelectorAll('a[href*="/short-video/"], a[href*="/photo/"], a[href*="/video/"]');
        for (const link of links) {
            const href = link.getAttribute('href') || '';
            const match = href.match(/\\/(?:short-video|photo|video)\\/([^\\/?]+)/);
            if (!match) continue;
            const videoId = match[1];
            if (seen.has(videoId)) continue;
            seen.add(videoId);
            let parent = link.closest('[class*="card"]') || link.closest('[class*="Card"]') ||
                         link.closest('[class*="item"]') || link.closest('[class*="feed"]') ||
                         link.closest('li') || link.parentElement?.parentElement?.parentElement;
            let parentText = '';
            try { parentText = parent ? parent.innerText : link.innerText; } catch(e) {}
            let fullHref = href;
            if (href.startsWith('/')) fullHref = 'https://www.kuaishou.com' + href;
            results.push({ href: fullHref, videoId: videoId, parentText: parentText });
        }
        return results;
    }''')
    
    print(f"\n  Videos extracted: {len(video_data)}")
    for v in video_data:
        print(f"    id={v['videoId'][:15]} | {v['href'][:50]} | {v['parentText'][:30]}")
    
    check("Extracted 3 Kuaishou videos", len(video_data) == 3)
    check("Found /short-video/ pattern", any('/short-video/' in v['href'] for v in video_data))
    check("Found /photo/ pattern", any('/photo/' in v['href'] for v in video_data))
    check("Found /video/ pattern", any('/video/' in v['href'] for v in video_data))
    check("Video IDs correct", set(v['videoId'] for v in video_data) == {'vid001', 'vid002', 'vid003'})
    
    os.unlink(ks_path)
    
    # Cleanup
    await context.close()
    if browser:
        await browser.close()
    await pw.stop()
    
    # =========================================================
    # SUMMARY
    # =========================================================
    print(f"\n{'='*60}")
    print(f"  EXTRACTION FUNCTIONAL TEST SUMMARY")
    print(f"{'='*60}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print(f"  Total:  {passed + failed}")
    print(f"{'='*60}")
    
    if failed > 0:
        print(f"\n  ⚠️  {failed} test(s) FAILED!")
        sys.exit(1)
    else:
        print(f"\n  ✅ ALL {passed} EXTRACTION TESTS PASSED!")


asyncio.run(run_tests())
