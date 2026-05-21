import logging
import re
from datetime import datetime

from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

BASE_URL = "https://cinematecadebogota.gov.co"
AGENDA_URL = "https://cinematecadebogota.gov.co/agenda/11"

MESES_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}

RE_FECHA = re.compile(
    r"([A-Za-záéíóúÁÉÍÓÚñÑ]+)\s+(\d{1,2})",
    re.IGNORECASE,
)

CATEGORIA_MAP = {
    "estrenos nacionales": "cine",
    "festivales y muestras": "cine",
    "vive la cinemateca": "cine",
    "matinée persona mayor": "cine",
    "que haiga paz": "cine",
    "primera infancia": "cine",
    "ciclo": "cine",
    "retrospectiva": "cine",
}


class CinematecaScraper(BaseScraper):

    def extraer_eventos(self):
        soup = self.fetch(AGENDA_URL)
        if not soup:
            return []

        eventos = []
        seen = set()

        for item in soup.select(".views-view-responsive-grid__item"):
            try:
                titulo_a = item.select_one(".views-field-title a")
                if not titulo_a:
                    continue
                titulo = titulo_a.get_text(strip=True)
                if not titulo or titulo in seen:
                    continue
                seen.add(titulo)

                href = titulo_a.get("href", "")
                url = href if href.startswith("http") else f"{BASE_URL}{href}"

                cat_elem = item.select_one(".views-field-field-taxonomy-1 .field-content")
                cat_raw = cat_elem.get_text(strip=True).lower() if cat_elem else ""
                categoria = CATEGORIA_MAP.get(cat_raw, "cine")

                fecha_elem = item.select_one(".funcion-fecha")
                hora_elem = item.select_one(".funcion-hora")
                sala_elem = item.select_one(".funcion-sala")

                fecha_txt = fecha_elem.get_text(strip=True) if fecha_elem else ""
                hora = hora_elem.get_text(strip=True) if hora_elem else "no especificado"
                sala = sala_elem.get_text(strip=True) if sala_elem else "Cinemateca de Bogotá"

                fecha = self._parsear_fecha(fecha_txt)
                if not fecha:
                    continue

                img_elem = item.select_one("img")
                imagen_url = ""
                if img_elem:
                    src = img_elem.get("src", "")
                    imagen_url = src if src.startswith("http") else f"{BASE_URL}{src}"

                eventos.append({
                    "nombre_evento": titulo,
                    "fecha_evento": fecha,
                    "hora": hora,
                    "lugar": sala,
                    "ciudad": self.ciudad or "Bogotá",
                    "categoria": categoria,
                    "descripcion": "",
                    "url_post": url,
                    "imagen_url": imagen_url,
                    "notas": "",
                })
            except Exception as e:
                logger.warning(f"Error parseando item en Cinemateca: {e}")
                continue

        return eventos

    def _parsear_fecha(self, texto):
        m = RE_FECHA.search(texto)
        if not m:
            return None
        mes_str, dia_str = m.group(1).lower(), m.group(2)
        mes = MESES_ES.get(mes_str)
        if not mes:
            return None
        try:
            dia = int(dia_str)
        except ValueError:
            return None
        hoy = datetime.now().date()
        for anio in (hoy.year, hoy.year + 1):
            try:
                candidato = datetime(anio, mes, dia).date()
            except ValueError:
                return None
            if candidato >= hoy:
                return candidato.strftime("%Y-%m-%d")
        return None
