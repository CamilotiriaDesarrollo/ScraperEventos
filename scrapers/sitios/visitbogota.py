import logging
import re
from datetime import datetime

from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

MES_EN = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
          "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
MES_ES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
          "jul": 7, "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12}

# "May 03" o "May 03 - May 05" o "Mayo 03"
RE_MES_DIA = re.compile(r"\b([A-Za-zÁÉÍÓÚáéíóúñÑ]{3,9})\s*(\d{1,2})\b")


class VisitBogotaScraper(BaseScraper):
    BASE_URL = "https://visitbogota.co"
    AGENDA_URL = "https://visitbogota.co/es/agenda-de-eventos"

    def extraer_eventos(self):
        soup = self.fetch(self.AGENDA_URL)
        if not soup:
            return []

        eventos = []
        hoy = datetime.now().date()
        vistos = set()

        for li in soup.select("li.card, .card"):
            try:
                a = li.select_one("a[href*='/agenda-de-eventos/']")
                if not a:
                    continue
                href = a.get("href", "")
                url = self._absolutizar(href)
                if url == self.AGENDA_URL or url.rstrip("/") == self.AGENDA_URL.rstrip("/"):
                    continue

                titulo_elem = a.select_one(".event-info .title, .title")
                if not titulo_elem:
                    continue
                titulo = titulo_elem.get_text(" ", strip=True)
                if not titulo:
                    continue

                clave = (titulo.lower(), url)
                if clave in vistos:
                    continue
                vistos.add(clave)

                fecha_elem = a.select_one(".event-info .date, .date")
                fecha = None
                if fecha_elem:
                    fecha = self._extraer_fecha(fecha_elem.get_text(" ", strip=True), hoy)
                if not fecha:
                    continue

                lugar_elem = a.select_one(".event-info .place, .place")
                lugar = lugar_elem.get_text(" ", strip=True) if lugar_elem else ""

                img_elem = a.select_one("img[src]")
                imagen = ""
                if img_elem:
                    src = img_elem.get("src", "")
                    if src.startswith("http"):
                        imagen = src
                    elif src.startswith("/"):
                        imagen = self.BASE_URL + src

                eventos.append({
                    "nombre_evento": titulo,
                    "fecha_evento": fecha,
                    "hora": "no especificado",
                    "lugar": lugar,
                    "ciudad": self.ciudad or "Bogotá",
                    "categoria": "",
                    "descripcion": "",
                    "url_post": url,
                    "imagen_url": imagen,
                    "notas": "Visit Bogotá",
                })
            except Exception as e:
                logger.warning(f"Error parseando item Visit Bogotá: {e}")
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
            return None
        m = RE_MES_DIA.search(texto)
        if not m:
            return None
        mes_str, dia_str = m.groups()
        mes = MES_EN.get(mes_str[:3].lower()) or MES_ES.get(mes_str[:3].lower())
        if not mes:
            return None
        try:
            dia = int(dia_str)
        except ValueError:
            return None
        for anio in (hoy.year, hoy.year + 1):
            try:
                d = datetime(anio, mes, dia).date()
            except ValueError:
                return None
            if d >= hoy:
                return d.strftime("%Y-%m-%d")
        return None
