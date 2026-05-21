import argparse
import logging
import time
from datetime import datetime
from pathlib import Path

from config import DELAY_BETWEEN_REQUESTS, TAB_EVENTOS
from deduplicator import deduplicar_por_titulo_en_sheet, es_duplicado, generar_hash
from scrapers.sitios.biblored import BibloRedScraper
from scrapers.sitios.bogota_agenda import BogotaAgendaScraper
from scrapers.sitios.cinemateca import CinematecaScraper
from scrapers.sitios.eneldelia import EnDeldiaScraper
from scrapers.sitios.teatronacional import TeatroNacionalScraper
from scrapers.sitios.eticketablanca import eTicketablancaScraper
from scrapers.sitios.eventbrite import EventbriteScraper
from scrapers.sitios.fever import FeverScraper
from scrapers.sitios.fuga import FugaScraper
from scrapers.sitios.idartes import IdArtesScraper
from scrapers.sitios.latiquetera import LaTiqueteraScraper
from scrapers.sitios.plancpereira import PlanCPereiraScraper
from scrapers.sitios.planetario import PlanetarioScraper
from scrapers.sitios.taquillalive import TaquillaLiveScraper
from scrapers.sitios.teatrolibre import TeatroLibreScraper
from scrapers.sitios.teatromayor import TeatroMayorScraper
from scrapers.sitios.tuboleta import TuBoletaScraper
from scrapers.sitios.visitbogota import VisitBogotaScraper
from sheets_client import (
    actualizar_ultimo_scrape,
    agregar_eventos,
    escribir_log,
    get_client,
    get_eventos_existentes,
    get_fuentes_web_activas,
)

LOGS_DIR = Path(__file__).resolve().parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOGS_DIR / "scraper.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

CIUDADES_PERMITIDAS = {"bogotá", "bogota", "pereira", "online"}


def _filtrar_y_normalizar_ciudades(eventos):
    out = []
    for e in eventos:
        ciudad_low = str(e.get("ciudad", "")).strip().lower()
        if ciudad_low not in CIUDADES_PERMITIDAS:
            continue
        if ciudad_low in ("bogotá", "bogota"):
            e["ciudad"] = "Bogotá"
        elif ciudad_low == "pereira":
            e["ciudad"] = "Pereira"
        elif ciudad_low == "online":
            e["ciudad"] = "online"
        out.append(e)
    return out


SCRAPER_MAP = {
    "idartes.gov.co": IdArtesScraper,
    "plancpereira.com": PlanCPereiraScraper,
    "teatromayor.org": TeatroMayorScraper,
    "teatrolibre.com": TeatroLibreScraper,
    "bogota.gov.co/agenda-cultural": BogotaAgendaScraper,
    "tuboleta.com": TuBoletaScraper,
    "eventbrite.com.co": EventbriteScraper,
    "feverup.com": FeverScraper,
    "latiquetera.com": LaTiqueteraScraper,
    "eticketablanca.com": eTicketablancaScraper,
    "taquillalive.com": TaquillaLiveScraper,
    "biblored.gov.co": BibloRedScraper,
    "planetariodebogota.gov.co": PlanetarioScraper,
    "visitbogota.co": VisitBogotaScraper,
    "fuga.gov.co": FugaScraper,
    "cinematecadebogota.gov.co": CinematecaScraper,
    "eneldelia.gov.co": EnDeldiaScraper,
    "teatronacional.co": TeatroNacionalScraper,
}


