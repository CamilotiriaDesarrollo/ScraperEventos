import logging
from datetime import datetime

from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class BogotaAgendaScraper(BaseScraper):
    BASE_URL = "https://bogota.gov.co"
    AGENDA_URL = "https://bogota.gov.co/que-hacer/agenda-cultural"

    def extraer_eventos(self):
        soup = self.fetch(self.AGENDA_URL)
        if not soup:
            return []

        eventos = []
        hoy = datetime.now().date()
        cards = soup.select(
            "a.agenda-cultural-v2__tarjeta-basica, "
            "a.agenda-cultural-v2__tarjeta-item-evento__link"
        )
        vistos = set()
        for card in cards:
            try:
                titulo_elem = card.select_one("h3, h2, .titulo")
                if not titulo_elem:
                    continue
                titulo = titulo_elem.get_text(" ", strip=True)
                if not titulo:
                    continue

                href = card.get("href", "")
                url = self._absolutizar(href)

                time_elem = card.select_one(".evento-detalle-fecha time[datetime]")
                if not time_elem:
                    continue
                fecha = time_elem.get("datetime", "")[:10]
                if not fecha:
                    continue
                try:
                    fd = datetime.strptime(fecha, "%Y-%m-%d").date()
                except ValueError:
                    continue
                if fd < hoy:
                    continue

                clave = (titulo.lower(), fecha)
                if clave in vistos:
                    continue
                vistos.add(clave)

                lugar_elem = card.select_one(".evento-detalle-lugar span")
                lugar = lugar_elem.get_text(strip=True) if lugar_elem else ""

                pago_elem = card.select_one(".evento-detalle-es-pago span")
                pago = pago_elem.get_text(strip=True) if pago_elem else ""

                cat_elem = card.select_one(".categoria-tarjeta span")
                categoria = cat_elem.get_text(strip=True).lower() if cat_elem else ""

                img_elem = card.select_one("img")
                imagen = ""
                if img_elem:
                    src = img_elem.get("src", "") or img_elem.get("data-src", "")
                    imagen = self._absolutizar(src)

                eventos.append({
                    "nombre_evento": titulo,
                    "fecha_evento": fecha,
                    "hora": "no especificado",
                    "lugar": lugar,
                    "ciudad": self.ciudad or "Bogotá",
                    "categoria": categoria,
                    "descripcion": "",
                    "url_post": url,
                    "imagen_url": imagen,
                    "notas": pago,
                })
            except Exception as e:
                logger.warning(f"Error parseando item Bogotá Agenda: {e}")
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
