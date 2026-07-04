# platform: web
# name: test_login
# generated: 2026-07-04T07:06:43.623869
from autoscope.drivers.web import WebDriver
from autoscope.config.loader import load_config

def run():
    config = load_config()
    driver = WebDriver(config.web)
    page = driver.start()
    try:
        page.goto('https://example.com/login')
        page.fill("input[type='email']", 'user@example.com')
        page.fill("input[type='password']", 'secret')
        page.click("button:has-text('Login')")
    finally:
        driver.stop()

if __name__ == "__main__":
    run()
