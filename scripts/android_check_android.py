# platform: android
# name: android_check
# generated: 2026-07-04T12:45:46.408679
from autoscope.drivers.android import AndroidDriver
from autoscope.config.loader import load_config

def run():
    config = load_config()
    driver = AndroidDriver(config.android)
    device = driver.start()
    try:
        pass
    finally:
        driver.stop()

if __name__ == "__main__":
    run()
