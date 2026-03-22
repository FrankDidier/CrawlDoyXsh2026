"""
Shared helpers for web crawlers: user confirmation signals.
"""
import asyncio


async def page_has_go_signal(page) -> bool:
    """
    Detect #go in URL. Uses window.location (works when Playwright page.url omits hash on some SPAs).
    """
    try:
        return await page.evaluate(
            """() => {
                try {
                    const h = window.location.href || '';
                    const hash = window.location.hash || '';
                    return h.includes('#go') || hash.includes('go');
                } catch (e) { return false; }
            }"""
        )
    except Exception:
        return False


async def wait_for_go_or_timeout(page, max_wait_seconds: int = 180, poll_interval: float = 1.0) -> bool:
    """
    Wait until user adds #go to URL or timeout.
    Returns True if #go was seen before timeout.
    """
    waited = 0
    while waited < max_wait_seconds:
        if await page_has_go_signal(page):
            return True
        await asyncio.sleep(poll_interval)
        waited += int(poll_interval)
    return await page_has_go_signal(page)
