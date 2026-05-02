import logging
import re
from datetime import datetime

from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

MESES_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}

# "3 de Mayo - 10:00 AM"
RE_FECHA_HORA = re.compile(
    r"(\d{1,2})\s+de\s+([A-Za-zÁÉÍÓÚáéíóúñÑ]+)\s*[-–]?\s*"
    r"(?:(\d{1,2})(?::(\d{2}))?\s*(AM|PM|am|pm|a\.?m\.?|p\.?m\.?))?",
    re.IGNORECASE,
)


class PlanetarioScraper(BaseScraper):
    BASE_URL = "https://planetariodebogota.gov.co"
    AGENDA_URL = "https://planetariodebogota.gov.co/"

    def extraer_eventos(self):
        soup = self.fetch(self.AGENDA_URL)
        if not soup:
            return []

        eventos = []
        hoy = datetime.now().date()
        vistos = set()

        for row in soup.select(".views-row"):
            try:
                box = row.select_one(".box-ev") or row
                titulo_a = box.select_one(".box-ev-tit h2 a, .box-ev-tit a")
                if not titulo_a:
                    continue
                titulo = titulo_a.get_text(" ", strip=True)
                if not titulo:
                    continue
                href = titulo_a.get("href", "")
                url = self._absolutizar(href)

                clave = (titulo.lower(), url)
                if clave in vistos:
                    continue
                vistos.add(clave)

                fecha_elem = box.select_one(".box-ev-date")
                if not fecha_elem:
                    continue
                fecha, hora = self._extraer_fecha(fecha_elem.get_text(" ", strip=True), hoy)
                if not fecha:
                    continue

                img_elem = box.select_one("img[src]")
                imagen = ""
                if img_elem:
                    imagen = self._absolutizar(img_elem.get("src", ""))

                eventos.append({
                    "nombre_evento": titulo,
                    "fecha_evento": fecha,
                    "hora": hora or "no especificado",
                    "lugar": "Planetario de Bogotá",
                    "ciudad": self.ciudad or "Bogotá",
                    "categoria": "",
                    "descripcion": "",
                    "url_post": url,
                    "imagen_url": imagen,
                    "notas": "Planetario de Bogotá",
                })
            except Exception as e:
                logger.warning(f"Error parseando item Planetario: {e}")
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

    def _extraer_fecha(self, texto, hoy):
        if not texto:
            return None, None
        m = RE_FECHA_HORA.search(texto)
        if not m:
            return None, None
        dia_str, mes_str, h, mm, ampm = m.groups()
        mes = MESES_ES.get(mes_str.lower().strip())
        if not mes:
            return None, None
        try:
            dia = int(dia_str)
        except ValueError:
            return None, None

        fecha_iso = None
        for anio in (hoy.year, hoy.year + 1):
            try:
                d = datetime(anio, mes, dia).date()
            except ValueError:
                return None, None
            if d >= hoy:
                fecha_iso = d.strftime("%Y-%m-%d")
                break
        if not fecha_iso:
            return None, None

        hora = None
        if h and ampm:
            hora = f"{int(h)}:{mm or '00'} {ampm.replace('.', '').upper()}"
        return fecha_iso, hora
