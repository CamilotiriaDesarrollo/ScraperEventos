import json
import logging
from datetime import datetime

from scrapers.base_playwright import BasePlaywrightScraper

logger = logging.getLogger(__name__)


def _unwrap(v):
    """astro-island envuelve cada valor en [tag, valor]; lo deshacemos recursivamente."""
    if isinstance(v, list) and len(v) == 2 and isinstance(v[0], int) and v[0] in (0, 1, 2):
        return _unwrap(v[1])
    if isinstance(v, list):
        return [_unwrap(x) for x in v]
    if isinstance(v, dict):
        return {k: _unwrap(val) for k, val in v.items()}
    return v


class FeverScraper(BasePlaywrightScraper):
    BASE_URL = "https://feverup.com"
    wait_selector = ".fv-plan-preview-card__link"
    extra_wait_ms = 3500

    def extraer_eventos(self):
        soup = self.fetch()
        if not soup:
            return []

        eventos = []
        hoy = datetime.now().date()
        vistos = set()

        for island in soup.select("astro-island[component-url*='CityPlanCard']"):
            props_str = island.get("props", "")
            if not props_str:
                continue
            try:
                raw = json.loads(props_str)
            except json.JSONDecodeError as e:
                logger.warning(f"JSON malformado Fever: {e}")
                continue

            try:
                data = _unwrap(raw)
                plan = data.get("plan") or {}
                if not plan:
                    continue

                plan_id = plan.get("id")
                if plan_id is not None and plan_id in vistos:
                    continue
                vistos.add(plan_id)

                titulo = (plan.get("name") or "").strip()
                if not titulo:
                    continue

                start = plan.get("startDate", "")
                if not start:
                    continue
                fecha = start[:10]
                try:
                    fd = datetime.strptime(fecha, "%Y-%m-%d").date()
                except ValueError:
                    continue
                if fd < hoy:
                    continue

                hora = "no especificado"
                try:
                    dt = datetime.fromisoformat(start)
                    h12 = dt.hour % 12 or 12
                    ampm = "AM" if dt.hour < 12 else "PM"
                    hora = f"{h12}:{dt.minute:02d} {ampm}"
                except ValueError:
                    pass

                location = plan.get("location") or {}
                lugar = location.get("name") or ""
                places = plan.get("places") or []
                if not lugar and places:
                    lugar = places[0].get("name", "")

                ciudad = self.ciudad or "Bogotá"
                if places:
                    city_obj = places[0].get("city") or {}
                    ciudad = city_obj.get("name") or ciudad

                imagen = plan.get("image") or ""

                price = plan.get("priceAmount")
                currency = plan.get("priceCurrency", "")
                price_type = plan.get("priceType", "")
                notas_partes = []
                if price:
                    prefix = "Desde" if price_type == "from" else "Precio"
                    notas_partes.append(f"{prefix} ${int(price):,} {currency}".strip())
                notas_partes.append("Boletería: feverup.com")
                notas = ". ".join(notas_partes)

                link_elem = island.select_one("a.fv-plan-preview-card__link")
                url = ""
                if link_elem:
                    href = link_elem.get("href", "")
                    if href.startswith("http"):
                        url = href
                    elif href.startswith("/"):
                        url = self.BASE_URL + href
                if not url and plan_id:
                    url = f"{self.BASE_URL}/m/{plan_id}"

                eventos.append({
                    "nombre_evento": titulo,
                    "fecha_evento": fecha,
                    "hora": hora,
                    "lugar": lugar,
                    "ciudad": ciudad,
                    "categoria": "",
                    "descripcion": "",
                    "url_post": url,
                    "imagen_url": imagen,
                    "notas": notas,
                })
            except Exception as e:
                logger.warning(f"Error parseando plan Fever: {e}")
                continue
        return eventos
