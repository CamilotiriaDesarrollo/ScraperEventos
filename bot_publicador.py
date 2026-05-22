"""Orquesta la cola de publicación a WhatsApp.

Estrategia:
- Cola ordenada por fecha_evento ASC: hoy primero, mañana después, etc.
- Bogotá:  intervalo ~20 min (8 AM – 10 PM)
- Pereira: intervalo ~60 min (8 AM – 10 PM)
- Cada evento se publica una sola vez; el canal es un tablero cronológico limpio.

Modos de uso:
    # Cola completa (arranca a las 8 AM, se detiene sola a las 10 PM)
    python bot_publicador.py --canal "Plan :D - Bogotá" --ciudad Bogotá
    python bot_publicador.py --canal "Plan :D Pereira"  --ciudad Pereira

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

from caption import generar_caption
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

# Mínimo absoluto entre publicaciones. Por debajo de este umbral WhatsApp
# detecta spam y puede cerrar el canal. Aplica incluso al canal TEST.
INTERVALO_MINIMO_SPAM_SEG = 600  # 10 minutos

_INTERVALOS = {
    "bogota": (WA_INTERVALO_MIN_SEC_BOGOTA, WA_INTERVALO_MAX_SEC_BOGOTA),
    "pereira": (WA_INTERVALO_MIN_SEC_PEREIRA, WA_INTERVALO_MAX_SEC_PEREIRA),
}


def _intervalo_ciudad(ciudad):
    return _INTERVALOS.get(_norm(ciudad), (WA_INTERVALO_MIN_SEC, WA_INTERVALO_MAX_SEC))


def en_ventana_horaria(ahora=None, h_fin=None):
    h_inicio, h_fin_cfg = WA_VENTANA_HORARIA
    h = (ahora or datetime.now()).hour
    fin = h_fin if h_fin else h_fin_cfg
    return h_inicio <= h < fin


def _norm(s):
    """Normaliza ciudad: minúsculas sin tildes para comparación robusta."""
    import unicodedata
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().strip().lower()


def cola_a_publicar(spreadsheet, ciudad):
    """Eventos aprobados de esa ciudad desde hoy, ordenados por fecha asc."""
    hoy = datetime.now().strftime("%Y-%m-%d")
    ws = spreadsheet.worksheet(TAB_EVENTOS)
    registros = ws.get_all_records()
    cola = [
        r for r in registros
        if str(r.get("estado", "")).strip().lower() == "aprobado"
        and _norm(str(r.get("ciudad", ""))) == _norm(ciudad)
        and str(r.get("fecha_evento", "")).strip() >= hoy
    ]
    cola.sort(key=lambda e: (str(e.get("fecha_evento", "9999")), str(e.get("hora", ""))))
    return cola



def _publicar_uno(spreadsheet, evento, canal_url, dry_run, headless=True):
    eid = str(evento.get("byil", evento.get("id", "")))
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



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--canal", default="TEST", help="Nombre del canal en WA_CANALES")
    parser.add_argument("--ciudad", default="Bogotá", help="Ciudad a publicar (Bogotá / Pereira)")
    parser.add_argument("--una-sola", action="store_true", help="Publica solo 1 evento y sale")
    parser.add_argument("--n", type=int, default=0,
                        help="Publica N eventos y sale (testing). 0 = ilimitado (modo cola).")
    parser.add_argument("--intervalo", type=int, default=0,
                        help="Override del intervalo en segundos. 0 = usa intervalo por ciudad.")
    parser.add_argument("--dry-run", action="store_true", help="No publica, solo muestra el caption")
    parser.add_argument("--hora-fin", type=int, default=0,
                        help="Hora (0-23) en que el bot se detiene. 0 = usa WA_VENTANA_HORARIA[1]")
    parser.add_argument("--ignorar-ventana", action="store_true",
                        help="Permite publicar fuera de la ventana horaria (testing)")
    parser.add_argument("--no-headless", action="store_true",
                        help="Mostrar el navegador (debug)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    canal_url = WA_CANALES.get(args.canal, "")
    if not canal_url:
        for k, v in WA_CANALES.items():
            if _norm(k) == _norm(args.canal):
                canal_url = v
                break
    if not canal_url and not args.dry_run:
        logger.error(f"Canal '{args.canal}' no tiene URL configurada en WA_CANALES.")
        return 2

    spreadsheet = get_client()
    intervalo_min, intervalo_max = _intervalo_ciudad(args.ciudad)

    # ── Cola de publicación ────────────────────────────────────────────────
    publicados = 0
    while True:
        h_fin_override = args.hora_fin or None
        if not args.ignorar_ventana and not en_ventana_horaria(h_fin=h_fin_override):
            h_ini, h_fin_cfg = WA_VENTANA_HORARIA
            fin = h_fin_override or h_fin_cfg
            logger.info(f"Fuera de la ventana horaria {h_ini:02d}:00-{fin:02d}:00. Saliendo.")
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
        if delay < INTERVALO_MINIMO_SPAM_SEG:
            logger.warning(
                f"Intervalo {delay:.0f}s está por debajo del mínimo anti-spam "
                f"({INTERVALO_MINIMO_SPAM_SEG}s / {INTERVALO_MINIMO_SPAM_SEG//60} min). "
                f"Usando mínimo para proteger el canal."
            )
            delay = INTERVALO_MINIMO_SPAM_SEG
        logger.info(f"Esperando {delay:.0f}s ({delay/60:.1f} min) antes del siguiente...")
        time.sleep(delay)


if __name__ == "__main__":
    sys.exit(main())
