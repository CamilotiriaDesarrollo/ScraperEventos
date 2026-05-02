import logging
import re
from datetime import datetime

from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

# Categorías inferidas del path URL del evento (/es/evento/<categoria>/<slug>)
CATEGORIA_PATH_MAP = {
    "musica": "concierto",
    "teatro": "teatro",
    "danza": "danza",
    "circo": "festival",
    "opera": "concierto",
    "jazz": "concierto",
    "sinfonica": "concierto",
}

RE_HORA = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*(AM|PM|am|pm|a\.?m\.?|p\.?m\.?)")


class TeatroMayorScraper(BaseScraper):
    BASE_URL = "https://www.teatromayor.org"
    AGENDA_URL = "https://www.teatromayor.org/"

    def extraer_eventos(self):
        soup = self.fetch(self.AGENDA_URL)
        if not soup:
            return []

        eventos = []
        hoy = datetime.now().date()
        for row in soup.select(".views-row"):
            try:
                titulo_a = (
                    row.select_one(".views-field-title a")
                    or row.select_one(".views-field-field-title a")
                    or row.select_one("a[title]")
                )
                if not titulo_a:
                    continue
                titulo = titulo_a.get_text(strip=True) or titulo_a.get("title", "")
                if not titulo:
                    continue
                href = titulo_a.get("href", "")
                url = self._absolutizar(href)

                fecha_elem = row.select_one(".date-display-single")
                if not fecha_elem:
                    continue
                iso = fecha_elem.get("content", "")
                if not iso:
                    continue
                fecha = iso[:10]
                try:
                    fd = datetime.strptime(fecha, "%Y-%m-%d").date()
                except ValueError:
                    continue
                if fd < hoy:
                    continue

                hora = None
                m = RE_HORA.search(fecha_elem.get_text(" ", strip=True))
                if m:
                    h, mm, ampm = m.groups()
                    hora = f"{int(h)}:{mm or '00'} {ampm.replace('.', '').upper()}"

                categoria = ""
                href_low = href.lower()
                for clave, cat in CATEGORIA_PATH_MAP.items():
                    if f"/{clave}/" in href_low or f"/{clave}-" in href_low:
                        categoria = cat
                        break

                imagen = ""
                src_elem = row.select_one("source[srcset]") or row.select_one("img[src]")
                if src_elem is not None:
                    if src_elem.has_attr("srcset"):
                        imagen = src_elem["srcset"].split()[0]
                    else:
                        imagen = src_elem.get("src", "")

                eventos.append({
                    "nombre_evento": titulo,
                    "fecha_evento": fecha,
                    "hora": hora or "no especificado",
                    "lugar": "Teatro Mayor JMSD",
                    "ciudad": self.ciudad or "Bogotá",
                    "categoria": categoria,
                    "descripcion": "",
                    "url_post": url,
                    "imagen_url": imagen,
                })
            except Exception as e:
                logger.warning(f"Error parseando item Teatro Mayor: {e}")
                continue
        return eventos

    def _absolutizar(self, href):
        if not href:
            return ""
        if href.startswith("http"):
            return href
        if href.startswith("/"):
            return self.BASE_URL + href
        return ""
