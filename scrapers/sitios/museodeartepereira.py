import logging
import re
from datetime import datetime

from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

BASE_URL = "https://www.museodeartedepereira.com"
EVENTOS_URL = f"{BASE_URL}/events/list/"


class MuseoArtePereiraScraper(BaseScraper):

    def extraer_eventos(self):
        soup = self.fetch(EVENTOS_URL)
        if not soup:
            return []

        hoy = datetime.now().date()
        eventos = []
        seen = set()

        for art in soup.select("article[class*='tribe_events']"):
            try:
                title_a = art.select_one("h2 a, h3 a")
                if not title_a:
                    continue
                titulo = title_a.get_text(strip=True)
                url_evento = title_a.get("href", "")
                if not titulo or not url_evento or url_evento in seen:
                    continue
                seen.add(url_evento)

                # time[datetime] attribute: "2026-06-10"
                time_el = art.select_one("time[datetime]")
                if not time_el:
                    continue
                dt_val = time_el.get("datetime", "")[:10]
                try:
                    dt = datetime.strptime(dt_val, "%Y-%m-%d").date()
                except ValueError:
                    continue
                if dt < hoy:
                    continue
                fecha = dt.strftime("%Y-%m-%d")

                # Hora from time text: "mayo 20, 2026 @ 10:00 am"
                hora = "no especificado"
                time_text = time_el.get_text(" ", strip=True)
                m_hora = re.search(r"(\d{1,2}:\d{2}\s*(?:am|pm))", time_text, re.I)
                if m_hora:
                    hora = m_hora.group(1)

                lugar_el = art.select_one("[class*='venue-title']")
                lugar = lugar_el.get_text(strip=True) if lugar_el else "Museo de Arte de Pereira"

                img_el = art.select_one("img")
                imagen_url = img_el.get("src", "") if img_el else ""

                eventos.append({
                    "nombre_evento": titulo,
                    "fecha_evento": fecha,
                    "hora": hora,
                    "lugar": lugar,
                    "ciudad": self.ciudad or "Pereira",
                    "categoria": "exposicion",
                    "descripcion": "",
                    "url_post": url_evento,
                    "imagen_url": imagen_url,
                    "notas": "",
                })
            except Exception as e:
                logger.warning(f"Error parseando evento MuseoArtePereira: {e}")

        return eventos
