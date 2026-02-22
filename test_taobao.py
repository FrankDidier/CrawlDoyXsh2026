#!/usr/bin/env python3
"""
Test Taobao store crawler with improved extraction
"""

import asyncio
import sys
sys.path.insert(0, '.')

from src.crawlers.base import ContentType
from src.crawlers.taobao import TaobaoCrawler


async def test():
    print("=" * 60)
    print("Testing Taobao Store Crawler (淘宝店铺)")
    print("=" * 60)
    print("Keyword: 手机壳")
    print("Max results: 50 (should get most of one page)")
    print("-" * 60)
    print("NOTE: Login may be required - complete in browser")
    print("-" * 60)
    
    crawler = TaobaoCrawler()
    
    def on_progress(p):
        print(f"[{p.percentage}%] {p.message}")
    
    def on_result(r):
        # Shorten URL for display
        url_short = r.url[:50] + "..." if len(r.url) > 50 else r.url
        print(f"✓ {r.store_name} => {url_short}")
    
    crawler.set_progress_callback(on_progress)
    crawler.set_result_callback(on_result)
    
    results = await crawler.search(
        keyword='手机壳',
        content_type=ContentType.STORE,
        max_results=50,
        headless=False,
        browser_type="自动"
    )
    
    print(f"\n{'=' * 60}")
    print(f"RESULTS: {len(results)} stores found")
    print("=" * 60)
    
    # Show URL format distribution
    taobao_urls = [r for r in results if 'shop' in r.url and '.taobao.com' in r.url]
    tmall_urls = [r for r in results if '.tmall.com' in r.url]
    appuid_urls = [r for r in results if 'appUid=' in r.url]
    
    print(f"\nURL Format Distribution:")
    print(f"  shop*.taobao.com format: {len(taobao_urls)}")
    print(f"  *.tmall.com format: {len(tmall_urls)}")
    print(f"  appUid format (long): {len(appuid_urls)}")
    
    # Show sample URLs
    print(f"\nSample URLs:")
    for i, r in enumerate(results[:5], 1):
        print(f"  {i}. {r.store_name}")
        print(f"     {r.url}")
    
    print("\n✅ Test complete!")
    return len(results) >= 40  # Should get at least 40 out of 49


if __name__ == "__main__":
    success = asyncio.run(test())
    sys.exit(0 if success else 1)
