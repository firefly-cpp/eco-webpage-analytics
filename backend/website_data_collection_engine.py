import logging
import io
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import tldextract
from PIL import Image, UnidentifiedImageError
from playwright.sync_api import Browser, Error, Page, Request, Route, sync_playwright

LOGGER = logging.getLogger("website-data-collector")
logging.basicConfig(level=getattr(logging, "INFO"), format="%(levelname)s %(message)s")

TRACKED_RESOURCE_TYPES = {"image", "script", "stylesheet", "font", "media"}

DEFAULT_TIMEOUT_MS = 180000
DEFAULT_QUIET_WINDOW_MS = 1000
DEFAULT_MAX_OBSERVATION_MS = 15000
DEFAULT_POLL_INTERVAL_MS = 100
DEFAULT_MAX_SCROLLS = 100
DEFAULT_SCROLL_WAIT_MS = 750
DEFAULT_SCROLL_STEP_RATIO = 0.8

WEBP_QUALITY = 80

TLD_EXTRACTOR = tldextract.TLDExtract(suffix_list_urls=())


@dataclass
class RequestRecord:
    resource_type: str
    third_party: bool = False
    transfer_bytes: int = 0
    webp_bytes: Optional[int] = None
    completed: bool = False


@dataclass
class SingleRunResult:
    success: bool
    summary: Dict[str, Any]
    error: Optional[str] = None


def normalize_url(url: str):
    url = url.strip()

    if not url:
        raise ValueError("URL cannot be empty.")

    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"Invalid URL: {url}")

    return url


def get_registered_domain(url: str):
    parsed = urlparse(url)

    if not parsed.hostname:
        return ""

    extracted = TLD_EXTRACTOR(parsed.hostname)

    if extracted.suffix:
        return f"{extracted.domain}.{extracted.suffix}"

    return parsed.hostname


