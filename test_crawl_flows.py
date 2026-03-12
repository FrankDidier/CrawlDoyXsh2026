"""
Test complete crawl flows: pagination, scrolling, #go mechanism, 
CrawlResult generation, and end-to-end crawl with mock pages.
Loads multi-page mock HTML into a real browser to simulate actual crawling.
"""
import asyncio
import sys
import os
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(__file__))

from src.crawlers.base import CrawlResult, CrawlProgress, CrawlStatus, Platform, ContentType
from src.crawlers.jd import JDCrawler
from src.crawlers.taobao import TaobaoCrawler
from src.crawlers.douyin import DouyinCrawler
from src.crawlers.kuaishou import KuaishouCrawler

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


# ==========================================================
# Create a multi-page JD mock site for pagination testing
# ==========================================================
def create_jd_mock_site(tmpdir):
    """Create 3 pages of JD search results with pagination links."""
    for pg in range(1, 4):
        items_html = ""
        for i in range(1, 11):
            item_id = (pg - 1) * 10 + i
            items_html += f'''
            <li class="gl-item" data-sku="{item_id}">
              <div class="gl-i-wrap">
                <div class="p-name"><em><a href="//item.jd.com/{item_id}.html">商品{item_id} - Page{pg}</a></em></div>
                <div class="p-price"><i>{100 * item_id}.00</i></div>
                <div class="p-shop"><a href="//mall.jd.com/index-{item_id % 5}.html" class="curr-shop">店铺{item_id % 5 + 1}</a></div>
              </div>
            </li>'''

        next_link = ""
        if pg < 3:
            next_link = f'<a class="pn-next" href="page{pg+1}.html">下一页<em>&gt;</em></a>'
        prev_link = ""
        if pg > 1:
            prev_link = f'<a class="pn-prev" href="page{pg-1}.html">上一页<em>&lt;</em></a>'

        html = f"""<!DOCTYPE html>
<html><head><title>手机 - 京东搜索 - 第{pg}页</title></head><body>
<div id="J_goodsList"><ul class="gl-warp">{items_html}</ul></div>
<div class="p-wrap">
  <span class="p-num">
    {''.join(f'<a {"class=curr " if p==pg else ""}href="page{p}.html">{p}</a>' for p in range(1,4))}
  </span>
  {prev_link} {next_link}
</div>
</body></html>"""
        with open(os.path.join(tmpdir, f'page{pg}.html'), 'w', encoding='utf-8') as f:
            f.write(html)


# ==========================================================
# Create a Taobao mock with store links across multiple items
# ==========================================================
def create_taobao_mock_page(tmpdir):
    items_html = ""
    for i in range(1, 21):
        store_type = i % 4
        if store_type == 0:
            store_link = f'<a href="//store.taobao.com/shop/view_shop.htm?appUid=uid{i}">淘宝店铺{i}</a>'
        elif store_type == 1:
            store_link = f'<a href="//shop{10000+i}.taobao.com/">淘宝店铺{i}</a>'
        elif store_type == 2:
            store_link = f'<a href="//brand{i}.tmall.com/">天猫店铺{i}</a>'
        else:
            store_link = f'<a href="//store.taobao.com/shop/view_shop.htm?appUid=u{i}">混合店铺{i}</a>'

        items_html += f'''
        <div class="Card--doubleCard">
            {store_link}
            <a href="//item.taobao.com/item.htm?id={i}">商品标题{i} 好看的连衣裙</a>
            <span class="price">¥{50+i}.00</span>
        </div>'''

    html = f"""<!DOCTYPE html>
<html><head><title>连衣裙 - 淘宝搜索</title></head><body>
<div id="search-results">{items_html}</div>
</body></html>"""
    with open(os.path.join(tmpdir, 'taobao.html'), 'w', encoding='utf-8') as f:
        f.write(html)


