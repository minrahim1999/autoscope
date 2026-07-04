"""No-script web crawler: log in (optional), then visit every internal link."""

import json
import time
from collections import deque
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urldefrag, urljoin, urlparse

from playwright.sync_api import Page, Response, sync_playwright

from autoscope.config.loader import Config, WebConfig, load_config
from autoscope.reporting.html import generate_html_report


class CrawlResult:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self.visited: Dict[str, Dict] = {}
        self.broken: List[Dict] = []
        self.start_time = time.time()

    def add(self, url: str, response: Optional[Response], screenshot: Optional[Path]) -> None:
        status = response.status if response else None
        ok = status is not None and status < 400
        record = {
            "url": url,
            "status": status,
            "ok": ok,
            "screenshot": str(screenshot) if screenshot else None,
        }
        self.visited[url] = record
        if not ok:
            self.broken.append(record)

    def to_dict(self) -> Dict:
        duration = time.time() - self.start_time
        return {
            "type": "crawl",
            "base_url": self.base_url,
            "duration_seconds": duration,
            "summary": {
                "total": len(self.visited),
                "ok": sum(1 for v in self.visited.values() if v["ok"]),
                "broken": len(self.broken),
            },
            "visited": list(self.visited.values()),
            "broken": self.broken,
        }


def _same_origin(a: str, b: str) -> bool:
    pa, pb = urlparse(a), urlparse(b)
    return (pa.scheme, pa.netloc) == (pb.scheme, pb.netloc)


def _normalize(url: str) -> str:
    return urldefrag(url)[0].rstrip("/")


