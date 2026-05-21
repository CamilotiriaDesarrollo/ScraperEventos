import logging
import re
from datetime import datetime

from scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

PROGRAMACION_URL = "https://maloka.org/programacion"

MESES_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}

RE_FECHA = re.compile(r"(\d{1,2})\s+de\s+(\w+)(?:\s+de\s+(\d{4}))?", re.I)
RE_HORA = re.compile(r"(\d{1,2}:\d{2})\s*(AM|PM|am|pm)?")

LUGAR_KW = ["Cinedomo", "Domo", "Auditorio", "Sala"]


class MalokaScraper(BaseScraper):

    def extraer_eventos(self):
        soup = self.fetch(PROGRAMACION_URL)
        if not soup:
            return []

        event_urls = []
        for item in soup.select('[class*="evento"]'):
            a = item.select_one("a[href]")
            if a:
                href = a["href"]
                if href and href not in event_urls:
                    event_urls.append(href)

        eventos = []
        hoy = datetime.now().date()

        for url in event_urls:
            try:
                detail = self.fetch(url)
                if not detail:
                    continue

                h1 = detail.find("h1") or detail.find("h2")
                if not h1:
                    og = detail.find("meta", property="og:title")
                    if not og:
                        continue
                    titulo = og.get("content", "").split(" - ")[0].strip()
                else:
                    titulo = h1.get_text(strip=True)
                if not titulo:
                    continue

                text = detail.get_text(" ", strip=True)

                fecha = None
                for m in RE_FECHA.finditer(text[:3000]):
                    dia_str, mes_str, anio_str = m.groups()
                    mes = MESES_ES.get(mes_str.lower())
                    if not mes:
                        continue
                    dia = int(dia_str)
                    anio = int(anio_str) if anio_str else hoy.year
                    try:
                        candidato = datetime(anio, mes, dia).date()
                        if candidato >= hoy:
                            fecha = candidato.strftime("%Y-%m-%d")
                            break
                    except ValueError:
                        continue

                if not fecha:
                    continue

                hora = "no especificado"
                m_hora = RE_HORA.search(text[:3000])
                if m_hora:
                    h_val, ampm = m_hora.groups()
                    hora = f"{h_val} {ampm.upper()}" if ampm else h_val

                lugar = "Maloka"
                lugar_match = re.search(r"Lugar\s*:\s*(.{3,80}?)(?:\s*(?:🎟|Invers|Ingreso|\n|$))", text, re.I)
                if lugar_match:
                    lugar = lugar_match.group(1).strip().rstrip(".,;")
                else:
                    text_lower = text.lower()
                    for kw in LUGAR_KW:
                        idx = text_lower.find(kw.lower())
                        if idx != -1:
                            snippet = text[idx:idx+40]
                            lugar = re.split(r"[\n🎟]|Ingreso|Invers", snippet)[0].strip().rstrip(".,;")
                            break

                img = detail.select_one(".wp-post-image, .entry-content img, article img")
                imagen_url = img.get("src", "") if img else ""
                if imagen_url and not imagen_url.startswith("http"):
                    imagen_url = f"https://maloka.org{imagen_url}"

                eventos.append({
                    "nombre_evento": titulo,
                    "fecha_evento": fecha,
                    "hora": hora,
                    "lugar": lugar,
                    "ciudad": self.ciudad or "Bogotá",
                    "categoria": "taller",
                    "descripcion": "",
                    "url_post": url,
                    "imagen_url": imagen_url,
                    "notas": "",
                })
            except Exception as e:
                logger.warning(f"Error scrapeando evento Maloka {url}: {e}")

        return eventos
