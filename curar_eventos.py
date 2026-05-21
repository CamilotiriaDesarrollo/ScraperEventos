"""
Curaduría de la pestaña EVENTOS:
  - Filtro A: eventos en ciudad errónea (verificado visitando el URL del evento)
  - Filtro B: eventos en línea en idioma no español
  - Filtro C: eventos en línea sin contexto local (Colombia/Bogotá/Pereira)
  - Renumeración de IDs EVT001, EVT002…

Uso: python curar_eventos.py [--dry-run]
     O importar curar_eventos(spreadsheet) desde main.py
"""
import argparse
import logging
import time

import requests

from config import TAB_EVENTOS, USER_AGENT
from sheets_client import get_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

CIUDADES_OTRAS = {
    "medellín", "medellin", "cali", "barranquilla", "cartagena",
    "bucaramanga", "manizales", "armenia", "cúcuta", "cucuta",
    "ibagué", "ibague", "santa marta", "villavicencio",
    "montería", "monteria", "pasto", "neiva", "popayán", "popayan",
    "tunja", "sincelejo", "valledupar", "riohacha", "floridablanca",
}

CIUDADES_VALIDAS = {"bogotá", "bogota", "pereira"}

TOKENS_INGLES = {
    "the", "you", "your", "our", "and", "for", "with", "this", "that",
    "are", "have", "how", "what", "will", "can", "from", "into", "join",
    "learn", "discover", "workshop", "webinar", "training", "course",
}

TOKENS_ITALIANO = {
    "dello", "della", "degli", "delle", "gestione", "formazione",
    "continua", "emozioni", "curare", "sistema", "corso", "benessere",
    "certificazione", "approccio", "psicoterapia",
}

MARCADORES_LOCALES = {
    "bogotá", "bogota", "pereira", "colombia", "colombiano",
    "colombiana", "colombianos", "colombianas",
}


# ---------------------------------------------------------------------------
# Filtros
# ---------------------------------------------------------------------------

def _es_sospechoso_ciudad(row):
    """Evento etiquetado como Bogotá/Pereira pero con nombre de otra ciudad en los campos."""
    ciudad = row.get("ciudad", "").lower().replace("bogotá", "bogota")
    if ciudad not in CIUDADES_VALIDAS:
        return False
    texto = " ".join([
        row.get("lugar", ""),
        row.get("nombre_evento", ""),
        row.get("descripcion", ""),
    ]).lower()
    return any(c in texto for c in CIUDADES_OTRAS)


def _verificar_ciudad_en_url(url, ciudad_declarada, session):
    """
    Visita el URL del evento y confirma si la ciudad real es distinta.
    Retorna el nombre de la ciudad real encontrada, o "ok" si no se puede confirmar.
    """
    try:
        resp = session.get(url, timeout=12, allow_redirects=True)
        texto = resp.text.lower()
    except Exception as e:
        logger.debug(f"No se pudo verificar {url}: {e}")
        return "ok"

    ciudad_low = ciudad_declarada.lower().replace("bogotá", "bogota")
    ciudad_en_pagina = ciudad_low in texto

    ciudad_otra = next((c for c in CIUDADES_OTRAS if c in texto), None)

    if ciudad_otra and not ciudad_en_pagina:
        return ciudad_otra
    return "ok"


def _es_idioma_no_espanol(row):
    """Evento online con título claramente en inglés o italiano."""
    if row.get("ciudad", "").lower() != "online":
        return False
    titulo = row.get("nombre_evento", "").lower()
    palabras = set(titulo.split())
    hits_en = palabras & TOKENS_INGLES
    hits_it = palabras & TOKENS_ITALIANO
    return len(hits_en) >= 2 or len(hits_it) >= 1


def _es_online_sin_contexto(row):
    """Evento online que no menciona Colombia/Bogotá/Pereira en ningún campo."""
    if row.get("ciudad", "").lower() != "online":
        return False
    texto = " ".join([
        row.get("nombre_evento", ""),
        row.get("descripcion", ""),
        row.get("lugar", ""),
        row.get("notas", ""),
    ]).lower()
    return not any(m in texto for m in MARCADORES_LOCALES)


# ---------------------------------------------------------------------------
# Función principal de curaduría
# ---------------------------------------------------------------------------

