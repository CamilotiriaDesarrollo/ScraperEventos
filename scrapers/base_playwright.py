import logging

from bs4 import BeautifulSoup

from config import USER_AGENT
from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class BasePlaywrightScraper(BaseScraper):
    """Variante de BaseScraper que usa Playwright para sitios que renderizan con JS."""

    wait_selector = None
    wait_timeout_ms = 20000
    extra_wait_ms = 0

    def fetch(self, url=None):
        target = url or self.url
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error("playwright no esta instalado. Ejecuta: pip install playwright && playwright install chromium")
            return None

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=USER_AGENT,
                    locale="es-CO",
                    viewport={"width": 1366, "height": 900},
                )
                page = context.new_page()
                page.set_default_timeout(self.wait_timeout_ms)
                page.goto(target, wait_until="domcontentloaded")
                if self.wait_selector:
                    try:
                        page.wait_for_selector(self.wait_selector, timeout=self.wait_timeout_ms)
                    except Exception as e:
                        logger.warning(f"wait_selector '{self.wait_selector}' no aparecio en {target}: {e}")
                if self.extra_wait_ms:
                    page.wait_for_timeout(self.extra_wait_ms)
                html = page.content()
                browser.close()
            return BeautifulSoup(html, "lxml")
        except Exception as e:
            logger.error(f"Playwright error fetching {target}: {e}")
            return None
