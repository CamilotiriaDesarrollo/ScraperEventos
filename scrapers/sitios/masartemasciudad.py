import logging
import re
from datetime import datetime, date

from scrapers.base_playwright import BasePlaywrightScraper

logger = logging.getLogger(__name__)

BASE_URL = "https://masartemasciudad.com"

MESES_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}

CATEGORIA_KW = {
    "teatro": "teatro",
    "danza": "danza",
    "concierto": "concierto",
    "música": "concierto",
    "cine": "cine",
    "exposición": "exposicion",
    "exposicion": "exposicion",
    "arte": "exposicion",
    "festival": "festival",
    "taller": "taller",
}

RE_HORA = re.compile(r"@\s*(\d{1,2}:\d{2}\s*(?:AM|PM))", re.I)


class MasArteMasCiudadScraper(BasePlaywrightScraper):

    wait_selector = "article.type-tribe_events, article[data-event-id]"
    wait_timeout_ms = 25000
    extra_wait_ms = 3000

    def extraer_eventos(self):
        hoy = date.today()
        # Scrape current month + next 2 months
        months = []
        yr, mo = hoy.year, hoy.month
        for _ in range(3):
            months.append(f"{yr}-{mo:02d}")
            mo += 1
            if mo > 12:
                mo = 1
                yr += 1

        seen_ids = set()
        eventos = []

        for month_str in months:
            url = f"{BASE_URL}/eventos/mes/{month_str}"
            soup = self.fetch(url)
            if not soup:
                continue

            for art in soup.select("article[data-event-id]"):
                event_id = art.get("data-event-id", "")
                if event_id in seen_ids:
                    continue
                seen_ids.add(event_id)

                try:
                    # Title
                    title_el = art.select_one("h2 a, h3 a, a[aria-describedby]")
                    if not title_el:
                        continue
                    titulo = title_el.get_text(strip=True)
                    if not titulo:
                        continue
                    url_evento = title_el.get("href", "")

                    # Date: first time[datetime] with YYYY-MM-DD
                    fecha = None
                    for t in art.find_all("time"):
                        dt_val = t.get("datetime", "")
                        if re.match(r"\d{4}-\d{2}-\d{2}$", dt_val):
                            try:
                                fecha_dt = datetime.strptime(dt_val, "%Y-%m-%d").date()
                                if fecha_dt >= hoy:
                                    fecha = fecha_dt.strftime("%Y-%m-%d")
                                break
                            except ValueError:
                                continue

                    if not fecha:
                        # Try parsing from text "mes DD @"
                        text = art.get_text(" ", strip=True)
                        m = re.search(r"(\w+)\s+(\d{1,2})\s*@", text, re.I)
                        if m:
                            mes = MESES_ES.get(m.group(1).lower())
                            if mes:
                                for yr_try in (hoy.year, hoy.year + 1):
                                    try:
                                        cand = date(yr_try, mes, int(m.group(2)))
                                        if cand >= hoy:
                                            fecha = cand.strftime("%Y-%m-%d")
                                            break
                                    except ValueError:
                                        continue
                    if not fecha:
                        continue

                    # Hora
                    text = art.get_text(" ", strip=True)
                    hora = "no especificado"
                    m_hora = RE_HORA.search(text)
                    if m_hora:
                        hora = m_hora.group(1).strip()

                    # Category from title/text
                    categoria = self._inferir_categoria(titulo)

                    # Image
                    img = art.select_one("img")
                    imagen_url = ""
                    if img:
                        src = img.get("src", img.get("data-src", ""))
                        imagen_url = src if src.startswith("http") else f"{BASE_URL}{src}"

                    eventos.append({
                        "nombre_evento": titulo,
                        "fecha_evento": fecha,
                        "hora": hora,
                        "lugar": "Bogotá",
                        "ciudad": self.ciudad or "Bogotá",
                        "categoria": categoria,
                        "descripcion": "",
                        "url_post": url_evento,
                        "imagen_url": imagen_url,
                        "notas": "",
                    })
                except Exception as e:
                    logger.warning(f"Error parseando evento MasArte: {e}")

        return eventos

    def _inferir_categoria(self, texto):
        texto_low = texto.lower()
        for kw, cat in CATEGORIA_KW.items():
            if kw in texto_low:
                return cat
        return "exposicion"
