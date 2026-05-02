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

# El sitio muestra el datetime en UTC pero la hora visible es local Bogotá;
# usamos la fecha del datetime y la hora del texto visible.
RE_HORA = re.compile(
    r"(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)",
    re.IGNORECASE,
)
RE_FECHA_TEXTO = re.compile(
    r"(\d{1,2})\s+de\s+([A-Za-zÁÉÍÓÚáéíóúñÑ]+)",
    re.IGNORECASE,
)

# Mapea la categoría que muestra el sitio (.ctg-ev-24) a las categorías
# normalizadas del Sheet (sin tildes, lowercase).
CATEGORIA_MAP = {
    "teatro": "teatro",
    "obra de teatro": "teatro",
    "danza": "danza",
    "concierto": "concierto",
    "música": "concierto",
    "musica": "concierto",
    "exposición": "exposicion",
    "exposicion": "exposicion",
    "cine": "cine",
    "audiovisual": "cine",
    "conversatorio": "conversatorio",
    "festival": "festival",
    "taller": "taller",
    "literatura": "conversatorio",
    "lanzamiento": "lanzamiento",
}


class IdArtesScraper(BaseScraper):
    BASE_URL = "https://www.idartes.gov.co"
    AGENDA_URL = "https://www.idartes.gov.co/es/agenda"

    def extraer_eventos(self):
        soup = self.fetch(self.AGENDA_URL)
        if not soup:
            return []

        eventos = []
        for caja in soup.select(".cajashomeeventos"):
            try:
                titulo_a = caja.select_one(".titulo_cajashomeeventos a")
                if not titulo_a:
                    continue
                titulo = titulo_a.get_text(strip=True)
                if not titulo:
                    continue
                url = self._absolutizar(titulo_a.get("href", ""))

                fecha, hora = self._extraer_fecha_hora(caja)
                if not fecha:
                    continue

                cat_elem = caja.select_one(".ctg-ev-24")
                categoria = self._normalizar_categoria(
                    cat_elem.get_text(strip=True) if cat_elem else ""
                )

                desc_elem = caja.select_one(".descripcion_cajashomeeventos")
                descripcion = desc_elem.get_text(" ", strip=True) if desc_elem else ""

                tipo_elem = caja.select_one(".tipo_cajashomeeventos")
                tipo_entrada = tipo_elem.get_text(strip=True) if tipo_elem else ""

                img_elem = caja.select_one("img")
                imagen_url = ""
                if img_elem:
                    src = img_elem.get("src") or img_elem.get("data-src", "")
                    imagen_url = self._absolutizar(src)

                eventos.append({
                    "nombre_evento": titulo,
                    "fecha_evento": fecha,
                    "hora": hora or "no especificado",
                    "lugar": "IDARTES",
                    "ciudad": self.ciudad or "Bogotá",
                    "categoria": categoria,
                    "descripcion": descripcion[:200],
                    "url_post": url,
                    "imagen_url": imagen_url,
                    "notas": tipo_entrada,
                })
            except Exception as e:
                logger.warning(f"Error parseando item en IDARTES: {e}")
                continue

        return eventos

    def _absolutizar(self, href):
        if not href:
            return ""
        if href.startswith("http"):
            return href
        if href.startswith("/"):
            return f"{self.BASE_URL}{href}"
        return ""

    def _extraer_fecha_hora(self, caja):
        contenedor = caja.select_one(".fecha_cajashomeeventos")
        if not contenedor:
            return None, None

        fecha = None
        time_elem = contenedor.select_one("time[datetime]")
        if time_elem and time_elem.get("datetime"):
            fecha = time_elem["datetime"][:10]
        else:
            texto = contenedor.get_text(" ", strip=True)
            m = RE_FECHA_TEXTO.search(texto)
            if m:
                fecha = self._construir_fecha(m.group(1), m.group(2))

        texto_visible = contenedor.get_text(" ", strip=True)
        hora = None
        m = RE_HORA.search(texto_visible)
        if m:
            h, mm, ampm = m.groups()
            hora = f"{int(h)}:{mm or '00'} {ampm.replace('.', '').upper()}"

        return fecha, hora

    def _construir_fecha(self, dia_str, mes_str):
        mes = MESES_ES.get(mes_str.lower().strip())
        if not mes:
            return None
        try:
            dia = int(dia_str)
        except ValueError:
            return None
        hoy = datetime.now().date()
        for anio in (hoy.year, hoy.year + 1):
            try:
                candidato = datetime(anio, mes, dia).date()
            except ValueError:
                return None
            if candidato >= hoy:
                return candidato.strftime("%Y-%m-%d")
        return None

    def _normalizar_categoria(self, texto):
        clave = texto.strip().lower()
        if not clave:
            return ""
        if clave in CATEGORIA_MAP:
            return CATEGORIA_MAP[clave]
        for cat_sitio, cat_norm in CATEGORIA_MAP.items():
            if cat_sitio in clave:
                return cat_norm
        return clave
