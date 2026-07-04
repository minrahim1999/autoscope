import sys
from playwright.sync_api import sync_playwright

url = sys.argv[1] if len(sys.argv) > 1 else "https://staging-ucaringiot.lcpsolution.com/login"
print(f"Loading {url}")
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.set_default_timeout(30000)
    try:
        response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
        print("status:", response.status if response else None)
        print("title:", page.title())
        print("url:", page.url)
    except Exception as e:
        print("ERROR:", type(e).__name__, e)
    finally:
        browser.close()
