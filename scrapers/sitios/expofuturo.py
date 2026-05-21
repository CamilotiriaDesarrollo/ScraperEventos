import logging
import re
from datetime import datetime

from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

BASE_URL = "https://www.expofuturo.com"
EVENTOS_URL = f"{BASE_URL}/es/ieventos/"

MESES_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}

RE_FECHA = re.compile(r"\[?\s*(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})\s*\]?", re.I)


class ExpoFuturoScraper(BaseScraper):

    def extraer_eventos(self):
        soup = self.fetch(EVENTOS_URL)
        if not soup:
            return []

        hoy = datetime.now().date()
        eventos = []
        seen = set()

        for card in soup.select("div.card"):
            try:
                a = card.select_one("a.overlay[href]")
                if not a:
                    continue
                href = a.get("href", "")
                if not href or href in seen:
                    continue
                seen.add(href)
                url = f"{BASE_URL}{href}" if href.startswith("/") else href

                titulo_el = card.select_one("h4.card-title")
                if not titulo_el:
                    titulo_el = card.select_one("h4")
                if not titulo_el:
                    continue
                titulo = titulo_el.get_text(strip=True).title()
                if not titulo:
                    continue

                # Date in <p>[06 de Noviembre de 2026]</p>
                fecha = None
                for p in card.select("p"):
                    m = RE_FECHA.search(p.get_text())
                    if m:
                        dia, mes_str, anio = m.groups()
                        mes = MESES_ES.get(mes_str.lower())
                        if mes:
                            try:
                                dt = datetime(int(anio), mes, int(dia)).date()
                                if dt >= hoy:
                                    fecha = dt.strftime("%Y-%m-%d")
                            except ValueError:
                                pass
                        break

                if not fecha:
                    continue

                img_el = card.select_one("img")
                imagen_url = img_el.get("src", "") if img_el else ""

                eventos.append({
                    "nombre_evento": titulo,
                    "fecha_evento": fecha,
                    "hora": "no especificado",
                    "lugar": "Expofuturo Pereira",
                    "ciudad": self.ciudad or "Pereira",
                    "categoria": "festival",
                    "descripcion": "",
                    "url_post": url,
                    "imagen_url": imagen_url,
                    "notas": "",
                })
            except Exception as e:
                logger.warning(f"Error parseando evento ExpoFuturo: {e}")

        return eventos
