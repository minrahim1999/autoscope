"""Record manual web interactions using Playwright and generate scripts."""

import json
import threading
import time
from pathlib import Path
from typing import Callable, List, Optional, cast

from playwright.sync_api import Page, Playwright, sync_playwright

from autoscope.config.loader import Config, WebConfig, load_config
from autoscope.desktop.recorder.script_builder import RecordedAction, ScriptBuilder


_JS_RECORDER = """
(function() {
  if (window.__automateTesterRecording) return;
  window.__automateTesterRecording = true;

  function generateLocator(el) {
    if (!el || el.nodeType !== 1) return "";
    const testId = el.getAttribute("data-testid");
    if (testId) return `[data-testid="${testId}"]`;
    if (el.id) return `#${el.id}`;
    const name = el.getAttribute("name");
    if (name) return `[name="${name}"]`;
    const ariaLabel = el.getAttribute("aria-label");
    if (ariaLabel) return `[aria-label="${ariaLabel}"]`;
    const placeholder = el.getAttribute("placeholder");
    if (placeholder) return `[placeholder="${placeholder}"]`;
    const text = (el.textContent || "").trim();
    if (text && (el.tagName === "BUTTON" || el.tagName === "A")) {
      return `${el.tagName.toLowerCase()}:has-text('${text.replace(/'/g, "\\'")}')`;
    }
    // Fallback: simple CSS path
    const path = [];
    let node = el;
    while (node && node.nodeType === 1) {
      let selector = node.nodeName.toLowerCase();
      if (node.id) {
        selector += "#" + node.id;
        path.unshift(selector);
        break;
      }
      let sib = node, nth = 1;
      while (sib = sib.previousElementSibling) {
        if (sib.nodeName === node.nodeName) nth++;
      }
      if (nth > 1) selector += `:nth-of-type(${nth})`;
      path.unshift(selector);
      node = node.parentElement;
    }
    return path.join(" > ");
  }

  function send(action, data) {
    if (window.automateTesterRecord) {
      window.automateTesterRecord({
        action: action,
        data: data,
        url: location.href,
        title: document.title,
        timestamp: Date.now()
      });
    }
  }

  document.addEventListener("click", function(e) {
    const el = e.composedPath ? e.composedPath()[0] : e.target;
    const locator = generateLocator(el);
    if (locator) {
      send("click", { selector: locator, x: e.clientX, y: e.clientY });
    }
  }, true);

  document.addEventListener("input", function(e) {
    const el = e.target;
    if (el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.isContentEditable)) {
      const locator = generateLocator(el);
      const value = el.isContentEditable ? el.innerText : el.value;
      if (locator) {
        send("fill", { selector: locator, value: value });
      }
    }
  }, true);

  document.addEventListener("submit", function(e) {
    const el = e.target;
    const locator = generateLocator(el);
    if (locator) {
      send("submit", { selector: locator });
    }
  }, true);

  // Detect navigation
  let lastUrl = location.href;
  setInterval(function() {
    const url = location.href;
    if (url !== lastUrl) {
      lastUrl = url;
      send("goto", { url: url });
    }
  }, 500);
})();
"""


class WebRecorder:
    """Record web interactions in a headed Playwright browser."""

    def __init__(self, config: Optional[Config] = None) -> None:
        self.config = config or load_config()
        self.web_config: WebConfig = self.config.web
        self._playwright: Optional[Playwright] = None
        self._browser = None
        self._page: Optional[Page] = None
        self._actions: List[RecordedAction] = []
        self._builder: Optional[ScriptBuilder] = None
        self._callback: Optional[Callable[[RecordedAction], None]] = None
        self._lock = threading.Lock()
        self._recording = False

    def set_callback(self, callback: Callable[[RecordedAction], None]) -> None:
        self._callback = callback

    def start(
        self,
        url: str,
        name: str = "web_recording",
        headless: bool = False,
    ) -> Page:
        """Launch browser, navigate to URL, and start recording interactions."""
        self._actions = []
        self._builder = ScriptBuilder(platform="web", name=name, base_url=url)
        self._recording = True

        self._playwright = sync_playwright().start()
        browser_type = getattr(self._playwright, self.web_config.browser, self._playwright.chromium)
        self._browser = browser_type.launch(headless=headless)
        context = self._browser.new_context(viewport=cast(dict, self.web_config.viewport))  # type: ignore[arg-type]
        self._page = context.new_page()
        assert self._page is not None
        self._page.set_default_timeout(self.web_config.timeout_ms)

        self._page.expose_function("automateTesterRecord", self._on_action)
        self._page.add_init_script(_JS_RECORDER)
        self._page.goto(url, wait_until="domcontentloaded")

        # Seed first goto action
        self._record("goto", {"url": self._page.url})
        return self._page

    def _record(self, action: str, data: dict) -> None:
        with self._lock:
            if not self._recording:
                return
            # Deduplicate consecutive fill actions on the same selector
            if action == "fill" and self._actions:
                last = self._actions[-1]
                if last.action == "fill" and last.data.get("selector") == data.get("selector"):
                    last.data["value"] = data.get("value", "")
                    return
            recorded = RecordedAction(action=action, platform="web", data=data)
            self._actions.append(recorded)
            assert self._builder is not None
            self._builder.add(action, data)
            if self._callback:
                self._callback(recorded)

    def _on_action(self, payload: dict) -> None:
        action = payload.get("action", "")
        data = payload.get("data", {})
        current_url = payload.get("url", "")
        # Insert goto if the action happened on a different page than last recorded url
        with self._lock:
            last_url = self._actions[-1].data.get("url", "") if self._actions else ""
        if action != "goto" and current_url and current_url != last_url:
            self._record("goto", {"url": current_url})
        self._record(action, data)

    def stop(self) -> Optional[Path]:
        """Stop recording and save generated script. Returns path to script."""
        self._recording = False
        try:
            if self._page:
                self._page.close()
            if self._browser:
                self._browser.close()
        finally:
            if self._playwright:
                self._playwright.stop()
            self._page = None
            self._browser = None
            self._playwright = None
        if self._builder:
            return self._builder.save()
        return None

    def take_screenshot(self, name: str) -> None:
        """Record a screenshot action and capture actual screenshot if running."""
        self._record("screenshot", {"name": name})
        if self._page:
            shot_dir = Path(self.web_config.screenshot_dir)
            shot_dir.mkdir(parents=True, exist_ok=True)
            self._page.screenshot(path=str(shot_dir / name))

    @property
    def is_recording(self) -> bool:
        return self._recording

    def get_script_preview(self) -> str:
        if self._builder:
            return self._builder.build()
        return ""
