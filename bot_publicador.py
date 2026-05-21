"""Orquesta la cola de publicación a WhatsApp.

Estrategia de cobertura total:
- Bogotá:  intervalo ~20 min → hasta 42 publicaciones/día (cubre 200-250 eventos/semana)
- Pereira: intervalo ~60 min → hasta 14 publicaciones/día (cubre 50-100 eventos/semana)
- Cola ordenada por fecha_evento ASC (más cercanos primero)
- Alerta HOY: a las 9 AM publica copy de urgencia para eventos que ocurren ese día

Modos de uso:
    # Cola completa (corre todo el día, se autolimita a las 10 PM)
    python bot_publicador.py --canal "Eventos Bogotá" --ciudad Bogotá
    python bot_publicador.py --canal "Eventos Pereira" --ciudad Pereira

    # Solo alertas del día (correr a las 9 AM antes de la cola normal)
    python bot_publicador.py --canal "Eventos Bogotá" --ciudad Bogotá --alertas

    # Test: 1 evento sin publicar realmente
    python bot_publicador.py --canal TEST --ciudad Bogotá --una-sola --dry-run --ignorar-ventana
"""
import argparse
import logging
import random
import sys
import time
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from caption import generar_caption, generar_caption_alerta
from config import (
    TAB_EVENTOS,
    WA_CANALES,
    WA_INTERVALO_MAX_SEC,
    WA_INTERVALO_MAX_SEC_BOGOTA,
    WA_INTERVALO_MAX_SEC_PEREIRA,
    WA_INTERVALO_MIN_SEC,
    WA_INTERVALO_MIN_SEC_BOGOTA,
    WA_INTERVALO_MIN_SEC_PEREIRA,
    WA_VENTANA_HORARIA,
)
from sheets_client import actualizar_evento, get_client
from whatsapp_publisher import publicar

logger = logging.getLogger(__name__)

_INTERVALOS = {
    "bogotá": (WA_INTERVALO_MIN_SEC_BOGOTA, WA_INTERVALO_MAX_SEC_BOGOTA),
    "bogota": (WA_INTERVALO_MIN_SEC_BOGOTA, WA_INTERVALO_MAX_SEC_BOGOTA),
    "pereira": (WA_INTERVALO_MIN_SEC_PEREIRA, WA_INTERVALO_MAX_SEC_PEREIRA),
}


def _intervalo_ciudad(ciudad):
    return _INTERVALOS.get(ciudad.strip().lower(), (WA_INTERVALO_MIN_SEC, WA_INTERVALO_MAX_SEC))


def en_ventana_horaria(ahora=None):
    h_inicio, h_fin = WA_VENTANA_HORARIA
    h = (ahora or datetime.now()).hour
    return h_inicio <= h < h_fin


def cola_a_publicar(spreadsheet, ciudad):
    """Eventos aprobados de esa ciudad, ordenados por fecha asc (más cercanos primero)."""
    ws = spreadsheet.worksheet(TAB_EVENTOS)
    registros = ws.get_all_records()
    cola = [
        r for r in registros
        if str(r.get("estado", "")).strip().lower() == "aprobado"
        and str(r.get("ciudad", "")).strip().lower() == ciudad.strip().lower()
    ]
    cola.sort(key=lambda e: (str(e.get("fecha_evento", "9999")), str(e.get("hora", ""))))
    return cola


def cola_alertas_hoy(spreadsheet, ciudad):
    """Eventos que ocurren hoy y ya fueron publicados normalmente (estado=publicado)."""
    hoy = datetime.now().strftime("%Y-%m-%d")
    ws = spreadsheet.worksheet(TAB_EVENTOS)
    registros = ws.get_all_records()
    alertas = [
        r for r in registros
        if str(r.get("estado", "")).strip().lower() == "publicado"
        and str(r.get("fecha_evento", "")).strip() == hoy
        and str(r.get("ciudad", "")).strip().lower() == ciudad.strip().lower()
    ]
    alertas.sort(key=lambda e: str(e.get("hora", "")))
    return alertas


