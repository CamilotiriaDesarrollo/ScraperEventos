import logging
from datetime import datetime

from scrapers.base_playwright import BasePlaywrightScraper

logger = logging.getLogger(__name__)

MESES_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
    "jul": 7, "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12,
}


class TuBoletaScraper(BasePlaywrightScraper):
    BASE_URL = "https://tuboleta.com"
    wait_selector = "a.content-link-container, .card-element"
    extra_wait_ms = 2000

    def extraer_eventos(self):
        soup = self.fetch()
        if not soup:
            return []

        eventos = []
        hoy = datetime.now().date()
        vistos = set()

        for card in soup.select("a.content-link-container"):
            try:
                href = card.get("href", "")
                if not href:
                    continue
                url = self._absolutizar(href)

                info = card.select_one(".content-info")
                if not info:
                    continue
                spans = [s.get_text(" ", strip=True) for s in info.select("span")]
                spans = [s for s in spans if s]
                if not spans:
                    continue
                titulo = spans[0]
                if not titulo:
                    continue
                lugar = spans[1] if len(spans) > 1 else ""
                ciudad = spans[2] if len(spans) > 2 else (self.ciudad or "")

                fecha_div = card.select_one(".content-date")
                fecha = self._extraer_fecha(fecha_div, hoy) if fecha_div else None
                if not fecha:
                    continue

                clave = (titulo.lower(), fecha)
                if clave in vistos:
                    continue
                vistos.add(clave)

                img = card.select_one("img[src]")
                imagen = ""
                if img:
                    src = img.get("src", "")
                    imagen = self._absolutizar(src)

                eventos.append({
                    "nombre_evento": titulo,
                    "fecha_evento": fecha,
                    "hora": "no especificado",
                    "lugar": lugar,
                    "ciudad": ciudad or self.ciudad or "Bogotá",
                    "categoria": "",
                    "descripcion": "",
                    "url_post": url,
                    "imagen_url": imagen,
                    "notas": "Boletería: tuboleta.com",
                })
            except Exception as e:
                logger.warning(f"Error parseando item TuBoleta: {e}")
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

    def _extraer_fecha(self, fecha_div, hoy):
        spans = [s.get_text(" ", strip=True) for s in fecha_div.select("span")]
        spans = [s for s in spans if s]
        if not spans:
            return None
        # "01" "Mayo" "Vie" "01 Mayo"
        dia_str = ""
        mes_str = ""
        for s in spans:
            partes = s.split()
            if len(partes) == 2 and partes[0].isdigit():
                dia_str = partes[0]
                mes_str = partes[1]
                break
            if s.isdigit() and not dia_str:
                dia_str = s
            elif s.lower().strip(".") in MESES_ES and not mes_str:
                mes_str = s
        if not (dia_str and mes_str):
            return None
        try:
            dia = int(dia_str)
        except ValueError:
            return None
        mes = MESES_ES.get(mes_str.lower().strip("."))
        if not mes:
            return None
        for anio in (hoy.year, hoy.year + 1):
            try:
                d = datetime(anio, mes, dia).date()
            except ValueError:
                return None
            if d >= hoy:
                return d.strftime("%Y-%m-%d")
        return None