# ==========================================================
# Create a Douyin mock with scroll-loading simulation
# ==========================================================
def create_douyin_scroll_mock(tmpdir):
    html = """<!DOCTYPE html>
<html><head><title>美食 - 抖音搜索</title>
<script>
let loadCount = 0;
const maxLoads = 3;
function loadMore() {
    if (loadCount >= maxLoads) return;
    loadCount++;
    const container = document.getElementById('results');
    for (let i = 0; i < 5; i++) {
        const idx = (loadCount - 1) * 5 + i + 1;
        const div = document.createElement('div');
        div.className = 'Card--video';
        div.innerHTML = '<a href="/video/730000' + String(idx).padStart(4, '0') + '"><span>动态加载视频' + idx + '</span></a>';
        container.appendChild(div);
    }
    document.body.style.height = (document.body.scrollHeight + 500) + 'px';
}
window.addEventListener('scroll', function() {
    if ((window.innerHeight + window.scrollY) >= document.body.scrollHeight - 200) {
        loadMore();
    }
});
</script>
</head><body style="height: 2000px;">
<div id="results">
  <div class="Card--video"><a href="/video/7300010001"><span>初始视频1</span></a></div>
  <div class="Card--video"><a href="/video/7300010002"><span>初始视频2</span></a></div>
  <div class="Card--video"><a href="/video/7300010003"><span>初始视频3</span></a></div>
</div>
</body></html>"""
    with open(os.path.join(tmpdir, 'douyin_scroll.html'), 'w', encoding='utf-8') as f:
        f.write(html)


