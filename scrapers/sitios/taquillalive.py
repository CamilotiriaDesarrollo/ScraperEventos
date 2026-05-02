import logging
import re
from datetime import datetime

from scrapers.base_playwright import BasePlaywrightScraper

logger = logging.getLogger(__name__)

MES_EN = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
          "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
MES_ES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
          "jul": 7, "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12}

RE_FECHA = re.compile(r"\b([A-Za-zÁÉÍÓÚáéíóú]{3,9})\s+(\d{1,2})\b")
RE_HORA = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm|AM|PM)")


class TaquillaLiveScraper(BasePlaywrightScraper):
    BASE_URL = "https://www.taquillalive.com"
    AGENDA_URL = "https://www.taquillalive.com/eventos-y-boleteria/"
    wait_selector = ".filter-ticket-info"
    extra_wait_ms = 3500

    def extraer_eventos(self):
        target = self.url or self.AGENDA_URL
        if "/eventos-y-boleteria" not in target:
            target = self.AGENDA_URL
        soup = self.fetch(target)
        if not soup:
            return []

        eventos = []
        hoy = datetime.now().date()
        vistos = set()

        for caja in soup.select(".filter-ticket-info"):
            try:
                titulo_a = caja.select_one(".filter-ticket-detail h6 a")
                if not titulo_a:
                    continue
                titulo = titulo_a.get_text(" ", strip=True)
                if not titulo:
                    continue
                url = titulo_a.get("href", "")
                if not url.startswith("http"):
                    url = self.BASE_URL + url if url.startswith("/") else self.BASE_URL + "/" + url

                clave = (titulo.lower(), url)
                if clave in vistos:
                    continue
                vistos.add(clave)

                lugar_elem = caja.select_one(".distance-info p")
                lugar = ""
                if lugar_elem:
                    lugar = lugar_elem.get_text(" ", strip=True)
                    lugar = re.sub(r"^\s*", "", lugar)

                fecha_block = caja.select(".event-date-time p")
                fecha = None
                hora = None
                for p in fecha_block:
                    txt = p.get_text(" ", strip=True)
                    if not fecha:
                        fecha = self._extraer_fecha(txt, hoy)
                    if not hora:
                        m = RE_HORA.search(txt)
                        if m:
                            h, mm, ampm = m.groups()
                            hora = f"{int(h)}:{mm or '00'} {ampm.upper()}"
                if not fecha:
                    continue

                img_elem = caja.select_one(".filter-ticket-img img[src]")
                imagen = img_elem.get("src", "") if img_elem else ""

                eventos.append({
                    "nombre_evento": titulo,
                    "fecha_evento": fecha,
                    "hora": hora or "no especificado",
                    "lugar": lugar,
                    "ciudad": self.ciudad or "Bogotá",
                    "categoria": "",
                    "descripcion": "",
                    "url_post": url,
                    "imagen_url": imagen,
                    "notas": "Boletería: taquillalive.com",
                })
            except Exception as e:
                logger.warning(f"Error parseando item TaquillaLive: {e}")
                continue
        return eventos

    def _extraer_fecha(self, texto, hoy):
        if not texto:
            return None
        m = RE_FECHA.search(texto)
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
