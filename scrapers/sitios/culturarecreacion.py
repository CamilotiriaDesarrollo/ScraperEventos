import logging
from datetime import datetime

from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

BASE_URL = "https://culturarecreacionydeporte.gov.co"
AGENDA_URL = f"{BASE_URL}/agenda"

CATEGORIA_KW = {
    "teatro": "teatro",
    "danza": "danza",
    "música": "concierto",
    "musica": "concierto",
    "concierto": "concierto",
    "exposición": "exposicion",
    "exposicion": "exposicion",
    "cine": "cine",
    "taller": "taller",
    "festival": "festival",
    "ballet": "danza",
}


class CulturaRecreacionScraper(BaseScraper):

    def extraer_eventos(self):
        soup = self.fetch(AGENDA_URL)
        if not soup:
            return []

        hoy = datetime.now().date()
        eventos = []

        for art in soup.select("article.node--type-event"):
            try:
                title_el = art.select_one("h2 a, h3 a")
                if not title_el:
                    continue
                titulo = title_el.get_text(strip=True)
                if not titulo:
                    continue

                url_rel = title_el.get("href", "")
                url = f"{BASE_URL}{url_rel}" if url_rel.startswith("/") else url_rel

                time_els = art.select("time[datetime]")
                if not time_els:
                    continue
                start_str = time_els[0].get("datetime", "")[:10]
                if not start_str:
                    continue

                start_dt = datetime.strptime(start_str, "%Y-%m-%d").date()
                # Use end date if available; otherwise end == start
                end_str = time_els[-1].get("datetime", "")[:10] if len(time_els) > 1 else start_str
                end_dt = datetime.strptime(end_str, "%Y-%m-%d").date() if end_str else start_dt

                if end_dt < hoy:
                    continue
                fecha = start_dt.strftime("%Y-%m-%d")

                desc_el = art.select_one(".field--name-body, .field--name-field-description, p")
                desc = desc_el.get_text(" ", strip=True)[:200] if desc_el else ""

                categoria = self._inferir_categoria(titulo + " " + desc)

                img_el = art.select_one("img")
                imagen_url = ""
                if img_el:
                    src = img_el.get("src", "")
                    imagen_url = src if src.startswith("http") else f"{BASE_URL}{src}"

                eventos.append({
                    "nombre_evento": titulo,
                    "fecha_evento": fecha,
                    "hora": "no especificado",
                    "lugar": "Bogotá",
                    "ciudad": self.ciudad or "Bogotá",
                    "categoria": categoria,
                    "descripcion": desc,
                    "url_post": url,
                    "imagen_url": imagen_url,
                    "notas": "",
                })
            except Exception as e:
                logger.warning(f"Error parseando evento CRD: {e}")

        return eventos

    def _inferir_categoria(self, texto):
        texto_low = texto.lower()
        for kw, cat in CATEGORIA_KW.items():
            if kw in texto_low:
                return cat
        return "teatro"
