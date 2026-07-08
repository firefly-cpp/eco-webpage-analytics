import logging

import time
from dataclasses import dataclass
from typing import Any, Dict,  Optional
from urllib.parse import urlparse

from playwright.sync_api import Browser, Error, Page, Request, sync_playwright

LOGGER = logging.getLogger("website-data-collector")
logging.basicConfig(level=getattr(logging, "INFO"), format="%(levelname)s %(message)s")

TRACKED_RESOURCE_TYPES = {"image", "script", "stylesheet"}

DEFAULT_TIMEOUT_MS = 45000
DEFAULT_QUIET_WINDOW_MS = 1000
DEFAULT_MAX_OBSERVATION_MS = 15000
DEFAULT_POLL_INTERVAL_MS = 100


def normalize_url(url: str) -> str:
    url = url.strip()

    if not url:
        raise ValueError("URL cannot be empty.")

    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"Invalid URL: {url}")

    return url


@dataclass
class RequestRecord:
    resource_type: str
    transfer_bytes: int = 0
    completed: bool = False


@dataclass
class SingleRunResult:
    success: bool
    summary: Dict[str, Any]
    error: Optional[str] = None


class WebsiteMeasurementEngine:
    def __init__(self, *, headless: bool = True, timeout_ms: int = DEFAULT_TIMEOUT_MS, quiet_window_ms: int = DEFAULT_QUIET_WINDOW_MS, max_observation_ms: int = DEFAULT_MAX_OBSERVATION_MS):
        if timeout_ms <= 0:
            raise ValueError("timeout_ms must be greater than zero.")

        if quiet_window_ms < 0:
            raise ValueError("post_load_wait_ms cannot be negative.")

        if max_observation_ms <= 0:
            raise ValueError("max_observation_ms must be greater than zero.")

        if quiet_window_ms >= max_observation_ms:
            raise ValueError(
                "quiet_window_ms must be smaller than max_observation_ms."
            )

        self.headless = headless
        self.timeout_ms = timeout_ms
        self.quiet_window_ms = quiet_window_ms
        self.max_observation_ms = max_observation_ms

    def measure_url(self, url: str):

        normalized_url = normalize_url(url)

        if not normalized_url:
            raise ValueError("At least one URL must be provided.")

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=self.headless)

            try:
                result = self.measure_run(browser, normalized_url)
            finally:
                browser.close()

        if not result.success:
            raise RuntimeError(result.error or f"Failed to measure {normalized_url}")

        return result.summary

    def build_context(self, browser: Browser):
        return browser.new_context(
            device_scale_factor=1,
            is_mobile=False,
            has_touch=False,
            timezone_id="UTC",
            service_workers="block"
        )
    

    def measure_run(self, browser: Browser, input_url: str):
        context = self.build_context(browser)
        page = context.new_page()
        page.set_default_timeout(self.timeout_ms)
        page.set_default_navigation_timeout(self.timeout_ms)

        request_records: Dict[Request, RequestRecord] = {}
        in_flight_requests: set[Request] = set()

        collecting = True
        last_network_activity = time.monotonic()

        def mark_network_activity():
            nonlocal last_network_activity
            last_network_activity = time.monotonic()

        def on_request(request: Request):
            if not collecting:
                return
            
            if request.resource_type in TRACKED_RESOURCE_TYPES:
                resource_type = request.resource_type
            else:
                resource_type = "other"

            request_records[request] = RequestRecord(resource_type=resource_type)

            in_flight_requests.add(request)
            mark_network_activity()

        def on_request_finished(request: Request):
            if not collecting:
                return

            record = request_records.get(request)
            if record is None:
                in_flight_requests.discard(request)
                mark_network_activity()
                return

            try:
                sizes = request.sizes()
                body_size = max(0, int(sizes.get("responseBodySize", 0) or 0))
                header_size = max(0, int(sizes.get("responseHeadersSize", 0) or 0))

                record.transfer_bytes = body_size + header_size
                record.completed = True

            except Error as exc:
                LOGGER.warning("Could not obtain response size for %s: %s", request.url, exc)

            finally:
                in_flight_requests.discard(request)
                mark_network_activity()

        def on_request_failed(request: Request):
            if not collecting:
                return
            
            in_flight_requests.discard(request)
            request_records.pop(request, None)
            mark_network_activity()

        page.on("request", on_request)
        page.on("requestfinished", on_request_finished)
        page.on("requestfailed", on_request_failed)

        success = False
        error_message: Optional[str] = None
        page_metrics: Dict[str, Any] = {}

        try:
            main_response = page.goto(input_url, wait_until="load")

            quiet_window_seconds = self.quiet_window_ms / 1000.0
            deadline = (time.monotonic() + self.max_observation_ms / 1000.0)

            while time.monotonic() < deadline:
                now = time.monotonic()

                quiet_for_long_enough = (now - last_network_activity >= quiet_window_seconds)

                if not in_flight_requests and quiet_for_long_enough:
                    break

                page.wait_for_timeout(DEFAULT_POLL_INTERVAL_MS)


            if main_response is None:
                error_message = "Navigation completed without an HTTP response."
            elif not main_response.ok:
                error_message = f"Main document returned HTTP {main_response.status}."
            else:
                success = True

            page_metrics = self.collect_page_metrics(page)

        except Error as exc:
            error_message = str(exc)
            LOGGER.warning("Failed to analyze %s: %s", input_url, exc)

        finally:
            collecting = False
            summary = self.build_summary(input_url=input_url, request_records=request_records, page_metrics=page_metrics)
            context.close()

        return SingleRunResult(success=success, summary=summary, error=error_message)

    @staticmethod
    def collect_page_metrics(page: Page):
        return page.evaluate(
            """
            () => {
              const nav = performance.getEntriesByType("navigation")[0];
              return {
                loadMs:
                  nav && nav.loadEventEnd > 0
                    ? nav.loadEventEnd
                    : null
              };
            }
            """
        )

    @staticmethod
    def build_summary(*, input_url: str, request_records: Dict[Request, RequestRecord], page_metrics: Dict[str, Any]):
        totals = {
            "total_bytes": 0,
            "requests": 0,
            "images_bytes": 0,
            "js_bytes": 0,
            "css_bytes": 0
        }

        for record in request_records.values():
            if not record.completed:
                continue

            size = record.transfer_bytes
            totals["total_bytes"] += size
            totals["requests"] += 1

            if record.resource_type == "image":
                totals["images_bytes"] += size
            elif record.resource_type == "script":
                totals["js_bytes"] += size
            elif record.resource_type == "stylesheet":
                totals["css_bytes"] += size

        load_ms = page_metrics.get("loadMs")

        if isinstance(load_ms, (int, float)) and load_ms > 0:
            load_time = round(float(load_ms) / 1000.0, 3)
        else:
            load_time = None

        return {
            "url": input_url,
            **totals,
            "load_time": load_time
        }