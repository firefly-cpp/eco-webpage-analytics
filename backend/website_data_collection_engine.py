from __future__ import annotations

import argparse
import json
import logging
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse

from playwright.sync_api import Browser, Error, Page, Playwright, Request, Response, sync_playwright

LOGGER = logging.getLogger("website-data-collector")

RESOURCE_TYPE_MAP = {
    "document": "document",
    "stylesheet": "stylesheet",
    "script": "script",
    "image": "image",
    "media": "media",
    "font": "font",
    "xhr": "xhr_fetch",
    "fetch": "xhr_fetch",
    "websocket": "websocket",
    "manifest": "other",
    "eventsource": "other",
    "texttrack": "other",
    "other": "other",
}

def normalize_url(url: str):
    url = url.strip()

    if not url:
        raise ValueError("URL cannot be empty")

    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"Invalid URL: {url}")

    return url


def safe_float(value: Any):
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@dataclass
class RequestRecord:
    url: str
    resource_type: str
    transfer_bytes: int = 0
    content_length_header: Optional[int] = None


@dataclass
class SingleRunResult:
    success: bool
    summary: Dict[str, Any]


class WebsiteMeasurementEngine:
    def __init__(self, *, browser_name: str = "chromium", headless: bool = True, device: str = "desktop",
                 timeout_ms: int = 45000, wait_until: str = "load", post_load_wait_ms: int = 2500, 
                 block_images: bool = False, user_agent: Optional[str] = None):
        
        self.browser_name = browser_name
        self.headless = headless
        self.device = device
        self.timeout_ms = timeout_ms
        self.wait_until = wait_until
        self.post_load_wait_ms = post_load_wait_ms
        self.block_images = block_images
        self.user_agent = user_agent

    def measure_urls(self, urls: List[str], repeat_runs: int = 1):
        normalized_urls = [normalize_url(url) for url in urls]
        results: List[Dict[str, Any]] = []

        with sync_playwright() as playwright:
            browser = self.launch_browser(playwright)

            try:
                for url in normalized_urls:
                    runs = [self.measure_single_run(browser, url) for _ in range(repeat_runs)]
                    results.append(self.aggregate_runs(url, runs))
            finally:
                browser.close()

        return results

    def launch_browser(self, playwright: Playwright):
        browser_type = getattr(playwright, self.browser_name)
        return browser_type.launch(headless=self.headless)

    def build_context_options(self) -> Dict[str, Any]:
        options: Dict[str, Any] = {"ignore_https_errors": True, "java_script_enabled": True}

        if self.user_agent:
            options["user_agent"] = self.user_agent

        if self.device == "mobile":
            options.update(
                {
                    "viewport": {"width": 390, "height": 844},
                    "device_scale_factor": 2,
                    "is_mobile": True,
                    "has_touch": True,
                }
            )
        else:
            options.update(
                {
                    "viewport": {"width": 1440, "height": 900},
                    "device_scale_factor": 1,
                    "is_mobile": False,
                    "has_touch": False,
                }
            )

        return options

    def measure_single_run(self, browser: Browser, input_url: str):
        context = browser.new_context(**self.build_context_options())
        page = context.new_page()

        page.set_default_timeout(self.timeout_ms)
        page.set_default_navigation_timeout(self.timeout_ms)

        request_records: Dict[str, RequestRecord] = {}

        if self.block_images:
            def route_handler(route):
                if route.request.resource_type == "image":
                    route.abort()
                else:
                    route.continue_()

            page.route("**/*", route_handler)

        def on_request(request: Request):
            resource_type = RESOURCE_TYPE_MAP.get(request.resource_type, "other")

            request_records[request.url] = RequestRecord(url=request.url, resource_type=resource_type)

        def on_response(response: Response):
            request = response.request

            record = request_records.get(request.url)

            if not record:
                resource_type = RESOURCE_TYPE_MAP.get(request.resource_type, "other")
                record = RequestRecord(url=request.url, resource_type=resource_type)
                request_records[request.url] = record

            try:
                sizes = request.sizes()
            except Error:
                sizes = {}

            response_body_size = int(sizes.get("responseBodySize", 0) or 0)
            response_headers_size = int(sizes.get("responseHeadersSize", 0) or 0)

            record.transfer_bytes = response_body_size + response_headers_size

            content_length = response.headers.get("content-length")
            if content_length and content_length.isdigit():
                record.content_length_header = int(content_length)

                if record.transfer_bytes == 0:
                    record.transfer_bytes = record.content_length_header

        page.on("request", on_request)
        page.on("response", on_response)

        success = False
        page_metrics: Dict[str, Any] = {}

        try:
            response = page.goto(input_url, wait_until=self.wait_until)

            if self.post_load_wait_ms > 0:
                page.wait_for_timeout(self.post_load_wait_ms)

            success = response is not None
            page_metrics = self.collect_page_metrics(page)

        except Error as exc:
            LOGGER.warning("Failed to analyze %s: %s", input_url, exc)

            try:
                page_metrics = self.collect_page_metrics(page)
            except Error:
                page_metrics = {}

        summary = self.build_summary(input_url=input_url, request_records=request_records, page_metrics=page_metrics)

        page.close()
        context.close()

        return SingleRunResult(success=success, summary=summary)

    def collect_page_metrics(self, page: Page):
        script = """
        () => {
          const nav = performance.getEntriesByType('navigation')[0];

          return {
            loadMs: nav ? nav.loadEventEnd : null
          };
        }
        """

        return page.evaluate(script)

    def build_summary(self, *, input_url: str, request_records: Dict[str, RequestRecord], page_metrics: Dict[str, Any]):
        total_bytes = 0
        total_requests = 0
        images_bytes = 0
        js_bytes = 0
        css_bytes = 0

        for record in request_records.values():
            size = record.transfer_bytes or record.content_length_header or 0

            total_bytes += size
            total_requests += 1

            if record.resource_type == "image":
                images_bytes += size
            elif record.resource_type == "script":
                js_bytes += size
            elif record.resource_type == "stylesheet":
                css_bytes += size

        load_time_ms = safe_float(page_metrics.get("loadMs"))
        load_time_seconds = round(load_time_ms / 1000.0, 3) if load_time_ms else None

        return {
            "url": input_url,
            "total_bytes": total_bytes,
            "requests": total_requests,
            "images_bytes": images_bytes,
            "js_bytes": js_bytes,
            "css_bytes": css_bytes,
            "load_time": load_time_seconds,
        }

    def aggregate_runs(self, input_url: str, runs: List[SingleRunResult]):
        successful_runs = [run for run in runs if run.success]
        reference_runs = successful_runs or runs

        def median_for(field: str):
            values = [run.summary.get(field) for run in reference_runs]
            clean_values = [value for value in values if isinstance(value, (int, float))]

            if not clean_values:
                return None

            return statistics.median(clean_values)

        return {
            "url": input_url,
            "total_bytes": int(median_for("total_bytes") or 0),
            "requests": int(median_for("requests") or 0),
            "images_bytes": int(median_for("images_bytes") or 0),
            "js_bytes": int(median_for("js_bytes") or 0),
            "css_bytes": int(median_for("css_bytes") or 0),
            "load_time": median_for("load_time"),
        }


