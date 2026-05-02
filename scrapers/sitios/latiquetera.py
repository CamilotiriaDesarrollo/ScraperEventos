import logging
import re
from datetime import datetime

from scrapers.base_playwright import BasePlaywrightScraper

logger = logging.getLogger(__name__)

CATEGORIA_BALLOON_MAP = {
    "concierto": "concierto",
    "música": "concierto",
    "musica": "concierto",
    "teatro": "teatro",
    "circo": "festival",
    "comedia": "stand-up",
    "stand": "stand-up",
    "cine": "cine",
    "danza": "danza",
    "festival": "festival",
    "feria": "feria",
    "deporte": "festival",
    "infantil": "teatro",
    "fiesta": "fiesta",
    "carrera": "festival",
    "running": "festival",
    "gastronomía": "gastronomia",
    "gastronomia": "gastronomia",
    "exposición": "exposicion",
    "exposicion": "exposicion",
    "conferencia": "conversatorio",
    "conversatorio": "conversatorio",
    "taller": "taller",
}


class LaTiqueteraScraper(BasePlaywrightScraper):
    BASE_URL = "https://latiquetera.com"
    wait_selector = ".item-box-event, .item-big-box-event"
    extra_wait_ms = 3000

    def extraer_eventos(self):
        soup = self.fetch()
        if not soup:
            return []

        eventos = []
        hoy = datetime.now().date()
        vistos = set()

        for caja in soup.select(".item-box-event, .item-big-box-event"):
            try:
                titulo_elem = caja.select_one(".item-box-content-title")
                if not titulo_elem:
                    continue
                titulo = titulo_elem.get_text(" ", strip=True)
                if not titulo:
                    continue

                cover = caja.select_one("a.cover")
                href = cover.get("href", "") if cover else ""
                if not href:
                    bottom = caja.select_one(".item-box-bottom-action")
                    href = bottom.get("href", "") if bottom else ""
                url = self._absolutizar(href)

                clave = (titulo.lower(), url)
                if clave in vistos:
                    continue
                vistos.add(clave)

                fecha = self._extraer_fecha(caja, hoy)
                if not fecha:
                    continue

                tags = caja.select(".item-box-tags span")
                lugar_ciudad = ""
                if tags:
                    lugar_ciudad = tags[0].get_text(" ", strip=True)
                ciudad = self.ciudad or "Bogotá"
                lugar = lugar_ciudad
                if "," in lugar_ciudad:
                    partes = [p.strip() for p in lugar_ciudad.split(",")]
                    lugar = partes[0]
                    ciudad = partes[0] if len(partes) == 1 else partes[0]

                cat_elem = caja.select_one(".item-box-balloon-extra")
                categoria = ""
                if cat_elem:
                    raw = cat_elem.get_text(" ", strip=True).lower()
                    categoria = self._normalizar_categoria(raw)

                desc_elem = caja.select_one(".item-box-balloon p")
                descripcion = desc_elem.get_text(" ", strip=True) if desc_elem else ""

                img_elem = caja.select_one("img.item-box-image")
                imagen = ""
                if img_elem:
                    src = img_elem.get("src", "")
                    imagen = self._absolutizar(src)

                eventos.append({
                    "nombre_evento": titulo,
                    "fecha_evento": fecha,
                    "hora": "no especificado",
                    "lugar": lugar,
                    "ciudad": ciudad,
                    "categoria": categoria,
                    "descripcion": descripcion[:200],
                    "url_post": url,
                    "imagen_url": imagen,
                    "notas": "Boletería: latiquetera.com",
                })
            except Exception as e:
                logger.warning(f"Error parseando item La Tiquetera: {e}")
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

    def _extraer_fecha(self, caja, hoy):
        # data-filters="category-36,date-2026-05-01,date-2026-05-02,..."
        df = caja.get("data-filters", "") or ""
        fechas_iso = re.findall(r"date-(\d{4}-\d{2}-\d{2})", df)
        for f_str in sorted(fechas_iso):
            try:
                fd = datetime.strptime(f_str, "%Y-%m-%d").date()
            except ValueError:
                continue
            if fd >= hoy:
                return f_str
        return None

    def _normalizar_categoria(self, texto):
        if not texto:
            return ""
        for clave, valor in CATEGORIA_BALLOON_MAP.items():
            if clave in texto:
                return valor
        return ""
