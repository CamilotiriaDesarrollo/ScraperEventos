import logging
import re
from datetime import datetime, timedelta

from scrapers.base_playwright import BasePlaywrightScraper

logger = logging.getLogger(__name__)

MES_EN = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
          "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
MES_ES = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
          "jul": 7, "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12}

CATEGORIA_MAP_EB = {
    "music": "concierto",
    "performing-arts": "teatro",
    "arts": "exposicion",
    "comedy": "stand-up",
    "film-and-media": "cine",
    "film-media": "cine",
    "food-and-drink": "gastronomia",
    "fashion": "exposicion",
    "business": "conversatorio",
    "school-activities": "taller",
    "family-and-education": "taller",
    "charity-and-causes": "festival",
    "community": "festival",
    "government": "conversatorio",
    "health": "taller",
    "hobbies": "taller",
    "home-and-lifestyle": "taller",
    "religion-and-spirituality": "conversatorio",
    "science-and-technology": "conversatorio",
    "seasonal-and-holiday": "festival",
    "travel-and-outdoor": "festival",
    "sports-and-fitness": "festival",
    "auto-boat-and-air": "festival",
}


class EventbriteScraper(BasePlaywrightScraper):
    BASE_URL = "https://www.eventbrite.com"
    wait_selector = ".event-card"
    extra_wait_ms = 3000

    def extraer_eventos(self):
        # eventbrite.com.co no resuelve DNS; reemplazamos por eventbrite.com
        target = (self.url or "").replace("eventbrite.com.co", "eventbrite.com")
        soup = self.fetch(target)
        if not soup:
            return []

        eventos = []
        hoy = datetime.now().date()
        vistos = set()

        for card in soup.select(".event-card"):
            try:
                link = card.select_one("a.event-card-link[data-event-id]")
                if not link:
                    continue
                event_id = link.get("data-event-id", "")
                if not event_id or event_id in vistos:
                    continue
                vistos.add(event_id)

                titulo = link.get("aria-label", "").replace("View ", "").strip()
                if not titulo:
                    h3 = card.select_one("h3")
                    titulo = h3.get_text(strip=True) if h3 else ""
                if not titulo:
                    continue

                url = link.get("href", "").split("?")[0]

                location = link.get("data-event-location", "")
                ciudad_loc = ""
                if location:
                    partes = [p.strip() for p in location.split(",")]
                    ciudad_loc = partes[-1] if partes else ""

                category = link.get("data-event-category", "")
                categoria = CATEGORIA_MAP_EB.get(category, "")

                detalles = card.select_one(".event-card-details")
                fecha = None
                hora = None
                direccion = ""
                if detalles:
                    p_fecha = detalles.find(
                        "p", class_=lambda c: c and "body-md-bold" in c
                    )
                    if p_fecha:
                        fecha, hora = self._parsear_fecha(p_fecha.get_text(strip=True), hoy)
                    p_direccion = detalles.find(
                        "p", class_=lambda c: c and "body-md" in c and "body-md-bold" not in c
                    )
                    if p_direccion:
                        direccion = p_direccion.get_text(strip=True)

                if not fecha:
                    continue

                img = card.select_one("img.event-card-image")
                imagen = img.get("src", "") if img else ""

                paid = link.get("data-event-paid-status", "")
                notas_partes = []
                if paid == "free":
                    notas_partes.append("Entrada libre")
                elif paid == "paid":
                    notas_partes.append("Boletería de pago")
                notas_partes.append("Boletería: eventbrite.com")
                notas = ". ".join(notas_partes)

                lugar = direccion or location

                eventos.append({
                    "nombre_evento": titulo,
                    "fecha_evento": fecha,
                    "hora": hora or "no especificado",
                    "lugar": lugar,
                    "ciudad": ciudad_loc or self.ciudad or "Bogotá",
                    "categoria": categoria,
                    "descripcion": "",
                    "url_post": url,
                    "imagen_url": imagen,
                    "notas": notas,
                })
            except Exception as e:
                logger.warning(f"Error parseando item Eventbrite: {e}")
                continue
        return eventos

    def _parsear_fecha(self, texto, hoy):
        if not texto:
            return None, None
        texto_low = texto.lower()

        hora = None
        m = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)", texto_low)
        if m:
            h, mm, ampm = m.groups()
            hora = f"{int(h)}:{mm or '00'} {ampm.upper()}"

        if "today" in texto_low or "hoy" in texto_low:
            return hoy.strftime("%Y-%m-%d"), hora
        if "tomorrow" in texto_low or "mañana" in texto_low or "manana" in texto_low:
            return (hoy + timedelta(days=1)).strftime("%Y-%m-%d"), hora

        m = re.search(r"\b([a-zA-Záéíóú]{3,9})\s+(\d{1,2})\b", texto_low)
        if m:
            mes_str, dia_str = m.groups()
            mes = MES_EN.get(mes_str[:3]) or MES_ES.get(mes_str[:3])
            if mes:
                try:
                    dia = int(dia_str)
                except ValueError:
                    return None, hora
                for anio in (hoy.year, hoy.year + 1):
                    try:
                        d = datetime(anio, mes, dia).date()
                    except ValueError:
                        return None, hora
                    if d >= hoy:
                        return d.strftime("%Y-%m-%d"), hora
        return None, hora
