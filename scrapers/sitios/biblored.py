import logging
from datetime import datetime

from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


CATEGORIA_BIBLORED = {
    "cuerpos en escena": "teatro",
    "teatro": "teatro",
    "danza": "danza",
    "música": "concierto",
    "musica": "concierto",
    "concierto": "concierto",
    "lectura": "conversatorio",
    "literatura": "conversatorio",
    "cine": "cine",
    "exposición": "exposicion",
    "exposicion": "exposicion",
    "taller": "taller",
    "laboratorio": "taller",
    "conversatorio": "conversatorio",
    "infantil": "taller",
}


class BibloRedScraper(BaseScraper):
    BASE_URL = "https://www.biblored.gov.co"
    AGENDA_URL = "https://www.biblored.gov.co/eventos"

    def extraer_eventos(self):
        soup = self.fetch(self.AGENDA_URL)
        if not soup:
            return []

        eventos = []
        hoy = datetime.now().date()
        vistos = set()

        for card in soup.select("a.event-row"):
            try:
                titulo_elem = card.select_one(".title h6, .title")
                if not titulo_elem:
                    continue
                titulo = titulo_elem.get_text(" ", strip=True)
                if not titulo:
                    continue
                href = card.get("href", "")
                url = self._absolutizar(href)

                clave = (titulo.lower(), url)
                if clave in vistos:
                    continue
                vistos.add(clave)

                fecha = ""
                for t in card.select(".date time"):
                    dt_attr = (t.get("datetime") or "").strip()
                    if dt_attr:
                        fecha = dt_attr[:10]
                        break
                if not fecha:
                    continue
                try:
                    fd = datetime.strptime(fecha, "%Y-%m-%d").date()
                except ValueError:
                    continue
                if fd < hoy:
                    continue

                tags = [t.get_text(" ", strip=True) for t in card.select(".tag-alternative")]
                tags = [t for t in tags if t]
                categoria = self._inferir_categoria(tags[0] if tags else "")
                lugar = tags[1] if len(tags) > 1 else ""

                desc_elem = card.select_one(".description a, .description")
                descripcion = desc_elem.get_text(" ", strip=True) if desc_elem else ""

                img_elem = card.select_one("img[src]")
                imagen = ""
                if img_elem:
                    imagen = self._absolutizar(img_elem.get("src", ""))

                eventos.append({
                    "nombre_evento": titulo,
                    "fecha_evento": fecha,
                    "hora": "no especificado",
                    "lugar": lugar,
                    "ciudad": self.ciudad or "Bogotá",
                    "categoria": categoria,
                    "descripcion": descripcion[:200],
                    "url_post": url,
                    "imagen_url": imagen,
                    "notas": "Entrada libre. BibloRed",
                })
            except Exception as e:
                logger.warning(f"Error parseando item BibloRed: {e}")
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

    def _inferir_categoria(self, texto):
        if not texto:
            return ""
        clave = texto.lower()
        for k, v in CATEGORIA_BIBLORED.items():
            if k in clave:
                return v
        return ""
