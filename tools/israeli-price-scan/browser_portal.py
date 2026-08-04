#!/usr/bin/env python3
"""Drive a real browser for portals behind a JS challenge (Super-Pharm) or picky TLS."""
import sys, json, re
from playwright.sync_api import sync_playwright


def dump(url, wait_selector=None, ms=15000):
    with sync_playwright() as p:
        import os
        proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
        b = p.chromium.launch(
            executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
            args=["--no-sandbox"],
            proxy={"server": proxy} if proxy else None)
        ctx = b.new_context(locale="he-IL", user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"))
        pg = ctx.new_page()
        pg.goto(url, wait_until="domcontentloaded", timeout=90000)
        pg.wait_for_timeout(ms)
        if wait_selector:
            try:
                pg.wait_for_selector(wait_selector, timeout=30000)
            except Exception:
                pass
        html = pg.content()
        b.close()
        return html


if __name__ == "__main__":
    url = sys.argv[1]
    sel = sys.argv[2] if len(sys.argv) > 2 else None
    h = dump(url, sel)
    print(len(h))
    open("/tmp/browser_dump.html", "w").write(h)
    for l in sorted(set(re.findall(r'href="([^"]+)"', h)))[:40]:
        print(l)
