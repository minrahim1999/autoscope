"""Sample web test."""

from autoscope import AutomateTestCase


class TestExampleWeb(AutomateTestCase):
    tags = ("web",)

    def test_homepage_title(self) -> None:
        self.web.goto(self.config.web.base_url)
        title = self.web.title()
        self.assertIn("Example", title)
        self.web_screenshot("homepage.png")
