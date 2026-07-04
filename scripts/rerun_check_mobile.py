# platform: mobile
# name: rerun_check
# generated: 2026-07-04T13:11:15.076425
from autoscope.drivers.mobile import MobileDriver
from autoscope.config.loader import load_config

def run():
    config = load_config()
    driver = MobileDriver(config.mobile)
    device = driver.start()
    try:
    finally:
        driver.stop()

if __name__ == "__main__":
    run()