def _publicar_uno(spreadsheet, evento, canal_url, dry_run, headless=True):
    eid = str(evento.get("id", ""))
    nombre = (evento.get("nombre_evento") or "")[:60]
    texto = generar_caption(evento)

    logger.info(f"--- {eid} · {nombre} ---")
    logger.info(f"--- caption ({len(texto)} chars) ---\n{texto}\n---")

    if dry_run:
        logger.info("DRY-RUN: no se publica.")
        return True

    ok = publicar(canal_url, texto, headless=headless)
    if ok:
        actualizar_evento(spreadsheet, eid, {"estado": "publicado"})
        logger.info(f"✅ {eid} publicado.")
    else:
        logger.error(f"❌ Falló la publicación de {eid}.")
    return ok


def _publicar_alerta(spreadsheet, evento, canal_url, dry_run, headless=True):
    eid = str(evento.get("id", ""))
    nombre = (evento.get("nombre_evento") or "")[:60]
    texto = generar_caption_alerta(evento)

    logger.info(f"--- ALERTA HOY {eid} · {nombre} ---")
    logger.info(f"--- caption ({len(texto)} chars) ---\n{texto}\n---")

    if dry_run:
        logger.info("DRY-RUN: no se publica alerta.")
        return True

    ok = publicar(canal_url, texto, headless=headless)
    if ok:
        actualizar_evento(spreadsheet, eid, {"estado": "alerta_hoy"})
        logger.info(f"✅ {eid} alerta_hoy publicada.")
    else:
        logger.error(f"❌ Falló la alerta de {eid}.")
    return ok


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--canal", default="TEST", help="Nombre del canal en WA_CANALES")
    parser.add_argument("--ciudad", default="Bogotá", help="Ciudad a publicar (Bogotá / Pereira)")
    parser.add_argument("--alertas", action="store_true",
                        help="Modo alertas: publica solo los eventos de HOY (estado=publicado) y sale")
    parser.add_argument("--una-sola", action="store_true", help="Publica solo 1 evento y sale")
    parser.add_argument("--n", type=int, default=0,
                        help="Publica N eventos y sale (testing). 0 = ilimitado (modo cola).")
    parser.add_argument("--intervalo", type=int, default=0,
                        help="Override del intervalo en segundos. 0 = usa intervalo por ciudad.")
    parser.add_argument("--dry-run", action="store_true", help="No publica, solo muestra el caption")
    parser.add_argument("--ignorar-ventana", action="store_true",
                        help="Permite publicar fuera de la ventana horaria (testing)")
    parser.add_argument("--no-headless", action="store_true",
                        help="Mostrar el navegador (debug)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    canal_url = WA_CANALES.get(args.canal, "")
    if not canal_url and not args.dry_run:
        logger.error(f"Canal '{args.canal}' no tiene URL configurada en WA_CANALES.")
        return 2

    spreadsheet = get_client()
    intervalo_min, intervalo_max = _intervalo_ciudad(args.ciudad)

    # ── Modo alertas: publica los HOY de la ciudad y sale ─────────────────
    if args.alertas:
        alertas = cola_alertas_hoy(spreadsheet, args.ciudad)
        if not alertas:
            logger.info(f"Sin alertas para hoy en {args.ciudad}.")
            return 0
        logger.info(f"{len(alertas)} alertas para hoy en {args.ciudad}.")
        for evento in alertas:
            _publicar_alerta(spreadsheet, evento, canal_url, args.dry_run,
                             headless=not args.no_headless)
        return 0

    # ── Modo cola normal ───────────────────────────────────────────────────
    publicados = 0
    while True:
        if not args.ignorar_ventana and not en_ventana_horaria():
            h_ini, h_fin = WA_VENTANA_HORARIA
            logger.info(f"Fuera de la ventana horaria {h_ini:02d}:00–{h_fin:02d}:00. Saliendo.")
            return 0

        cola = cola_a_publicar(spreadsheet, args.ciudad)
        if not cola:
            logger.info(f"Cola vacía para {args.ciudad}. Nada que publicar.")
            return 0

        evento = cola[0]
        ok = _publicar_uno(spreadsheet, evento, canal_url, args.dry_run,
                           headless=not args.no_headless)
        if not ok:
            logger.error("Abortando por fallo de publicación.")
            return 1

        publicados += 1
        if args.una_sola:
            return 0
        if args.n and publicados >= args.n:
            logger.info(f"Alcancé el límite de {args.n} publicaciones.")
            return 0

        delay = args.intervalo if args.intervalo else random.uniform(intervalo_min, intervalo_max)
        logger.info(f"Esperando {delay:.0f}s ({delay/60:.1f} min) antes del siguiente...")
        time.sleep(delay)


if __name__ == "__main__":
    sys.exit(main())
