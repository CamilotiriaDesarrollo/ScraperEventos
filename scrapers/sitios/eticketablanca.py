import logging
import re
from datetime import datetime

from scrapers.base_playwright import BasePlaywrightScraper

logger = logging.getLogger(__name__)

MESES_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}

# "1 de mayo de 2026" o "1 de mayo de 2026 - 2 de mayo de 2026"
RE_FECHA = re.compile(
    r"(\d{1,2})\s+de\s+([A-Za-zÁÉÍÓÚáéíóúñÑ]+)\s+de\s+(\d{4})",
    re.IGNORECASE,
)


class eTicketablancaScraper(BasePlaywrightScraper):
    BASE_URL = "https://www.eticketablanca.com"
    wait_selector = "article .card"
    extra_wait_ms = 3000

    def extraer_eventos(self):
        soup = self.fetch()
        if not soup:
            return []

        eventos = []
        hoy = datetime.now().date()
        vistos = set()

        for art in soup.select("article"):
            try:
                if not art.select_one(".card"):
                    continue

                titulo_a = art.select_one("h5 a")
                if not titulo_a:
                    continue
                titulo = titulo_a.get_text(" ", strip=True)
                if not titulo:
                    continue
                url = titulo_a.get("href", "")

                clave = (titulo.lower(), url)
                if clave in vistos:
                    continue
                vistos.add(clave)

                # Fecha está en un <span id="Date_..."> con texto tipo "1 de mayo de 2026"
                fecha_span = art.find("span", id=lambda v: v and v.startswith("Date_"))
                fecha = None
                if fecha_span:
                    fecha = self._extraer_fecha(fecha_span.get_text(" ", strip=True), hoy)
                if not fecha:
                    continue

                # Lugar en el span junto al icono bi-building
                lugar = ""
                ciudad = self.ciudad or "Bogotá"
                building_icon = art.select_one(".bi-building")
                if building_icon:
                    parent_p = building_icon.find_parent("p")
                    if parent_p:
                        texto_lugar = parent_p.get_text(" ", strip=True)
                        partes = [p.strip() for p in texto_lugar.split(",")]
                        partes = [p for p in partes if p]
                        if len(partes) >= 2:
                            lugar = partes[0]
                            ciudad = partes[-1]
                        elif partes:
                            lugar = partes[0]

                img_elem = art.select_one("img")
                imagen = img_elem.get("src", "") if img_elem else ""

                eventos.append({
                    "nombre_evento": titulo,
                    "fecha_evento": fecha,
                    "hora": "no especificado",
                    "lugar": lugar,
                    "ciudad": ciudad,
                    "categoria": "",
                    "descripcion": "",
                    "url_post": url,
                    "imagen_url": imagen,
                    "notas": "Boletería: eticketablanca.com",
                })
            except Exception as e:
                logger.warning(f"Error parseando item eTicketablanca: {e}")
                continue
        return eventos

    def _extraer_fecha(self, texto, hoy):
        m = RE_FECHA.search(texto)
        if not m:
            return None
        dia, mes_str, anio = m.groups()
        mes = MESES_ES.get(mes_str.lower().strip())
        if not mes:
            return None
        try:
            d = datetime(int(anio), mes, int(dia)).date()
        except ValueError:
            return None
        if d < hoy:
            return None
        return d.strftime("%Y-%m-%d")
