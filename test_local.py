#!/usr/bin/env python3
"""
Local functional test script for Mac
Tests web crawlers (not emulator mode - that's Windows only)
"""

import asyncio
import sys
sys.path.insert(0, '.')

from src.crawlers.base import ContentType


def print_header(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_result(r, idx):
    print(f"\n--- Result {idx} ---")
    print(f"  Title: {r.title[:50]}..." if len(r.title) > 50 else f"  Title: {r.title}")
    print(f"  Account: {r.account_name} (ID: {r.account_id})")
    print(f"  URL: {r.url[:60]}..." if len(r.url) > 60 else f"  URL: {r.url}")


async def test_douyin_live():
    """Test Douyin live stream search"""
    print_header("Testing Douyin Live (抖音直播)")
    
    from src.crawlers.douyin import DouyinCrawler
    
    crawler = DouyinCrawler()
    
    def on_progress(p):
        print(f"[{p.percentage}%] {p.message}")
    
    crawler.set_progress_callback(on_progress)
    
    print("Keyword: 游戏")
    print("Browser: Chrome (auto)")
    print("Max results: 5")
    print("-" * 40)
    
    results = await crawler.search(
        keyword='游戏',
        content_type=ContentType.LIVE,
        max_results=5,
        headless=False,
        browser_type="自动"
    )
    
    print(f"\n✅ Got {len(results)} results")
    for i, r in enumerate(results[:3], 1):
        print_result(r, i)
    
    return len(results) > 0


async def test_kuaishou_live():
    """Test Kuaishou live stream search"""
    print_header("Testing Kuaishou Live (快手直播)")
    
    from src.crawlers.kuaishou import KuaishouCrawler
    
    crawler = KuaishouCrawler()
    
    def on_progress(p):
        print(f"[{p.percentage}%] {p.message}")
    
    crawler.set_progress_callback(on_progress)
    
    print("Keyword: 美食")
    print("Browser: Chrome (auto)")
    print("Max results: 5")
    print("-" * 40)
    
    results = await crawler.search(
        keyword='美食',
        content_type=ContentType.LIVE,
        max_results=5,
        headless=False,
        browser_type="自动"
    )
    
    print(f"\n✅ Got {len(results)} results")
    for i, r in enumerate(results[:3], 1):
        print_result(r, i)
    
    return len(results) > 0


async def test_taobao_stores():
    """Test Taobao store search"""
    print_header("Testing Taobao Stores (淘宝店铺)")
    
    from src.crawlers.taobao import TaobaoCrawler
    
    crawler = TaobaoCrawler()
    
    def on_progress(p):
        print(f"[{p.percentage}%] {p.message}")
    
    crawler.set_progress_callback(on_progress)
    
    print("Keyword: 手机壳")
    print("Browser: Chrome (auto)")
    print("Max results: 10")
    print("-" * 40)
    print("NOTE: May require login - complete in browser if prompted")
    print("-" * 40)
    
    results = await crawler.search(
        keyword='手机壳',
        content_type=ContentType.STORE,
        max_results=10,
        headless=False,
        browser_type="自动"
    )
    
    print(f"\n✅ Got {len(results)} results")
    for i, r in enumerate(results[:5], 1):
        print(f"\n--- Store {i} ---")
        print(f"  Name: {r.store_name}")
        print(f"  URL: {r.url}")
    
    return len(results) > 0


async def test_jd_stores():
    """Test JD store search"""
    print_header("Testing JD Stores (京东店铺)")
    
    from src.crawlers.jd import JDCrawler
    
    crawler = JDCrawler()
    
    def on_progress(p):
        print(f"[{p.percentage}%] {p.message}")
    
    crawler.set_progress_callback(on_progress)
    
    print("Keyword: 笔记本电脑")
    print("Browser: Chrome (auto)")
    print("Max results: 10")
    print("-" * 40)
    
    results = await crawler.search(
        keyword='笔记本电脑',
        content_type=ContentType.STORE,
        max_results=10,
        headless=False,
        browser_type="自动"
    )
    
    print(f"\n✅ Got {len(results)} results")
    for i, r in enumerate(results[:5], 1):
        print(f"\n--- Store {i} ---")
        print(f"  Name: {r.store_name}")
        print(f"  URL: {r.url}")
    
    return len(results) > 0


def show_menu():
    print("\n" + "=" * 60)
    print("  Crawler Functional Test Menu")
    print("=" * 60)
    print("  1. Test Douyin Live (抖音直播)")
    print("  2. Test Kuaishou Live (快手直播)")
    print("  3. Test Taobao Stores (淘宝店铺)")
    print("  4. Test JD Stores (京东店铺)")
    print("  5. Run ALL tests")
    print("  0. Exit")
    print("-" * 60)
    return input("Select option: ").strip()


async def main():
    print("\n🧪 Crawler Functional Test Suite")
    print("   (Tests web crawlers on Mac - emulator mode is Windows only)")
    
    while True:
        choice = show_menu()
        
        if choice == "0":
            print("\nGoodbye! 👋")
            break
        elif choice == "1":
            await test_douyin_live()
        elif choice == "2":
            await test_kuaishou_live()
        elif choice == "3":
            await test_taobao_stores()
        elif choice == "4":
            await test_jd_stores()
        elif choice == "5":
            print("\n🚀 Running ALL tests...")
            results = {
                "Douyin Live": await test_douyin_live(),
                "Kuaishou Live": await test_kuaishou_live(),
                "Taobao Stores": await test_taobao_stores(),
                "JD Stores": await test_jd_stores(),
            }
            
            print_header("Test Results Summary")
            for name, passed in results.items():
                status = "✅ PASSED" if passed else "❌ FAILED"
                print(f"  {name}: {status}")
        else:
            print("Invalid option, try again.")
        
        input("\nPress Enter to continue...")


if __name__ == "__main__":
    asyncio.run(main())