def get_scraper_for_fuente(fuente):
    dominio = (fuente.get("dominio") or "").lower()
    url = (fuente.get("url") or "").lower()
    for key, scraper_class in SCRAPER_MAP.items():
        if key in dominio or key in url:
            return scraper_class(fuente)
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ciudad", choices=["Bogotá", "Bogota", "Pereira"], help="Filtrar por ciudad")
    args = parser.parse_args()

    hora_inicio = datetime.now()
    logger.info("=" * 60)
    logger.info("INICIO DE SESION DE SCRAPING WEB")
    logger.info("=" * 60)

    logger.info("Conectando a Google Sheets...")
    spreadsheet = get_client()

    fuentes = get_fuentes_web_activas(spreadsheet, incluir_js=True)
    if args.ciudad:
        ciudad_filtro = args.ciudad.lower().replace("bogota", "bogotá")
        fuentes = [f for f in fuentes if f.get("ciudad", "").strip().lower() == ciudad_filtro]
        logger.info(f"Filtro ciudad: {args.ciudad}")
    logger.info(f"Fuentes activas: {len(fuentes)}")

    hashes_existentes, ultimo_id = get_eventos_existentes(spreadsheet)
    logger.info(f"Eventos existentes: {len(hashes_existentes)}")
    logger.info(f"Ultimo ID: EVT{ultimo_id:03d}")

    total_nuevos = 0
    total_omitidos = 0
    fuentes_revisadas = 0
    fuentes_con_error = []
    fuentes_sin_scraper = []
    id_counter = ultimo_id

    for fuente in fuentes:
        nombre = fuente.get("nombre_real") or fuente.get("dominio") or "?"
        fuente_id = fuente.get("id", "")

        scraper = get_scraper_for_fuente(fuente)
        if not scraper:
            fuentes_sin_scraper.append(nombre)
            continue

        logger.info(f"--- Procesando: {nombre} ---")
        eventos_raw = scraper.run()
        fuentes_revisadas += 1

        if eventos_raw is None:
            fuentes_con_error.append(nombre)
            actualizar_ultimo_scrape(spreadsheet, fuente_id, "error")
            time.sleep(DELAY_BETWEEN_REQUESTS)
            continue

        eventos_raw = _filtrar_y_normalizar_ciudades(eventos_raw)

        eventos_nuevos = []
        for evento in eventos_raw:
            if es_duplicado(evento, hashes_existentes):
                total_omitidos += 1
                continue

            id_counter += 1
            evento["id"] = f"EVT{id_counter:03d}"
            evento["fecha_extraccion"] = datetime.now().strftime("%Y-%m-%d")
            evento["fuente_tipo"] = "web"
            evento["fuente"] = "web"
            evento["perfil_ig"] = fuente.get("dominio", "")
            evento["estado"] = "pendiente"
            evento.setdefault("imagen_url", "")
            if not evento.get("notas"):
                evento["notas"] = f"Fuente: {nombre}"

            hashes_existentes.add(generar_hash(
                evento.get("nombre_evento", ""),
                evento.get("fecha_evento", ""),
                evento.get("lugar", ""),
            ))
            eventos_nuevos.append(evento)

        if eventos_nuevos:
            agregar_eventos(spreadsheet, eventos_nuevos)
            total_nuevos += len(eventos_nuevos)
            logger.info(f"  -> {len(eventos_nuevos)} eventos nuevos agregados")
        else:
            logger.info("  -> 0 eventos nuevos (todos duplicados o sin resultados)")

        actualizar_ultimo_scrape(spreadsheet, fuente_id, "ok")
        time.sleep(DELAY_BETWEEN_REQUESTS)

    hora_fin = datetime.now()
    duracion = round((hora_fin - hora_inicio).total_seconds() / 60, 1)

    logger.info("=" * 60)
    logger.info("RESUMEN DE SESION")
    logger.info("=" * 60)
    logger.info(f"Fuentes revisadas:    {fuentes_revisadas}")
    logger.info(f"Eventos nuevos:       {total_nuevos}")
    logger.info(f"Duplicados omitidos:  {total_omitidos}")
    logger.info(f"Fuentes con error:    {len(fuentes_con_error)}")
    logger.info(f"Sin scraper:          {len(fuentes_sin_scraper)}")
    logger.info(f"Duracion:             {duracion} min")

    if fuentes_sin_scraper:
        logger.info(f"Sin scraper configurado: {', '.join(fuentes_sin_scraper)}")
    if fuentes_con_error:
        logger.info(f"Con errores: {', '.join(fuentes_con_error)}")

    # Paso final: depurar duplicados globales por título.
    # Un mismo evento puede haber entrado varias veces desde distintas fuentes
    # (ej. IDARTES + Bogotá Agenda) o con varias funciones (mismo nombre, fechas distintas).
    # Mantenemos uno por título según prioridad estado > fecha más cercana > ID.
    logger.info("Depurando duplicados globales por titulo...")
    try:
        stats_dedup = deduplicar_por_titulo_en_sheet(spreadsheet, TAB_EVENTOS)
        logger.info(
            f"Dedup global: {stats_dedup['filas_borradas']} filas borradas en "
            f"{stats_dedup['grupos_duplicados']} grupos"
        )
    except Exception as exc:
        logger.error(f"Dedup global fallo: {exc}")
        stats_dedup = {"filas_borradas": 0, "grupos_duplicados": 0}

    escribir_log(spreadsheet, {
        "flujo": "web",
        "fecha_sesion": hora_inicio.strftime("%Y-%m-%d"),
        "hora_inicio": hora_inicio.strftime("%H:%M"),
        "hora_fin": hora_fin.strftime("%H:%M"),
        "duracion_min": duracion,
        "fuentes_revisadas": fuentes_revisadas,
        "eventos_nuevos": total_nuevos,
        "eventos_omitidos": total_omitidos + stats_dedup["filas_borradas"],
        "fuentes_con_error": ", ".join(fuentes_con_error) or "ninguna",
        "notas": (
            f"Sin scraper: {len(fuentes_sin_scraper)} fuentes · "
            f"Dedup global: {stats_dedup['filas_borradas']} borrados"
        ),
    })

    logger.info("Sesion completada. Resultados escritos en Google Sheets.")


if __name__ == "__main__":
    main()
