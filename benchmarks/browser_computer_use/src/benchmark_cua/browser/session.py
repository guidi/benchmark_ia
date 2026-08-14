from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright


@dataclass
class BrowserConfig:
    channel: str = "chrome"
    headless: bool = True
    viewport_width: int = 1280
    viewport_height: int = 720


@contextmanager
def launch_browser(config: BrowserConfig) -> Iterator[tuple[Playwright, Browser, BrowserContext, Page]]:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            channel=config.channel,
            headless=config.headless,
        )
        context = browser.new_context(
            viewport={"width": config.viewport_width, "height": config.viewport_height},
        )
        page = context.new_page()
        try:
            yield playwright, browser, context, page
        finally:
            context.close()
            browser.close()


def browser_smoke_test(channel: str = "chrome", url: str = "https://example.com") -> str:
    config = BrowserConfig(channel=channel, headless=True)
    with launch_browser(config) as (_, _, _, page):
        page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        return page.title()

