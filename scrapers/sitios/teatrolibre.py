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


class TeatroLibreScraper(BaseScraper):
    BASE_URL = "https://teatrolibre.com"
    AGENDA_URL = "https://teatrolibre.com/"

    def extraer_eventos(self):
        soup = self.fetch(self.AGENDA_URL)
        if not soup:
            return []

        eventos = []
        hoy = datetime.now().date()
        for funcion in soup.select(".funcion"):
            try:
                titulo_a = funcion.select_one("h2.elementor-heading-title a")
                if not titulo_a:
                    titulo_a = funcion.select_one("h2 a")
                if not titulo_a:
                    continue
                titulo = titulo_a.get_text(strip=True)
                if not titulo:
                    continue
                url = titulo_a.get("href", "")

                lugar = "Teatro Libre"
                fecha_texto = ""
                for item in funcion.select(".elementor-icon-list-item"):
                    icon = item.select_one("i")
                    txt_elem = item.select_one(".elementor-icon-list-text")
                    if not (icon and txt_elem):
                        continue
                    icon_class = " ".join(icon.get("class", []))
                    txt = txt_elem.get_text(" ", strip=True)
                    if "marker" in icon_class or "map" in icon_class:
                        lugar = txt or lugar
                    elif "calendar" in icon_class:
                        fecha_texto = txt

                fecha = self._proxima_fecha(fecha_texto, hoy)
                if not fecha:
                    continue

                desc_elem = funcion.select_one(".elementor-widget-theme-post-excerpt p")
                descripcion = desc_elem.get_text(strip=True) if desc_elem else ""

                img_elem = funcion.select_one("img[src]")
                imagen = img_elem.get("src", "") if img_elem else ""

                eventos.append({
                    "nombre_evento": titulo,
                    "fecha_evento": fecha,
                    "hora": "no especificado",
                    "lugar": lugar,
                    "ciudad": self.ciudad or "Bogotá",
                    "categoria": "teatro",
                    "descripcion": descripcion[:200],
                    "url_post": url,
                    "imagen_url": imagen,
                })
            except Exception as e:
                logger.warning(f"Error parseando item Teatro Libre: {e}")
                continue
        return eventos

    def _proxima_fecha(self, texto, hoy):
        if not texto:
            return None
        m = re.search(r"de\s+([A-Za-zÁÉÍÓÚáéíóúñÑ]+)", texto, re.IGNORECASE)
        if not m:
            return None
        mes = MESES_ES.get(m.group(1).lower().strip())
        if not mes:
            return None
        dias = [int(d) for d in re.findall(r"\d+", texto[:m.start()])]
        if not dias:
            return None
        for anio in (hoy.year, hoy.year + 1):
            for dia in dias:
                try:
                    candidato = datetime(anio, mes, dia).date()
                except ValueError:
                    continue
                if candidato >= hoy:
                    return candidato.strftime("%Y-%m-%d")
        return None
