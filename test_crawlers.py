"""
Test script for all crawlers.
Run this to verify crawling functionality.
"""

import asyncio
import sys

# Add src to path
sys.path.insert(0, '.')

from src.crawlers.base import ContentType

async def test_taobao():
    """Test Taobao crawler"""
    print("\n" + "="*60)
    print("🛒 Testing Taobao Crawler")
    print("="*60)
    
    from src.crawlers.taobao import TaobaoCrawler
    
    crawler = TaobaoCrawler()
    
    # Set up progress callback
    def on_progress(p):
        print(f"  [{p.percentage}%] {p.message}")
    
    def on_result(r):
        print(f"  ✓ Found: {r.store_name or r.title} - {r.url[:50]}...")
    
    crawler.set_progress_callback(on_progress)
    crawler.set_result_callback(on_result)
    
    print("Starting search for '手机壳' (phone case)...")
    print("NOTE: Browser will open. Set filters then add #go to URL or wait 60s")
    
    try:
        results = await crawler.search(
            keyword="手机壳",
            content_type=ContentType.STORE,
            max_results=5,  # Just test with 5
            headless=False
        )
        print(f"\n✅ Taobao test complete! Got {len(results)} results")
        for i, r in enumerate(results[:3]):
            print(f"  {i+1}. {r.store_name} - {r.url}")
        return True
    except Exception as e:
        print(f"❌ Taobao test failed: {e}")
        return False

async def test_jd():
    """Test JD crawler"""
    print("\n" + "="*60)
    print("🛍️ Testing JD Crawler")
    print("="*60)
    
    from src.crawlers.jd import JDCrawler
    
    crawler = JDCrawler()
    
    def on_progress(p):
        print(f"  [{p.percentage}%] {p.message}")
    
    def on_result(r):
        print(f"  ✓ Found: {r.store_name or r.title} - {r.url[:50]}...")
    
    crawler.set_progress_callback(on_progress)
    crawler.set_result_callback(on_result)
    
    print("Starting search for '耳机' (earphones)...")
    
    try:
        results = await crawler.search(
            keyword="耳机",
            content_type=ContentType.STORE,
            max_results=5,
            headless=False
        )
        print(f"\n✅ JD test complete! Got {len(results)} results")
        for i, r in enumerate(results[:3]):
            print(f"  {i+1}. {r.store_name} - {r.url}")
        return True
    except Exception as e:
        print(f"❌ JD test failed: {e}")
        return False

async def test_douyin_live():
    """Test Douyin live crawler"""
    print("\n" + "="*60)
    print("🎬 Testing Douyin Live Crawler")
    print("="*60)
    
    from src.crawlers.douyin import DouyinCrawler
    
    crawler = DouyinCrawler()
    
    def on_progress(p):
        print(f"  [{p.percentage}%] {p.message}")
    
    def on_result(r):
        print(f"  ✓ Found: {r.account_name or 'Unknown'} (ID: {r.account_id}) - {r.url[:40]}...")
    
    crawler.set_progress_callback(on_progress)
    crawler.set_result_callback(on_result)
    
    print("Starting search for '游戏' (games)...")
    
    try:
        results = await crawler.search(
            keyword="游戏",
            content_type=ContentType.LIVE,
            max_results=5,
            headless=False
        )
        print(f"\n✅ Douyin test complete! Got {len(results)} results")
        for i, r in enumerate(results[:3]):
            print(f"  {i+1}. {r.account_name} (ID: {r.account_id}) - {r.url}")
        return True
    except Exception as e:
        print(f"❌ Douyin test failed: {e}")
        return False

async def test_kuaishou_live():
    """Test Kuaishou live crawler"""
    print("\n" + "="*60)
    print("📹 Testing Kuaishou Live Crawler")
    print("="*60)
    
    from src.crawlers.kuaishou import KuaishouCrawler
    
    crawler = KuaishouCrawler()
    
    def on_progress(p):
        print(f"  [{p.percentage}%] {p.message}")
    
    def on_result(r):
        print(f"  ✓ Found: {r.account_name or 'Unknown'} (ID: {r.account_id}) - {r.url[:40]}...")
    
    crawler.set_progress_callback(on_progress)
    crawler.set_result_callback(on_result)
    
    print("Starting search for '美食' (food)...")
    
    try:
        results = await crawler.search(
            keyword="美食",
            content_type=ContentType.LIVE,
            max_results=5,
            headless=False
        )
        print(f"\n✅ Kuaishou test complete! Got {len(results)} results")
        for i, r in enumerate(results[:3]):
            print(f"  {i+1}. {r.account_name} (ID: {r.account_id}) - {r.url}")
        return True
    except Exception as e:
        print(f"❌ Kuaishou test failed: {e}")
        return False

async def main():
    print("\n" + "🔧 "*20)
    print("CRAWLER FUNCTIONALITY TEST")
    print("🔧 "*20)
    
    print("\nSelect test to run:")
    print("1. Taobao (淘宝)")
    print("2. JD (京东)")
    print("3. Douyin Live (抖音直播)")
    print("4. Kuaishou Live (快手直播)")
    print("5. All tests")
    print("0. Exit")
    
    choice = input("\nEnter choice (0-5): ").strip()
    
    if choice == '1':
        await test_taobao()
    elif choice == '2':
        await test_jd()
    elif choice == '3':
        await test_douyin_live()
    elif choice == '4':
        await test_kuaishou_live()
    elif choice == '5':
        await test_taobao()
        await test_jd()
        await test_douyin_live()
        await test_kuaishou_live()
    else:
        print("Exiting...")

if __name__ == "__main__":
    asyncio.run(main())
