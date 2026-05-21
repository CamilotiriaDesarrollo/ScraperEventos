import logging
import re
from datetime import datetime

from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

EVENTOS_URL = "https://comfamiliar.com/eventos/"

MESES = {
    "ene": 1, "enero": 1,
    "feb": 2, "febrero": 2,
    "mar": 3, "marzo": 3,
    "abr": 4, "abril": 4,
    "may": 5, "mayo": 5,
    "jun": 6, "junio": 6,
    "jul": 7, "julio": 7,
    "ago": 8, "agosto": 8,
    "sep": 9, "septiembre": 9,
    "oct": 10, "octubre": 10,
    "nov": 11, "noviembre": 11,
    "dic": 12, "diciembre": 12,
}

RE_FECHA = re.compile(
    r"(\d{1,2})\s+([A-Za-záéíóú]{3,})\.?\s+(\d{4})",
    re.I,
)


class ComfamiliarScraper(BaseScraper):

    def extraer_eventos(self):
        soup = self.fetch(EVENTOS_URL)
        if not soup:
            return []

        hoy = datetime.now().date()
        eventos = []

        for card in soup.select(".jet-listing-grid__item"):
            try:
                btn = card.select_one("a.elementor-button[href*='/eventos/']")
                if not btn:
                    continue
                url = btn.get("href", "")
                if not url or "/categoria-eventos/" in url:
                    continue

                fields = card.select(".jet-listing-dynamic-field__content")
                if len(fields) < 5:
                    continue

                day_num_txt = fields[1].get_text(strip=True)
                month_year_txt = fields[2].get_text(strip=True)
                titulo = fields[3].get_text(strip=True)
                lugar = fields[4].get_text(strip=True)

                full_date_txt = f"{day_num_txt} {month_year_txt}"
                m = RE_FECHA.search(full_date_txt)
                if not m:
                    continue
                dia_str, mes_str, anio_str = m.groups()
                mes = MESES.get(mes_str.lower()[:3])
                if not mes:
                    mes = MESES.get(mes_str.lower())
                if not mes:
                    continue

                fecha_dt = datetime(int(anio_str), mes, int(dia_str)).date()
                if fecha_dt < hoy:
                    continue
                fecha = fecha_dt.strftime("%Y-%m-%d")

                img_el = card.select_one("img")
                imagen_url = img_el.get("src", "") if img_el else ""

                eventos.append({
                    "nombre_evento": titulo,
                    "fecha_evento": fecha,
                    "hora": "no especificado",
                    "lugar": lugar,
                    "ciudad": self.ciudad or "Pereira",
                    "categoria": "",
                    "descripcion": "",
                    "url_post": url,
                    "imagen_url": imagen_url,
                    "notas": "",
                })
            except Exception as e:
                logger.warning(f"Error parseando evento Comfamiliar: {e}")

        return eventos