def _selector_fallback(page: Page, selectors: List[str], timeout: float = 10.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        for sel in selectors:
            try:
                if page.locator(sel).count() > 0:
                    return True
            except Exception:
                continue
        time.sleep(0.5)
    return False


def _fill_fallback(page: Page, selectors: List[str], value: str) -> bool:
    for sel in selectors:
        try:
            page.fill(sel, value)
            return True
        except Exception:
            continue
    return False


def _click_fallback(page: Page, selectors: List[str]) -> bool:
    for sel in selectors:
        try:
            page.click(sel)
            return True
        except Exception:
            continue
    return False


def login(page: Page, config: WebConfig, username: str, password: str) -> bool:
    """Try to log in using configurable or default selectors."""
    selectors = getattr(config, "login_selectors", {})
    user_selectors = selectors.get("username", ["input[type='email']", "input[name='email']", "input[name='username']", "#username"])
    pass_selectors = selectors.get("password", ["input[type='password']", "input[name='password']", "#password"])
    submit_selectors = selectors.get("submit", ["button:has-text('Login')", "button:has-text('Log in')", "button:has-text('Sign in')", "button[type='submit']", "input[type='submit']"])

    if not _selector_fallback(page, user_selectors + pass_selectors):
        return False

    _fill_fallback(page, user_selectors, username)
    _fill_fallback(page, pass_selectors, password)
    return _click_fallback(page, submit_selectors)


def extract_links(page: Page, base_url: str) -> Set[str]:
    """Return unique same-origin absolute URLs found on the page."""
    anchors = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    links: Set[str] = set()
    for href in anchors:
        absolute = urljoin(base_url, href)
        absolute = _normalize(absolute)
        if _same_origin(base_url, absolute):
            links.add(absolute)
    return links


def _screenshot_name(url: str, index: int) -> str:
    parsed = urlparse(url)
    path = parsed.path.strip("/").replace("/", "_") or "root"
    return f"crawl_{index:03d}_{path}.png"


def _make_page(config: WebConfig):
    browser_type = getattr(config, "browser", "chromium")
    headless = getattr(config, "headless", True)
    viewport = getattr(config, "viewport", {"width": 1280, "height": 720})
    timeout = getattr(config, "timeout_ms", 30000)

    playwright = sync_playwright().start()
    try:
        browser = getattr(playwright, browser_type).launch(headless=headless)
        context = browser.new_context(viewport=viewport)
        page = context.new_page()
        page.set_default_timeout(timeout)
        return playwright, browser, page
    except Exception:
        playwright.stop()
        raise


def crawl(
    url: str,
    username: Optional[str] = None,
    password: Optional[str] = None,
    config: Optional[Config] = None,
    max_depth: int = 3,
    max_pages: int = 50,
    screenshot: bool = True,
) -> CrawlResult:
    """Crawl a site starting at url, optionally logging in first."""
    config = config or load_config()
    base_url = _normalize(url)
    result = CrawlResult(base_url)
    seen: Set[str] = set()
    queue: deque[Tuple[str, int]] = deque([(base_url, 0)])

    playwright, browser, page = _make_page(config.web)
    try:
        while queue and len(seen) < max_pages:
            current_url, depth = queue.popleft()
            if current_url in seen or depth > max_depth:
                continue
            seen.add(current_url)
            index = len(seen)
            print(f"[crawl {index}/{max_pages}] {current_url} (depth {depth})")

            try:
                response = page.goto(current_url, wait_until="domcontentloaded", timeout=20000)

                shot_path: Optional[Path] = None
                if screenshot:
                    name = _screenshot_name(current_url, index)
                    shot_path = Path(config.web.screenshot_dir) / name
                    shot_path.parent.mkdir(parents=True, exist_ok=True)
                    page.screenshot(path=str(shot_path))

                result.add(current_url, response, shot_path)

                # Login only on the very first page if credentials supplied
                if depth == 0 and username and password:
                    print("[crawl] attempting auto-login")
                    logged_in = login(page, config.web, username, password)
                    if logged_in:
                        print("[crawl] login submitted, waiting for navigation")
                        try:
                            page.wait_for_url(lambda u: u != current_url, timeout=20000)
                        except Exception:
                            page.wait_for_load_state("domcontentloaded", timeout=20000)
                        response = page.goto(current_url, wait_until="domcontentloaded", timeout=20000)
                        result.add(current_url, response, shot_path)
                        print(f"[crawl] post-login url: {page.url}")
                    else:
                        print("[crawl] login selectors not found")

                if depth < max_depth:
                    for link in extract_links(page, base_url):
                        if link not in seen:
                            queue.append((link, depth + 1))
            except Exception as exc:
                print(f"[crawl] error on {current_url}: {exc}")
                result.add(current_url, None, None)
                result.visited[current_url]["error"] = str(exc)
                result.broken.append(result.visited[current_url])

        return result
    finally:
        try:
            page.context.close()
            browser.close()
        except Exception as exc:
            print(f"[crawl] cleanup warning: {exc}")
        try:
            playwright.stop()
        except Exception as exc:
            print(f"[crawl] playwright stop warning: {exc}")


def save_crawl_report(result: CrawlResult, config: Config) -> Tuple[Path, Path]:
    data = result.to_dict()
    Path(config.runner.output_dir).mkdir(parents=True, exist_ok=True)

    json_path = Path(config.runner.output_dir) / "crawl.json"
    json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    html_path = Path(config.runner.output_dir) / "crawl.html"
    html_path.write_text(generate_html_report(_crawl_data_for_html(data)), encoding="utf-8")

    return json_path, html_path


def _crawl_data_for_html(data: Dict) -> Dict:
    """Convert crawl data to the same shape the existing HTML template expects."""
    tests = []
    for item in data["visited"]:
        status = "passed" if item["ok"] else "failed"
        message = f"HTTP {item['status']}" if item["status"] else item.get("error", "No response")
        tests.append({
            "name": item["url"],
            "status": status,
            "message": message,
            "traceback": None,
        })
    return {
        "duration_seconds": data["duration_seconds"],
        "summary": {
            "total": data["summary"]["total"],
            "passed": data["summary"]["ok"],
            "failed": data["summary"]["broken"],
            "errors": 0,
            "skipped": 0,
        },
        "tests": tests,
    }
