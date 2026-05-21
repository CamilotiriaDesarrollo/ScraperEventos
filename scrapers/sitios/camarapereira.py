import logging
import re
from datetime import datetime

from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

BASE_URL = "https://camarapereira.org.co"
AGENDA_URL = f"{BASE_URL}/es/ieventoscece/detalle/"

MESES_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}

RE_FECHA = re.compile(r"(\d{1,2})\s+de\s+(\w+)\s+(\d{4})", re.I)
RE_FECHA_RANGO = re.compile(r"[Dd]el?\s+(\d{1,2})\s+al?\s+\d{1,2}\s+de\s+(\w+)(?:\s+(\d{4}))?", re.I)


class CamaraPereiraScraper(BaseScraper):

    def extraer_eventos(self):
        soup = self.fetch(f"{BASE_URL}/es/ieventoscece/")
        if not soup:
            return []

        hoy = datetime.now().date()
        eventos = []
        seen = set()

        for art in soup.select("article"):
            try:
                a = art.select_one("a[href]")
                if not a:
                    continue
                href = a.get("href", "")
                if not href or href in seen:
                    continue
                seen.add(href)

                url = f"{BASE_URL}{href}" if href.startswith("/") else href

                titulo_el = art.select_one(".titulo-evento-list")
                if not titulo_el:
                    continue
                titulo = titulo_el.get_text(strip=True)
                if not titulo:
                    continue

                # Date text is in the divs inside panel-body
                panel = art.select_one(".panel-body")
                fecha = None
                fecha_text = ""
                if panel:
                    divs = panel.find_all("div", recursive=False)
                    for div in divs:
                        text = div.get_text(strip=True)
                        m = RE_FECHA.search(text)
                        if m:
                            dia, mes_str, anio = m.groups()
                            mes = MESES_ES.get(mes_str.lower())
                            if mes:
                                try:
                                    dt = datetime(int(anio), mes, int(dia)).date()
                                    if dt >= hoy:
                                        fecha = dt.strftime("%Y-%m-%d")
                                        fecha_text = text
                                except ValueError:
                                    pass
                            break
                        # Range: "Del 2 al 4 de junio"
                        mr = RE_FECHA_RANGO.search(text)
                        if mr:
                            dia, mes_str, anio_str = mr.groups()
                            mes = MESES_ES.get(mes_str.lower())
                            anio = int(anio_str) if anio_str else hoy.year
                            if mes:
                                try:
                                    dt = datetime(anio, mes, int(dia)).date()
                                    if dt >= hoy:
                                        fecha = dt.strftime("%Y-%m-%d")
                                        fecha_text = text
                                except ValueError:
                                    pass
                            break

                if not fecha:
                    continue

                lugar_el = art.select_one(".ellipsis")
                lugar = lugar_el.get_text(strip=True) if lugar_el else "Pereira"

                img_el = art.select_one("img")
                imagen_url = img_el.get("src", "") if img_el else ""

                eventos.append({
                    "nombre_evento": titulo,
                    "fecha_evento": fecha,
                    "hora": "no especificado",
                    "lugar": lugar,
                    "ciudad": self.ciudad or "Pereira",
                    "categoria": "taller",
                    "descripcion": "",
                    "url_post": url,
                    "imagen_url": imagen_url,
                    "notas": "",
                })
            except Exception as e:
                logger.warning(f"Error parseando evento CamaraPereira: {e}")

        return eventos
