import logging
import re
from datetime import datetime

from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

BASE_URL = "https://teatronacional.co"

MESES_ES = {
    "ENE": 1, "FEB": 2, "MAR": 3, "ABR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AGO": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DIC": 12,
}

# Ejemplo: "MIÉRCOLES 27 MAY 8:30PM" o "JUEVES 04 JUN 8:30PM"
RE_FECHA_BTN = re.compile(
    r"(?:[A-ZÁÉÍÓÚÑ]+)\s+(\d{1,2})\s+([A-Z]{3})\s+(\d{1,2}:\d{2})(AM|PM)",
    re.IGNORECASE,
)

# Dirección física: Calle, Carrera, Cra, Transversal
RE_DIR = re.compile(
    r"((?:Calle|Carrera|Cra|Transversal|Diagonal)\s+[\w\s#\-\.]+)",
    re.IGNORECASE,
)


class TeatroNacionalScraper(BaseScraper):

    def extraer_eventos(self):
        # Paso 1: Obtener lista de obras desde la homepage
        soup_home = self.fetch(BASE_URL)
        if not soup_home:
            return []

        show_links = {}
        for a in soup_home.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True)
            if (
                href.startswith(BASE_URL)
                and href.count("/") == 4
                and href != BASE_URL + "/"
                and text
                and len(text) > 2
                and not any(kw in href.lower() for kw in ["sobre", "beneficios", "formacion", "contacto", "proyecto"])
            ):
                show_links[href] = text

        eventos = []
        for url, titulo in show_links.items():
            try:
                soup = self.fetch(url)
                if not soup:
                    continue

                # Extraer todos los botones de función con fecha
                botones = soup.select("button.tc_seating_map_button")
                if not botones:
                    continue

                # Extraer dirección del venue desde el texto de la página
                texto_page = soup.get_text(" ", strip=True)
                dirs = RE_DIR.findall(texto_page)
                lugar = dirs[0].strip() if dirs else "Teatro Nacional"

                for btn in botones:
                    btn_text = btn.get_text(strip=True)
                    # Ignorar agotados si no tienen fecha parseable
                    m = RE_FECHA_BTN.search(btn_text.upper())
                    if not m:
                        continue
                    dia, mes_str, hora_raw, ampm = m.groups()
                    mes = MESES_ES.get(mes_str.upper())
                    if not mes:
                        continue
                    fecha = self._construir_fecha(int(dia), mes)
                    if not fecha:
                        continue

                    hora = f"{hora_raw} {ampm.upper()}"

                    eventos.append({
                        "nombre_evento": titulo,
                        "fecha_evento": fecha,
                        "hora": hora,
                        "lugar": lugar,
                        "ciudad": self.ciudad or "Bogotá",
                        "categoria": "teatro",
                        "descripcion": "",
                        "url_post": url,
                        "imagen_url": "",
                        "notas": "",
                    })
            except Exception as e:
                logger.warning(f"Error scrapeando obra Teatro Nacional {url}: {e}")
                continue

        return eventos

    def _construir_fecha(self, dia, mes):
        hoy = datetime.now().date()
        for anio in (hoy.year, hoy.year + 1):
            try:
                candidato = datetime(anio, mes, dia).date()
            except ValueError:
                return None
            if candidato >= hoy:
                return candidato.strftime("%Y-%m-%d")
        return None
