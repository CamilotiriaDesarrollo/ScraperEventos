"""
Limpia FUENTES_WEB eliminando fuentes no viables y reordena los F-IDs.
Uso: python limpiar_fuentes.py [--dry-run]
"""
import argparse
import logging
import sys

from config import TAB_FUENTES_WEB
from sheets_client import get_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DOMINIOS_NO_VIABLES = {
    "banrepcultural.org/bogota",
    "museonacional.gov.co/eventos",
    "teatrocolon.gov.co",
    "jbb.gov.co",
    "agora-bogota.com",
    "corferias.com",
    "parque93.com",
    "pereira.gov.co/calendario",
    "pereira.gov.co/cultura",
    "casaeborrero.com",
    "royalcenter.com.co",
    "blog.utp.edu.co/cultura",
    "comunicaciones.utp.edu.co",
    "pereiravirtual.com",
    "elretirobogota.com/eventos",
    "alianzafrancesa.edu.co/cultura",
    "teatropetra.com",
    "colombia.travel/lucy-tejada",
    "risaralda.gov.co/cultura",
    "eldiario.com.co",
}


def limpiar_fuentes_no_viables(spreadsheet, dry_run=False):
    ws = spreadsheet.worksheet(TAB_FUENTES_WEB)
    rows = ws.get_all_values()
    if not rows:
        logger.warning("FUENTES_WEB está vacía.")
        return {"filas_borradas": 0}

    headers = rows[0]
    try:
        idx_dominio = headers.index("dominio")
    except ValueError:
        logger.error("No se encontró columna 'dominio' en FUENTES_WEB.")
        return {"filas_borradas": 0}

    filas_borrar = []
    for i, row in enumerate(rows[1:], start=2):
        dominio = row[idx_dominio] if idx_dominio < len(row) else ""
        if dominio in DOMINIOS_NO_VIABLES:
            filas_borrar.append((i, dominio))

    logger.info(f"Fuentes no viables encontradas: {len(filas_borrar)}")
    for fila, dom in filas_borrar:
        logger.info(f"  Fila {fila}: {dom}")

    if dry_run:
        logger.info("[DRY RUN] No se realizaron cambios.")
        return {"filas_borradas": len(filas_borrar)}

    # Borrar de abajo hacia arriba para no desplazar índices
    for fila, _ in reversed(filas_borrar):
        ws.delete_rows(fila)
    logger.info(f"{len(filas_borrar)} filas eliminadas.")

    # Renumerar F-IDs
    rows_after = ws.get_all_values()
    if len(rows_after) < 2:
        return {"filas_borradas": len(filas_borrar)}

    updates = []
    for i, _ in enumerate(rows_after[1:], start=1):
        new_id = f"F{i:03d}"
        updates.append({"range": f"A{i + 1}", "values": [[new_id]]})

    if updates:
        ws.batch_update(updates, value_input_option="RAW")
        logger.info(f"IDs renumerados: F001 … F{len(updates):03d}")

    return {"filas_borradas": len(filas_borrar)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Limpia fuentes no viables de FUENTES_WEB.")
    parser.add_argument("--dry-run", action="store_true", help="Muestra qué borraría sin aplicar cambios.")
    args = parser.parse_args()

    logger.info("Conectando a Google Sheets...")
    sp = get_client()
    stats = limpiar_fuentes_no_viables(sp, dry_run=args.dry_run)
    logger.info(f"Resultado: {stats}")
