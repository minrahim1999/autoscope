import os
import time
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

url = "https://staging-ucaringiot.lcpsolution.com/login"
username = os.environ.get("CRAWL_USERNAME", "superadmin@ucaring.com")
password = os.environ.get("CRAWL_PASSWORD", "password123")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    page.set_default_timeout(20000)

    print("goto login")
    response = page.goto(url, wait_until="domcontentloaded", timeout=20000)
    print("status", response.status if response else None, "url", page.url)

    print("fill login")
    page.fill("input[type='email']", username)
    page.fill("input[type='password']", password)
    print("click login")
    page.click("button:has-text('Login')")
    try:
        page.wait_for_url(lambda u: u != url, timeout=20000)
        print("navigated to", page.url)
    except Exception as e:
        print("wait_for_url failed", e)

    print("re-goto login")
    response = page.goto(url, wait_until="domcontentloaded", timeout=20000)
    print("after re-goto status", response.status if response else None, "url", page.url)

    print("screenshot")
    shot = Path("var/reports/screenshots/diag.png")
    shot.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(shot))
    print("screenshot saved", shot)

    print("extract links")
    anchors = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    print("links count", len(anchors))
    print(anchors[:10])

    browser.close()
