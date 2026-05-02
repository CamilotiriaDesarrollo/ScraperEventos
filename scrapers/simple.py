import logging

from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class SimpleScraper(BaseScraper):
    """
    Scraper genérico para sitios HTML estáticos.
    Lee selectores desde el dict `fuente` (columnas opcionales en FUENTES_WEB):
      - selector_item, selector_titulo, selector_fecha,
        selector_lugar, selector_descripcion, selector_link
      - categoria_default
    """

    DEFAULTS = {
        "selector_item": "article, .event, .views-row",
        "selector_titulo": "h2, h3, .title",
        "selector_fecha": "time, .date",
        "selector_lugar": ".location, .venue, .place",
        "selector_descripcion": ".description, .summary, p",
        "selector_link": "a[href]",
    }

    def _sel(self, key):
        valor = (self.fuente.get(key) or "").strip()
        return valor or self.DEFAULTS[key]

    def extraer_eventos(self):
        soup = self.fetch()
        if not soup:
            return []

        items = soup.select(self._sel("selector_item"))
        eventos = []
        categoria = self.fuente.get("categoria_default", "") or ""

        for item in items:
            try:
                titulo_elem = item.select_one(self._sel("selector_titulo"))
                if not titulo_elem:
                    continue
                titulo = titulo_elem.get_text(strip=True)
                if not titulo:
                    continue

                fecha_elem = item.select_one(self._sel("selector_fecha"))
                fecha = ""
                if fecha_elem:
                    fecha = fecha_elem.get("datetime") or fecha_elem.get_text(strip=True)

                lugar_elem = item.select_one(self._sel("selector_lugar"))
                lugar = lugar_elem.get_text(strip=True) if lugar_elem else self.nombre

                desc_elem = item.select_one(self._sel("selector_descripcion"))
                desc = desc_elem.get_text(strip=True)[:200] if desc_elem else ""

                link_elem = item.select_one(self._sel("selector_link"))
                url = ""
                if link_elem and link_elem.has_attr("href"):
                    href = link_elem["href"]
                    if href.startswith("http"):
                        url = href
                    elif href.startswith("/"):
                        base = self.url.rstrip("/")
                        url = f"{base}{href}" if base else href

                eventos.append({
                    "nombre_evento": titulo,
                    "fecha_evento": fecha,
                    "hora": "no especificado",
                    "lugar": lugar,
                    "ciudad": self.ciudad,
                    "categoria": categoria,
                    "descripcion": desc,
                    "url_post": url,
                })
            except Exception as e:
                logger.warning(f"Error parseando item en {self.nombre}: {e}")
                continue

        return eventos
