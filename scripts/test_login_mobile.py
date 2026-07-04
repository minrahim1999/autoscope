# platform: mobile
# name: test_login
# generated: 2026-07-04T07:06:49.147942
from autoscope.drivers.mobile import MobileDriver
from autoscope.config.loader import load_config

def run():
    config = load_config()
    driver = MobileDriver(config.mobile)
    device = driver.start()
    try:
        device.click(540, 1200)
        driver.adb.run(['shell', 'input', 'text', 'hello world'])
        driver.adb.run(['shell', 'input', 'swipe', '100', '500', '100', '100', '300'])
    finally:
        driver.stop()

if __name__ == "__main__":
    run()
