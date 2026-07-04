import os
import sys
from playwright.sync_api import sync_playwright

url = "https://staging-ucaringiot.lcpsolution.com/login"
username = os.environ.get("CRAWL_USERNAME", "superadmin@ucaring.com")
password = os.environ.get("CRAWL_PASSWORD", "password123")

print(f"Loading {url}")
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.set_default_timeout(30000)
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        print("title:", page.title())
        print("url:", page.url)

        print("Filling username")
        page.fill("input[type='email']", username)
        print("Filling password")
        page.fill("input[type='password']", password)
        print("Clicking login")
        page.click("button:has-text('Login')")
        page.wait_for_load_state("domcontentloaded", timeout=30000)
        print("after login url:", page.url)
        print("after login title:", page.title())
    except Exception as e:
        print("ERROR:", type(e).__name__, e)
    finally:
        browser.close()
