import logging
from datetime import datetime
from html import unescape

from bs4 import BeautifulSoup

from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

API_URL = "https://eneldelia.gov.co/wp-json/tribe/events/v1/events"

CATEGORIA_MAP = {
    "teatro": "teatro",
    "danza": "danza",
    "música": "concierto",
    "musica": "concierto",
    "concierto": "concierto",
    "exposición": "exposicion",
    "exposicion": "exposicion",
    "cine": "cine",
    "taller": "taller",
    "conversatorio": "conversatorio",
    "festival": "festival",
    "lanzamiento": "lanzamiento",
    "familiar": "taller",
}


class EnDeldiaScraper(BaseScraper):

    def extraer_eventos(self):
        todos = []
        page = 1
        while True:
            try:
                resp = self.session.get(
                    API_URL,
                    params={"per_page": 50, "page": page, "status": "publish"},
                    timeout=15,
                    verify=False,
                )
                if resp.status_code != 200:
                    break
                data = resp.json()
                events = data.get("events", [])
                if not events:
                    break
                todos.extend(events)
                # Si hay menos de 50 resultados, no hay más páginas
                if len(events) < 50:
                    break
                page += 1
            except Exception as e:
                logger.warning(f"Error al pedir página {page} de Eneldelia API: {e}")
                break

        hoy = datetime.now().date()
        eventos = []
        for ev in todos:
            try:
                start_raw = ev.get("start_date", "")
                if not start_raw:
                    continue
                fecha_dt = datetime.strptime(start_raw[:10], "%Y-%m-%d").date()
                if fecha_dt < hoy:
                    continue
                fecha = fecha_dt.strftime("%Y-%m-%d")

                hora_str = start_raw[11:16] if len(start_raw) > 10 else "no especificado"
                if hora_str == "00:00":
                    hora_str = "no especificado"

                titulo = unescape(ev.get("title", "")).strip()
                if not titulo:
                    continue

                url = ev.get("url", "")

                venue = ev.get("venue") or {}
                if isinstance(venue, list):
                    venue = venue[0] if venue else {}
                lugar = venue.get("venue", "") or "Centro Nacional de las Artes Delia Zapata Olivella"

                cats = [c.get("name", "") for c in ev.get("categories", [])]
                categoria = self._normalizar_categoria(cats)

                img = ev.get("image") or {}
                imagen_url = img.get("url", "") if isinstance(img, dict) else ""
                if imagen_url and not imagen_url.startswith("http"):
                    imagen_url = f"https://eneldelia.gov.co{imagen_url}"

                desc = ev.get("excerpt", "")
                if desc:
                    desc = BeautifulSoup(desc, "html.parser").get_text(" ", strip=True)[:200]

                eventos.append({
                    "nombre_evento": titulo,
                    "fecha_evento": fecha,
                    "hora": hora_str,
                    "lugar": lugar,
                    "ciudad": self.ciudad or "Bogotá",
                    "categoria": categoria,
                    "descripcion": desc,
                    "url_post": url,
                    "imagen_url": imagen_url,
                    "notas": "",
                })
            except Exception as e:
                logger.warning(f"Error parseando evento Eneldelia: {e}")
                continue

        return eventos

    def _normalizar_categoria(self, cats):
        for cat in cats:
            key = cat.strip().lower()
            if key in CATEGORIA_MAP:
                return CATEGORIA_MAP[key]
            for k, v in CATEGORIA_MAP.items():
                if k in key:
                    return v
        return "teatro"
