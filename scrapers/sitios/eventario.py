import logging
import re
from datetime import date

from bs4 import BeautifulSoup

from config import USER_AGENT
from scrapers.base_playwright import BasePlaywrightScraper

logger = logging.getLogger(__name__)

BOGOTA_URL = "https://eventario.co/events/?location=Bogot%C3%A1%3B4.459464%2C-74.22363..4.837131%2C-73.99197"
PEREIRA_URL = "https://eventario.co/events/?location=Pereira"

CATEGORIA_KW = {
    "concierto": "concierto", "música": "concierto", "musica": "concierto",
    "rock": "concierto", "jazz": "concierto", "reggae": "concierto",
    "festival": "festival", "fiesta": "festival",
    "teatro": "teatro", "danza": "danza", "baile": "danza",
    "cine": "cine",
    "exposición": "exposicion", "exposicion": "exposicion", "arte": "exposicion",
    "taller": "taller",
}

RE_FECHA = re.compile(r"(\d{1,2})/(\d{2})")


class EventarioScraper(BasePlaywrightScraper):

    wait_selector = "h3.elementor-heading-title a"
    wait_timeout_ms = 20000
    extra_wait_ms = 2000

    def extraer_eventos(self):
        ciudad_low = (self.ciudad or "bogotá").lower()
        target_url = PEREIRA_URL if "pereira" in ciudad_low else BOGOTA_URL

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error("playwright no instalado. Ejecuta: pip install playwright && playwright install chromium")
            return []

        html = None
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
                page.goto(target_url, wait_until="domcontentloaded")
                page.wait_for_selector(self.wait_selector, timeout=self.wait_timeout_ms)
                page.wait_for_timeout(self.extra_wait_ms)

                # Click "Ver Más" until button disappears or count stops growing (max 20 clicks ~400 events)
                for _ in range(20):
                    btn = page.query_selector(".ts-load-more")
                    if not btn or not btn.is_visible():
                        break
                    prev_count = len(page.query_selector_all("h3.elementor-heading-title a"))
                    btn.scroll_into_view_if_needed()
                    btn.click()
                    page.wait_for_timeout(2500)
                    new_count = len(page.query_selector_all("h3.elementor-heading-title a"))
                    if new_count == prev_count:
                        break

                html = page.content()
                browser.close()
        except Exception as e:
            logger.error(f"Playwright error EventarioScraper: {e}")
            return []

        if not html:
            return []

        soup = BeautifulSoup(html, "lxml")
        return self._parsear(soup)

    def _parsear(self, soup):
        hoy = date.today()
        eventos = []
        seen = set()

        for card in soup.select("div.ts-preview"):
            try:
                title_a = card.select_one("h3.elementor-heading-title a")
                if not title_a:
                    continue
                titulo = title_a.get_text(strip=True)
                url_evento = title_a.get("href", "")
                if not titulo or not url_evento or url_evento in seen:
                    continue
                seen.add(url_evento)

                # Date: span whose entire text is DD/MM (e.g. "23/05")
                fecha = None
                for span in card.select("span"):
                    m = re.fullmatch(r"(\d{1,2})/(\d{2})", span.get_text(strip=True))
                    if m:
                        dia, mes = int(m.group(1)), int(m.group(2))
                        for yr in (hoy.year, hoy.year + 1):
                            try:
                                dt = date(yr, mes, dia)
                                if dt >= hoy:
                                    fecha = dt.strftime("%Y-%m-%d")
                                    break
                            except ValueError:
                                continue
                        if fecha:
                            break

                if not fecha:
                    continue

                # Venue from /places/ action link
                lugar = self.ciudad or "Bogotá"
                venue_a = card.select_one("a.ts-action-con[href*='/places/']")
                if venue_a:
                    lugar = venue_a.get_text(strip=True) or lugar

                # Image — Elementor lazy-loads; prefer data-src
                imagen_url = ""
                img = card.select_one("img")
                if img:
                    src = img.get("data-src", "") or img.get("src", "")
                    if src and src.startswith("http"):
                        imagen_url = src

                eventos.append({
                    "nombre_evento": titulo,
                    "fecha_evento": fecha,
                    "hora": "no especificado",
                    "lugar": lugar,
                    "ciudad": self.ciudad or "Bogotá",
                    "categoria": self._inferir_categoria(titulo),
                    "descripcion": "",
                    "url_post": url_evento,
                    "imagen_url": imagen_url,
                    "notas": "",
                })
            except Exception as e:
                logger.warning(f"Error parseando evento Eventario: {e}")

        return eventos

    def _inferir_categoria(self, texto):
        texto_low = texto.lower()
        for kw, cat in CATEGORIA_KW.items():
            if kw in texto_low:
                return cat
        return "concierto"
