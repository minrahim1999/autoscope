# platform: android
# name: rerun_check
# generated: 2026-07-04T13:11:15.076425
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