def is_third_party(request_url: str, page_url: str):
    request_domain = get_registered_domain(request_url)
    page_domain = get_registered_domain(page_url)

    if not request_domain or not page_domain:
        return False

    third_party = (request_domain != page_domain)

    if third_party:
        LOGGER.info(
            "BLOCK  page=%s request=%s url=%s", page_domain, request_domain, request_url
        )

    else:
        LOGGER.info(
            "ALLOW  page=%s request=%s url=%s", page_domain, request_domain, request_url
        )

    return third_party


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
                baseline = self.measure_run(browser, normalized_url)
                full_scroll = self.measure_run(browser, normalized_url, scroll_page=True)
                without_third_party = self.measure_run(browser, normalized_url, scroll_page=True, block_third_party=True)
            finally:
                browser.close()

        if not baseline.success:
            raise RuntimeError(baseline.error or f"Failed to measure {normalized_url}")

        if not full_scroll.success:
                    raise RuntimeError(full_scroll.error or f"Failed to measure full scroll for {normalized_url}")

        if not without_third_party.success:
                    raise RuntimeError(without_third_party.error or f"Failed to measure without third-party resources for {normalized_url}")

        return {
            "url": normalized_url,
            "baseline": {
                **baseline.summary,
                "image_transcoding": self.build_image_transcoding(baseline.summary)
            },
            "full_scroll": {
                **full_scroll.summary,
                "image_transcoding": self.build_image_transcoding(full_scroll.summary)
            },
            "without_third_party": {
                **without_third_party.summary,
                "image_transcoding": self.build_image_transcoding(without_third_party.summary)
            }
        }

    def build_context(self, browser: Browser):
        return browser.new_context(
            device_scale_factor=1,
            is_mobile=False,
            has_touch=False,
            timezone_id="UTC",
            service_workers="block"
        )
    

    def measure_run(self, browser: Browser, input_url: str, *, scroll_page: bool = False, block_third_party: bool = False):
        context = self.build_context(browser)

        if block_third_party:
            context.route("**/*", lambda route: self.handle_route(route, input_url))

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

        def wait_for_network_quiet():
            quiet_window_seconds = self.quiet_window_ms / 1000.0
            deadline = (time.monotonic() + self.max_observation_ms / 1000.0)

            while time.monotonic() < deadline:
                now = time.monotonic()
                quiet_for_long_enough = (now - last_network_activity >= quiet_window_seconds)

                if not in_flight_requests and quiet_for_long_enough:
                    break

                page.wait_for_timeout(DEFAULT_POLL_INTERVAL_MS)

        def on_request(request: Request):
            if not collecting:
                return
            
            if request.resource_type in TRACKED_RESOURCE_TYPES:
                resource_type = request.resource_type
            else:
                resource_type = "other"

            request_records[request] = RequestRecord(
                resource_type=resource_type,
                third_party=is_third_party(request.url, input_url)
            )

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

            record.completed = True

            try:
                sizes = request.sizes()
                request_body_size = max(0, int(sizes.get("requestBodySize", 0) or 0))
                request_header_size = max(0, int(sizes.get("requestHeadersSize", 0) or 0))
                response_body_size = max(0, int(sizes.get("responseBodySize", 0) or 0))
                response_header_size = max(0,int(sizes.get("responseHeadersSize", 0) or 0))

                record.transfer_bytes = request_body_size + request_header_size + response_body_size + response_header_size

                if record.resource_type == "image":
                    record.webp_bytes = self.measure_webp_size(request)

            except Error as exc:
                LOGGER.warning("Could not obtain response size for %s: %s", request.url, exc)

            finally:
                in_flight_requests.discard(request)
                mark_network_activity()

        def on_request_failed(request: Request):
            if not collecting:
                return
            
            in_flight_requests.discard(request)
            mark_network_activity()

        page.on("request", on_request)
        page.on("requestfinished", on_request_finished)
        page.on("requestfailed", on_request_failed)

        success = False
        error_message: Optional[str] = None
        page_metrics: Dict[str, Any] = {}

        try:
            main_response = page.goto(input_url, wait_until="load")

            wait_for_network_quiet()

            if scroll_page:
                self.scroll_page(page, wait_for_network_quiet)
                wait_for_network_quiet()

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
    def build_image_transcoding(summary: Dict[str, Any]):
        original_bytes = summary.get("images_optimizable_bytes", 0)
        webp_bytes = summary.get("images_webp_bytes", 0)

        return {
            "quality": WEBP_QUALITY,
            "original_bytes": original_bytes,
            "webp_bytes": webp_bytes,
            "saved_bytes": max(0,original_bytes - webp_bytes)
        }

    @staticmethod
    def handle_route(route: Route, input_url: str):
        if is_third_party(route.request.url, input_url):
            route.abort()
        else:
            route.continue_()

    @staticmethod
    def measure_webp_size(request: Request):
        try:
            response = request.response()

            if response is None:
                return None

            body = response.body()

            if not body:
                return None

            with Image.open(io.BytesIO(body)) as image:
                if getattr(image, "is_animated", False):
                    return None

                image.load()
                has_alpha = ("A" in image.getbands() or "transparency" in image.info)

                if image.mode not in {"RGB", "RGBA"}:
                    image = image.convert("RGBA" if has_alpha else "RGB")

                output = io.BytesIO()
                image.save(output, format="WEBP", quality=WEBP_QUALITY)

                return output.tell()

        except (Error, OSError, UnidentifiedImageError):
            return None

    @staticmethod
    def scroll_page(page: Page, wait_for_network_quiet):
        for _ in range(DEFAULT_MAX_SCROLLS):
            scroll_data = page.evaluate(
                """
                () => {
                  const documentHeight = Math.max(
                    document.body.scrollHeight,
                    document.documentElement.scrollHeight
                  );

                  return {
                    documentHeight,
                    scrollY: window.scrollY,
                    viewportHeight: window.innerHeight
                  };
                }
                """
            )

            document_height = scroll_data["documentHeight"]
            scroll_y = scroll_data["scrollY"]
            viewport_height = scroll_data["viewportHeight"]

            if scroll_y + viewport_height >= document_height:
                page.wait_for_timeout(DEFAULT_SCROLL_WAIT_MS)
                wait_for_network_quiet()

                new_document_height = page.evaluate(
                    """
                    () => Math.max(
                      document.body.scrollHeight,
                      document.documentElement.scrollHeight
                    )
                    """
                )

                if new_document_height <= document_height:
                    break

            page.mouse.wheel(0, int(viewport_height * DEFAULT_SCROLL_STEP_RATIO))
            page.wait_for_timeout(DEFAULT_SCROLL_WAIT_MS)
            wait_for_network_quiet()

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
            "css_bytes": 0,
            "fonts_bytes": 0,
            "media_bytes": 0,
            "third_party_bytes": 0,
            "third_party_requests": 0,
            "images_optimizable_bytes": 0,
            "images_webp_bytes": 0,
            "unfinished_requests": 0
        }

        for record in request_records.values():
            if not record.completed:
                totals["unfinished_requests"] += 1
                continue

            size = record.transfer_bytes
            totals["total_bytes"] += size
            totals["requests"] += 1

            if record.third_party:
                totals["third_party_bytes"] += size
                totals["third_party_requests"] += 1

            if record.resource_type == "image":
                totals["images_bytes"] += size

                if record.webp_bytes is not None:
                    totals["images_optimizable_bytes"] += size
                    totals["images_webp_bytes"] += record.webp_bytes

            elif record.resource_type == "script":
                totals["js_bytes"] += size

            elif record.resource_type == "stylesheet":
                totals["css_bytes"] += size

            elif record.resource_type == "font":
                totals["fonts_bytes"] += size

            elif record.resource_type == "media":
                totals["media_bytes"] += size

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