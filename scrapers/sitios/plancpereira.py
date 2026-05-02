import logging
from datetime import datetime

from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

MESES_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}

# Plan C usa hashtags como #MúsicaC, #LiteraturaC, etc.
ETIQUETA_MAP = {
    "musicac": "concierto",
    "musica": "concierto",
    "teatroc": "teatro",
    "teatro": "teatro",
    "danzac": "danza",
    "danza": "danza",
    "literaturac": "conversatorio",
    "literatura": "conversatorio",
    "cinec": "cine",
    "cine": "cine",
    "gastronomiac": "gastronomia",
    "gastronomia": "gastronomia",
    "artec": "exposicion",
    "arte": "exposicion",
    "plasticasc": "exposicion",
    "fiestac": "fiesta",
    "fiesta": "fiesta",
    "festivalc": "festival",
    "festival": "festival",
    "tallerc": "taller",
    "taller": "taller",
}


class PlanCPereiraScraper(BaseScraper):
    BASE_URL = "https://plancpereira.com"
    AGENDA_URL = "https://plancpereira.com/"

    def extraer_eventos(self):
        soup = self.fetch(self.AGENDA_URL)
        if not soup:
            return []

        eventos = []
        hoy = datetime.now().date()
        vistos = set()

        for li in soup.select(".slider-agenda ul.slides > li"):
            try:
                titulo_a = li.select_one(".content-list-entrada h4 a")
                if not titulo_a:
                    continue
                titulo = titulo_a.get_text(strip=True)
                if not titulo:
                    continue
                url = titulo_a.get("href", "") or self.AGENDA_URL

                dia_elem = li.select_one(".span-dia-numero")
                mes_elem = li.select_one(".span-mes-texto")
                if not (dia_elem and mes_elem):
                    continue
                fecha = self._construir_fecha(
                    dia_elem.get_text(strip=True),
                    mes_elem.get_text(strip=True),
                    hoy,
                )
                if not fecha:
                    continue

                clave = (titulo.lower(), fecha)
                if clave in vistos:
                    continue
                vistos.add(clave)

                hora_elem = li.select_one(".span-hora")
                hora = hora_elem.get_text(strip=True) if hora_elem else ""
                hora = hora.upper().replace(".", "").strip() if hora else "no especificado"

                etiqueta_a = li.select_one(".span-etiqueta a")
                categoria = ""
                if etiqueta_a:
                    raw = etiqueta_a.get_text(strip=True).lstrip("#").lower()
                    categoria = ETIQUETA_MAP.get(raw, "")

                img_elem = li.select_one("img[data-src], img[src]")
                imagen = ""
                if img_elem:
                    src = img_elem.get("data-src", "") or img_elem.get("src", "")
                    if src.startswith("http") and not src.startswith("data:"):
                        imagen = src

                eventos.append({
                    "nombre_evento": titulo,
                    "fecha_evento": fecha,
                    "hora": hora,
                    "lugar": "Pereira",
                    "ciudad": self.ciudad or "Pereira",
                    "categoria": categoria,
                    "descripcion": "",
                    "url_post": url,
                    "imagen_url": imagen,
                })
            except Exception as e:
                logger.warning(f"Error parseando item Plan C Pereira: {e}")
                continue
        return eventos

    def _construir_fecha(self, dia_str, mes_str, hoy):
        mes = MESES_ES.get(mes_str.lower().strip())
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