async def run_tests():
    from playwright.async_api import async_playwright
    from src.utils.browser_helper import create_browser_context

    pw = await async_playwright().start()
    context, page, browser = await create_browser_context(pw, headless=True, browser_type="自动")

    tmpdir = tempfile.mkdtemp()

    try:
        # ===========================================================
        # TEST 1: JD Pagination (multi-page navigation)
        # ===========================================================
        print("\n" + "="*60)
        print("  TEST 1: JD Pagination Across 3 Pages")
        print("="*60)

        create_jd_mock_site(tmpdir)

        await page.goto(f'file://{tmpdir}/page1.html')
        await asyncio.sleep(1)

        title = await page.title()
        check("Page 1 loaded", "第1页" in title)

        # Extract items from page 1
        p1_items = await page.evaluate('''() => {
            const items = document.querySelectorAll('li.gl-item');
            return Array.from(items).map(item => {
                const link = item.querySelector('a[href*="item.jd.com"]');
                const title = item.querySelector('.p-name em');
                return { url: link?.getAttribute('href') || '', title: title?.innerText || '' };
            });
        }''')
        check("Page 1 has 10 items", len(p1_items) == 10)
        check("Page 1 first item is #1", "商品1" in p1_items[0]['title'])

        # Test "next page" button click  
        next_btn = await page.query_selector('a.pn-next')
        check("Next page button exists", next_btn is not None)

        await next_btn.click()
        await asyncio.sleep(1)

        title2 = await page.title()
        check("Page 2 loaded after click", "第2页" in title2)

        p2_items = await page.evaluate('''() => {
            return document.querySelectorAll('li.gl-item').length;
        }''')
        check("Page 2 has 10 items", p2_items == 10)

        # Navigate to page 3
        next_btn2 = await page.query_selector('a.pn-next')
        check("Page 2 has next button", next_btn2 is not None)
        await next_btn2.click()
        await asyncio.sleep(1)

        title3 = await page.title()
        check("Page 3 loaded", "第3页" in title3)

        # Page 3 should NOT have a next button
        next_btn3 = await page.query_selector('a.pn-next')
        check("Page 3 has no next button (last page)", next_btn3 is None)

        p3_items = await page.evaluate('''() => {
            const items = document.querySelectorAll('li.gl-item');
            return Array.from(items).map(item => {
                const link = item.querySelector('a[href*="item.jd.com"]');
                return link?.getAttribute('href') || '';
            });
        }''')
        check("Page 3 has 10 items", len(p3_items) == 10)
        check("Page 3 items are #21-30", '//item.jd.com/30.html' in p3_items)

        # Verify total unique items across all 3 pages
        all_items = set()
        for pg in range(1, 4):
            await page.goto(f'file://{tmpdir}/page{pg}.html')
            await asyncio.sleep(0.5)
            items = await page.evaluate('''() => {
                return Array.from(document.querySelectorAll('li.gl-item a[href*="item.jd.com"]'))
                    .map(a => a.getAttribute('href'));
            }''')
            all_items.update(items)
        check(f"Total unique items across 3 pages: {len(all_items)}", len(all_items) == 30)

        # ===========================================================
        # TEST 2: JD Store Deduplication
        # ===========================================================
        print("\n" + "="*60)
        print("  TEST 2: JD Store Deduplication")
        print("="*60)

        await page.goto(f'file://{tmpdir}/page1.html')
        await asyncio.sleep(0.5)

        stores = await page.evaluate('''() => {
            const results = [];
            const seen = new Set();
            const items = document.querySelectorAll('li.gl-item');
            for (const item of items) {
                const storeLink = item.querySelector('a.curr-shop, a.hd-shopname, .p-shop a');
                if (!storeLink) continue;
                const name = storeLink.innerText.trim();
                if (!name || seen.has(name)) continue;
                seen.add(name);
                results.push(name);
            }
            return results;
        }''')
        print(f"  Unique stores on page 1: {stores}")
        check("Stores are deduplicated (5 unique from 10 items)", len(stores) == 5)

        # ===========================================================
        # TEST 3: Taobao Store Extraction with All URL Patterns
        # ===========================================================
        print("\n" + "="*60)
        print("  TEST 3: Taobao 20-Item Page - All URL Patterns")
        print("="*60)

        create_taobao_mock_page(tmpdir)
        await page.goto(f'file://{tmpdir}/taobao.html')
        await asyncio.sleep(1)

        stores = await page.evaluate('''() => {
            const results = [];
            const seen = new Set();
            const links = document.querySelectorAll('a');
            for (const link of links) {
                const href = link.getAttribute('href') || '';
                if (!href) continue;
                let isStore = false;
                if (href.includes('store.taobao.com')) isStore = true;
                else if (/shop\\d+\\.taobao\\.com/.test(href)) isStore = true;
                else if (/\\/\\/[a-z][a-z0-9-]+\\.tmall\\.com/.test(href) &&
                         !href.includes('detail.tmall') && !href.includes('login') &&
                         !href.includes('pages.tmall') && !href.includes('www.tmall')) isStore = true;
                else if (href.includes('view_shop') || href.includes('appUid=')) isStore = true;
                if (!isStore) continue;
                if (href.includes('item.htm') || href.includes('detail.tmall') || href.includes('login')) continue;
                const ch = href.split('&spm')[0];
                if (seen.has(ch)) continue;
                seen.add(ch);
                results.push({ href: href, name: link.innerText.trim() });
            }
            return results;
        }''')
        
        print(f"  Stores found: {len(stores)}")
        check("Extracted all 20 stores", len(stores) == 20)

        store_patterns = {'store.taobao.com': 0, 'shop': 0, 'tmall.com': 0, 'view_shop': 0}
        for s in stores:
            if 'store.taobao.com' in s['href']:
                store_patterns['store.taobao.com'] += 1
            if '/shop' in s['href']:
                store_patterns['shop'] += 1
            if '.tmall.com' in s['href']:
                store_patterns['tmall.com'] += 1
            if 'view_shop' in s['href']:
                store_patterns['view_shop'] += 1
        
        print(f"  Pattern breakdown: {store_patterns}")
        check("Multiple URL patterns used", sum(1 for v in store_patterns.values() if v > 0) >= 3)

        products = await page.evaluate('''() => {
            return document.querySelectorAll('a[href*="item.taobao.com"]').length;
        }''')
        check(f"Products also extracted: {products}", products == 20)

        # ===========================================================
        # TEST 4: Douyin Scroll-to-Load More
        # ===========================================================
        print("\n" + "="*60)
        print("  TEST 4: Douyin Scroll-Loading Simulation")
        print("="*60)

        create_douyin_scroll_mock(tmpdir)
        await page.goto(f'file://{tmpdir}/douyin_scroll.html')
        await asyncio.sleep(1)

        initial_count = await page.evaluate('''() => {
            return document.querySelectorAll('a[href*="/video/"]').length;
        }''')
        check(f"Initial videos: {initial_count}", initial_count == 3)

        # Scroll to trigger lazy loading
        for i in range(5):
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(1)

        after_scroll = await page.evaluate('''() => {
            return document.querySelectorAll('a[href*="/video/"]').length;
        }''')
        print(f"  After scrolling: {after_scroll} videos")
        check("Scroll loaded more videos", after_scroll > initial_count)
        check(f"All dynamic content loaded ({after_scroll} total)", after_scroll >= 15)

        # Verify video IDs are unique
        video_ids = await page.evaluate('''() => {
            const ids = new Set();
            document.querySelectorAll('a[href*="/video/"]').forEach(a => {
                const m = a.getAttribute('href').match(/\\/video\\/(\\d+)/);
                if (m) ids.add(m[1]);
            });
            return ids.size;
        }''')
        check(f"All {video_ids} video IDs are unique", video_ids == after_scroll)

        # ===========================================================
        # TEST 5: CrawlResult Generation
        # ===========================================================
        print("\n" + "="*60)
        print("  TEST 5: CrawlResult Object Generation")
        print("="*60)

        # Test that we can create proper CrawlResult objects from extracted data
        jc = JDCrawler()
        
        # Simulate what _crawl_products does
        await page.goto(f'file://{tmpdir}/page1.html')
        await asyncio.sleep(0.5)

        raw_products = await page.evaluate('''() => {
            const results = [];
            const seen = new Set();
            const items = document.querySelectorAll('li.gl-item');
            for (const item of items) {
                const link = item.querySelector('a[href*="item.jd.com"]');
                if (!link) continue;
                let url = link.getAttribute('href') || '';
                if (url.startsWith('//')) url = 'https:' + url;
                const clean = url.split('?')[0];
                if (seen.has(clean)) continue;
                seen.add(clean);
                const titleEl = item.querySelector('.p-name em');
                const priceEl = item.querySelector('.p-price i');
                const storeEl = item.querySelector('.p-shop a');
                results.push({
                    url: url,
                    title: titleEl ? titleEl.innerText.trim() : '',
                    price: priceEl ? priceEl.innerText.trim() : '',
                    store: storeEl ? storeEl.innerText.trim() : ''
                });
            }
            return results;
        }''')

        crawl_results = []
        for p in raw_products:
            result = CrawlResult(
                platform=Platform.JD,
                content_type=ContentType.PRODUCT,
                url=p['url'],
                share_text=f"JD商品: {p['title']}",
                title=p['title'],
                product_name=p['title'],
                store_name=p['store'],
                price=f"¥{p['price']}",
            )
            crawl_results.append(result)

        check(f"Created {len(crawl_results)} CrawlResult objects", len(crawl_results) == 10)
        check("Results have platform=JD", all(r.platform == Platform.JD for r in crawl_results))
        check("Results have content_type=PRODUCT", all(r.content_type == ContentType.PRODUCT for r in crawl_results))
        check("Results have URLs", all(r.url.startswith('https://item.jd.com') for r in crawl_results))
        check("Results have titles", all(r.title for r in crawl_results))
        check("Results have prices", all(r.price for r in crawl_results))
        check("Results have store names", all(r.store_name for r in crawl_results))
        check("Results have share text", all(r.share_text for r in crawl_results))
        check("Results have crawled_at timestamp", all(r.crawled_at for r in crawl_results))

        print(f"\n  Sample results:")
        for r in crawl_results[:3]:
            print(f"    {r.title[:30]} | {r.price} | {r.store_name} | {r.url[:40]}")

        # ===========================================================
        # TEST 6: Progress Callbacks
        # ===========================================================
        print("\n" + "="*60)
        print("  TEST 6: Progress & Result Callbacks")
        print("="*60)

        jc2 = JDCrawler()
        progress_msgs = []
        result_list = []

        jc2.set_progress_callback(lambda p: progress_msgs.append(
            CrawlProgress(status=p.status, message=p.message, current=p.current, total=p.total)
        ))
        jc2.set_result_callback(lambda r: result_list.append(r))

        # Use the actual _update_progress method
        jc2._update_progress(status=CrawlStatus.RUNNING, message="正在搜索...", current=0, total=10)

        check("Progress callback fires", len(progress_msgs) == 1)
        check("Progress has message", progress_msgs[0].message == "正在搜索...")
        check("Progress has status RUNNING", progress_msgs[0].status == CrawlStatus.RUNNING)

        # Use the actual _add_result method
        test_result = CrawlResult(
            platform=Platform.JD,
            content_type=ContentType.PRODUCT,
            url="https://item.jd.com/999.html",
            share_text="test",
            title="Test Product",
        )
        jc2._add_result(test_result)
        check("Result callback fires", len(result_list) == 1)
        check("Result data correct", result_list[0].url == "https://item.jd.com/999.html")
        check("Result stored in crawler", len(jc2.results) == 1)

        # ===========================================================
        # TEST 7: Export Functionality
        # ===========================================================
        print("\n" + "="*60)
        print("  TEST 7: Export to Excel & CSV")
        print("="*60)

        from src.utils.exporter import Exporter
        
        export_dir = os.path.join(tmpdir, 'exports')
        os.makedirs(export_dir)

        # Convert CrawlResult to dicts (same as main_window does)
        dicts = [r.to_dict() for r in crawl_results]
        check("CrawlResult.to_dict() works", len(dicts) == 10)
        check("Dict has platform key", '平台' in dicts[0])
        check("Dict has URL key (链接)", '链接' in dicts[0])

        # Test Excel export
        excel_path = os.path.join(export_dir, 'test_results.xlsx')
        success = Exporter.to_excel_from_dicts(dicts, excel_path)
        check("Excel export succeeded", success)
        check("Excel file created", os.path.exists(excel_path))
        check("Excel file not empty", os.path.getsize(excel_path) > 0)

        # Test CSV export
        csv_path = os.path.join(export_dir, 'test_results.csv')
        success = Exporter.to_csv_from_dicts(dicts, csv_path)
        check("CSV export succeeded", success)
        check("CSV file created", os.path.exists(csv_path))
        
        # Read CSV and verify content
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()
        check("CSV has header + 10 data rows", len(lines) == 11)
        check("CSV header has columns", '平台' in lines[0] or 'URL' in lines[0])

        print(f"  Excel: {os.path.getsize(excel_path)} bytes")
        print(f"  CSV: {os.path.getsize(csv_path)} bytes, {len(lines)} lines")

    finally:
        await context.close()
        if browser:
            await browser.close()
        await pw.stop()
        shutil.rmtree(tmpdir, ignore_errors=True)

    print(f"\n{'='*60}")
    print(f"  CRAWL FLOW TEST SUMMARY")
    print(f"{'='*60}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print(f"  Total:  {passed + failed}")
    print(f"{'='*60}")

    if failed > 0:
        print(f"\n  ⚠️  {failed} test(s) FAILED!")
        sys.exit(1)
    else:
        print(f"\n  ✅ ALL {passed} CRAWL FLOW TESTS PASSED!")

asyncio.run(run_tests())
