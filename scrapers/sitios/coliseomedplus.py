import logging
import re
from datetime import datetime

from scrapers.base_playwright import BasePlaywrightScraper

logger = logging.getLogger(__name__)

BASE_URL = "https://www.coliseomedplus.com"

MESES_ES = {
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
    "jul": 7, "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12,
}

RE_FECHA = re.compile(r"(\d{1,2})\s+([A-Za-z]{3})\.?\s+(\d{4})\s+(\d{1,2}:\d{2})\s*(am|pm)", re.I)


class ColiseoMedPlusScraper(BasePlaywrightScraper):

    wait_selector = ".upcoming-event-details"
    wait_timeout_ms = 20000
    extra_wait_ms = 2000

    def extraer_eventos(self):
        soup = self.fetch(BASE_URL)
        if not soup:
            return []

        hoy = datetime.now().date()
        eventos = []
        seen = set()

        for card in soup.select(".upcoming-event-details"):
            try:
                title_a = card.select_one("h3 a")
                if not title_a:
                    continue
                titulo = title_a.get_text(strip=True).title()
                href = title_a.get("href", "")
                if not href or href in seen:
                    continue
                seen.add(href)
                url = href if href.startswith("http") else f"{BASE_URL}{href}"

                # Date from <li> with calendar icon: "22 Ago. 2026 8:00 pm"
                fecha = None
                hora = "no especificado"
                for li in card.select("li"):
                    m = RE_FECHA.search(li.get_text(strip=True))
                    if m:
                        dia, mes_str, anio, h_val, ampm = m.groups()
                        mes = MESES_ES.get(mes_str.lower()[:3])
                        if mes:
                            try:
                                dt = datetime(int(anio), mes, int(dia)).date()
                                if dt >= hoy:
                                    fecha = dt.strftime("%Y-%m-%d")
                                    hora = f"{h_val} {ampm.upper()}"
                            except ValueError:
                                pass
                        break

                if not fecha:
                    continue

                img_el = card.select_one("img[data-src]")
                imagen_url = img_el.get("data-src", "") if img_el else ""

                eventos.append({
                    "nombre_evento": titulo,
                    "fecha_evento": fecha,
                    "hora": hora,
                    "lugar": "Coliseo MedPlus",
                    "ciudad": self.ciudad or "Bogotá",
                    "categoria": "concierto",
                    "descripcion": "",
                    "url_post": url,
                    "imagen_url": imagen_url,
                    "notas": "",
                })
            except Exception as e:
                logger.warning(f"Error parseando evento ColiseoMedPlus: {e}")

        return eventos