def curar_eventos(spreadsheet, dry_run=False):
    ws = spreadsheet.worksheet(TAB_EVENTOS)
    records = ws.get_all_records()

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    filas_ciudad = []
    filas_idioma = []
    filas_online = []

    total = len(records)
    logger.info(f"Analizando {total} eventos...")

    for i, row in enumerate(records):
        fila_sheet = i + 2  # fila 1 = encabezado, fila 2 = primer dato

        # Filtro A: sospechoso por ciudad → verificar visitando el URL
        if _es_sospechoso_ciudad(row):
            url = row.get("url_post", "")
            ciudad_decl = row.get("ciudad", "")
            if url:
                resultado = _verificar_ciudad_en_url(url, ciudad_decl, session)
                time.sleep(0.5)
            else:
                resultado = "ok"

            if resultado != "ok":
                filas_ciudad.append(fila_sheet)
                logger.info(
                    f"  [A] Ciudad errónea confirmada: "
                    f"{row.get('nombre_evento', '')[:50]} → real={resultado}"
                )
            continue

        # Filtro B: idioma no español (solo online)
        if _es_idioma_no_espanol(row):
            filas_idioma.append(fila_sheet)
            logger.info(f"  [B] Idioma no español: {row.get('nombre_evento', '')[:60]}")
            continue

        # Filtro C: online sin contexto local
        if _es_online_sin_contexto(row):
            filas_online.append(fila_sheet)
            logger.info(f"  [C] Online sin contexto: {row.get('nombre_evento', '')[:60]}")

    todas = sorted(set(filas_ciudad + filas_idioma + filas_online), reverse=True)

    logger.info(
        f"Resumen — A(ciudad): {len(filas_ciudad)} · "
        f"B(idioma): {len(filas_idioma)} · "
        f"C(online): {len(filas_online)} · "
        f"Total a borrar: {len(todas)}"
    )

    if dry_run:
        logger.info("[DRY RUN] No se realizaron cambios en el Sheet.")
    else:
        for fila in todas:
            ws.delete_rows(fila)
        logger.info(f"{len(todas)} filas eliminadas.")

    return {
        "ciudad_erronea": len(filas_ciudad),
        "idioma_no_espanol": len(filas_idioma),
        "online_sin_contexto": len(filas_online),
        "total_borrados": len(todas),
    }


# ---------------------------------------------------------------------------
# Renumeración de IDs
# ---------------------------------------------------------------------------

def renumerar_ids_eventos(spreadsheet):
    """Reescribe la columna 'byid' con EVT001, EVT002… en orden consecutivo."""
    ws = spreadsheet.worksheet(TAB_EVENTOS)
    rows = ws.get_all_values()
    if len(rows) < 2:
        return 0

    headers = rows[0]
    # La columna de ID puede llamarse 'byid' o 'id'
    col_idx = 0
    for nombre in ("byid", "id"):
        if nombre in headers:
            col_idx = headers.index(nombre)
            break

    col_letra = chr(ord("A") + col_idx)
    updates = []
    for i in range(1, len(rows)):
        new_id = f"EVT{i:03d}"
        updates.append({"range": f"{col_letra}{i + 1}", "values": [[new_id]]})

    if updates:
        # batch_update acepta máximo 1000 celdas por llamada; dividir si es necesario
        chunk = 500
        for j in range(0, len(updates), chunk):
            ws.batch_update(updates[j: j + chunk], value_input_option="RAW")

    ultimo = len(updates)
    logger.info(f"IDs renumerados: EVT001 … EVT{ultimo:03d}")
    return ultimo


# ---------------------------------------------------------------------------
# Punto de entrada standalone
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cura y limpia la pestaña EVENTOS.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Muestra qué borraría sin aplicar cambios.")
    parser.add_argument("--no-renumerar", action="store_true",
                        help="Omite la renumeración de IDs.")
    args = parser.parse_args()

    logger.info("Conectando a Google Sheets...")
    sp = get_client()

    stats = curar_eventos(sp, dry_run=args.dry_run)
    logger.info(f"Curaduría completada: {stats}")

    if not args.dry_run and not args.no_renumerar:
        ultimo = renumerar_ids_eventos(sp)
        logger.info(f"Renumeración completada. Último ID: EVT{ultimo:03d}")
