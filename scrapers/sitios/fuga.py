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

# "27 de Abril 2026"
RE_FECHA_FUGA = re.compile(
    r"(\d{1,2})\s+de\s+([A-Za-zÁÉÍÓÚáéíóúñÑ]+)\s+(\d{4})",
    re.IGNORECASE,
)

CATEGORIA_FUGA = {
    "muestra": "exposicion",
    "exposición": "exposicion",
    "exposicion": "exposicion",
    "concierto": "concierto",
    "música": "concierto",
    "musica": "concierto",
    "teatro": "teatro",
    "danza": "danza",
    "cine": "cine",
    "taller": "taller",
    "conversatorio": "conversatorio",
    "literatura": "conversatorio",
    "festival": "festival",
}


class FugaScraper(BasePlaywrightScraper):
    BASE_URL = "https://www.fuga.gov.co"
    AGENDA_URL = "https://www.fuga.gov.co/agenda"
    wait_selector = ".views-row"
    extra_wait_ms = 3500

    def extraer_eventos(self):
        soup = self.fetch(self.AGENDA_URL)
        if not soup:
            return []

        eventos = []
        hoy = datetime.now().date()
        vistos = set()

        for row in soup.select(".views-row"):
            try:
                titulo_a = row.select_one(".news2-title h2 a")
                if not titulo_a:
                    continue
                titulo = titulo_a.get_text(" ", strip=True)
                if not titulo:
                    continue
                url = self._absolutizar(titulo_a.get("href", ""))

                clave = (titulo.lower(), url)
                if clave in vistos:
                    continue
                vistos.add(clave)

                # FUGA muestra rangos: "27 Abril 2026 / hasta / 4 Mayo 2026"
                # Tomamos todas las fechas del bloque y filtramos por la fecha fin (si existe)
                ev_day = row.select_one(".ev-day")
                fecha = None
                if ev_day:
                    fechas = []
                    for div in ev_day.find_all("div"):
                        f = self._parsear_fecha_raw(div.get_text(" ", strip=True))
                        if f:
                            fechas.append(f)
                    if fechas:
                        fecha_fin = fechas[-1]
                        if fecha_fin >= hoy:
                            fecha_inicio = fechas[0]
                            fecha = (fecha_inicio if fecha_inicio >= hoy else hoy).strftime("%Y-%m-%d")
                if not fecha:
                    continue

                # Hora "3:00 PM a 4:00 PM"
                ev_hour = row.select_one(".ev-hour")
                hora = "no especificado"
                if ev_hour:
                    hora_txt = ev_hour.get_text(" ", strip=True).replace("Hora:", "").strip()
                    if hora_txt:
                        hora = hora_txt.split(" a ")[0].strip()

                # Lugar
                ev_pl = row.select_one(".ev-pl")
                lugar = "FUGA"
                if ev_pl:
                    lugar_txt = ev_pl.get_text(" ", strip=True).replace("Lugar:", "").strip()
                    if lugar_txt:
                        lugar = lugar_txt

                # Tipo / categoría
                ev_type = row.select_one(".ev-type")
                categoria = ""
                if ev_type:
                    categoria = self._normalizar_categoria(ev_type.get_text(" ", strip=True).lower())

                # Descripción
                desc_elem = row.select_one(".news2-txt p")
                descripcion = desc_elem.get_text(" ", strip=True) if desc_elem else ""

                # Imagen
                img_elem = row.select_one(".ev-img img[src]")
                imagen = ""
                if img_elem:
                    imagen = self._absolutizar(img_elem.get("src", ""))

                eventos.append({
                    "nombre_evento": titulo,
                    "fecha_evento": fecha,
                    "hora": hora,
                    "lugar": lugar,
                    "ciudad": self.ciudad or "Bogotá",
                    "categoria": categoria,
                    "descripcion": descripcion[:200],
                    "url_post": url,
                    "imagen_url": imagen,
                    "notas": "FUGA - Fundación Gilberto Alzate",
                })
            except Exception as e:
                logger.warning(f"Error parseando item FUGA: {e}")
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

    def _parsear_fecha_raw(self, texto):
        """Parsea texto a date sin filtrar por hoy."""
        m = RE_FECHA_FUGA.search(texto)
        if not m:
            return None
        dia, mes_str, anio = m.groups()
        mes = MESES_ES.get(mes_str.lower().strip())
        if not mes:
            return None
        try:
            return datetime(int(anio), mes, int(dia)).date()
        except ValueError:
            return None

    def _normalizar_categoria(self, texto):
        for k, v in CATEGORIA_FUGA.items():
            if k in texto:
                return v
        return ""
