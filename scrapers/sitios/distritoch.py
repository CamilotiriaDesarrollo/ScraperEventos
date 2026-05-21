import logging
import re
from datetime import datetime

from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

BASE_URL = "https://distritoch.com"
CATEGORIES = [
    f"{BASE_URL}/categoria-evento/conciertos/",
    f"{BASE_URL}/categoria-evento/planes-en-bogota/",
    f"{BASE_URL}/categoria-evento/fiestas/",
]

MESES_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}

RE_FECHA = re.compile(r"(\w+)\s+(\d{1,2})[,\s]+(\d{4})", re.I)
RE_DIR = re.compile(r"(?:Cra\.?|Carrera|Calle|Cl\.?)\s+[\w#\s\-\.]+", re.I)

CATEGORIA_KW = {
    "concierto": "concierto",
    "música": "concierto",
    "musica": "concierto",
    "teatro": "teatro",
    "danza": "danza",
    "fiesta": "festival",
    "candlelight": "concierto",
    "jazz": "concierto",
    "rock": "concierto",
}


class DistritoCHScraper(BaseScraper):

    def extraer_eventos(self):
        event_urls = set()

        for cat_url in CATEGORIES:
            soup = self.fetch(cat_url)
            if not soup:
                continue
            for a in soup.find_all("a", href=re.compile(r"/evento/")):
                href = a.get("href", "")
                if href and "/categoria-evento/" not in href:
                    event_urls.add(href)

        hoy = datetime.now().date()
        eventos = []

        for url in event_urls:
            try:
                detail = self.fetch(url)
                if not detail:
                    continue

                og_title = detail.find("meta", property="og:title")
                titulo = og_title.get("content", "").strip() if og_title else ""
                for suffix in (" - Distrito CH", " - Agenda Cultural", " – Distrito CH"):
                    if titulo.endswith(suffix):
                        titulo = titulo[: -len(suffix)].strip()
                if not titulo:
                    h1 = detail.find("h1")
                    titulo = h1.get_text(strip=True) if h1 else ""
                if not titulo:
                    continue

                text = detail.get_text(" ", strip=True)
                m = RE_FECHA.search(text[:3000])
                if not m:
                    continue
                mes_str, dia_str, anio_str = m.groups()
                mes = MESES_ES.get(mes_str.lower())
                if not mes:
                    continue

                fecha_dt = datetime(int(anio_str), mes, int(dia_str)).date()
                if fecha_dt < hoy:
                    continue
                fecha = fecha_dt.strftime("%Y-%m-%d")

                dirs = RE_DIR.findall(text[:2000])
                lugar = dirs[0].split("Descripci")[0].strip().rstrip(".,;") if dirs else "Bogotá"

                img = detail.find("meta", property="og:image")
                imagen_url = img.get("content", "") if img else ""

                categoria = self._inferir_categoria(titulo)

                eventos.append({
                    "nombre_evento": titulo,
                    "fecha_evento": fecha,
                    "hora": "no especificado",
                    "lugar": lugar,
                    "ciudad": self.ciudad or "Bogotá",
                    "categoria": categoria,
                    "descripcion": "",
                    "url_post": url,
                    "imagen_url": imagen_url,
                    "notas": "",
                })
            except Exception as e:
                logger.warning(f"Error scrapeando evento DistritoCH {url}: {e}")

        return eventos

    def _inferir_categoria(self, titulo):
        titulo_low = titulo.lower()
        for kw, cat in CATEGORIA_KW.items():
            if kw in titulo_low:
                return cat
        return "concierto"
