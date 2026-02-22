#!/usr/bin/env python3
"""
Simple Douyin live test - non-interactive
"""

import asyncio
import sys
sys.path.insert(0, '.')

from src.crawlers.base import ContentType
from src.crawlers.douyin import DouyinCrawler


async def test():
    print("=" * 60)
    print("Testing Douyin Live Search (抖音直播)")
    print("=" * 60)
    print("Keyword: 游戏")
    print("Max results: 3")
    print("-" * 60)
    
    crawler = DouyinCrawler()
    
    def on_progress(p):
        print(f"[{p.percentage}%] {p.message}")
    
    def on_result(r):
        print(f"✓ Found: {r.account_name} | {r.url[:50]}...")
    
    crawler.set_progress_callback(on_progress)
    crawler.set_result_callback(on_result)
    
    results = await crawler.search(
        keyword='游戏',
        content_type=ContentType.LIVE,
        max_results=3,
        headless=False,
        browser_type="自动"
    )
    
    print(f"\n{'=' * 60}")
    print(f"RESULTS: {len(results)} live streams found")
    print("=" * 60)
    
    for i, r in enumerate(results, 1):
        print(f"\n[{i}] {r.account_name}")
        print(f"    ID: {r.account_id}")
        print(f"    Title: {r.title[:40]}..." if len(r.title) > 40 else f"    Title: {r.title}")
        print(f"    URL: {r.url}")
    
    print("\n✅ Test complete!")
    return len(results) > 0


if __name__ == "__main__":
    success = asyncio.run(test())
    sys.exit(0 if success else 1)