def parse_args(argv: Optional[Iterable[str]] = None):
    parser = argparse.ArgumentParser(description="Collect minimal webpage data transfer metrics using Playwright.")

    parser.add_argument("urls", nargs="*", help="One or more URLs to analyze.")
    parser.add_argument("--input-file", help="Path to a JSON file containing {'urls': [...], 'options': {...}.")
    parser.add_argument("--output-file", help="Where to save the JSON result.")

    parser.add_argument("--browser", choices=["chromium", "firefox", "webkit"], default="chromium")
    parser.add_argument("--device", choices=["desktop", "mobile"], default="desktop")
    parser.add_argument("--repeat-runs", type=int, default=1)
    parser.add_argument("--timeout-ms", type=int, default=45000)
    parser.add_argument("--wait-until", choices=["commit", "domcontentloaded", "load", "networkidle"], default="load")
    parser.add_argument("--post-load-wait-ms", type=int, default=2500)

    parser.add_argument("--headed", action="store_true", help="Run with a visible browser window.")
    parser.add_argument("--block-images", action="store_true")
    parser.add_argument("--user-agent", help="Optional custom user agent.")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    return parser.parse_args(list(argv) if argv is not None else None)


def load_urls_and_options(args: argparse.Namespace):
    urls = list(args.urls)
    options: Dict[str, Any] = {}

    if args.input_file:
        payload = json.loads(Path(args.input_file).read_text(encoding="utf-8"))
        urls.extend(payload.get("urls", []))
        options.update(payload.get("options", {}))

    deduped_urls: List[str] = []
    seen = set()

    for url in urls:
        normalized = normalize_url(url)

        if normalized not in seen:
            seen.add(normalized)
            deduped_urls.append(normalized)

    if not deduped_urls:
        raise SystemExit("No URLs were provided. Pass URLs directly or use --input-file.")

    cli_options = {
        "browser_name": args.browser,
        "device": args.device,
        "headless": not args.headed,
        "timeout_ms": args.timeout_ms,
        "wait_until": args.wait_until,
        "post_load_wait_ms": args.post_load_wait_ms,
        "block_images": args.block_images,
        "user_agent": args.user_agent,
    }

    cli_options.update(options)

    return deduped_urls, cli_options


def main(argv: Optional[Iterable[str]] = None):
    args = parse_args(argv)

    logging.basicConfig(level=getattr(logging, args.log_level), format="%(levelname)s %(message)s")

    urls, options = load_urls_and_options(args)
    repeat_runs = int(options.pop("repeat_runs", args.repeat_runs))

    LOGGER.info("Analyzing %s URL(s) with %s run(s) each", len(urls), repeat_runs)

    engine = WebsiteMeasurementEngine(**options)
    result = engine.measure_urls(urls, repeat_runs=repeat_runs)

    result_json = json.dumps(result, indent=2, ensure_ascii=False)

    if args.output_file:
        Path(args.output_file).write_text(result_json, encoding="utf-8")
        LOGGER.info("Saved results to %s", args.output_file)
    else:
        print(result_json)

    return 0


if __name__ == "__main__":
    sys.exit(main())