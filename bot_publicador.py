"""Orquesta la cola de publicación a WhatsApp.

Estrategia:
- Cola ordenada por fecha_evento ASC: continúa desde el último evento publicado.
- Intervalo 9-14 min aleatorio — igual para todas las ciudades.
- Se detiene sola a las 22:00; arrancar cuando el usuario decida.
- Cada evento se publica una sola vez; el canal es un tablero cronológico limpio.

Modos de uso:
    python bot_publicador.py --canal Bogotá --ciudad Bogota
    python bot_publicador.py --canal Pereira --ciudad Pereira

    # Test: 1 evento sin publicar realmente
    python bot_publicador.py --canal TEST --ciudad Bogotá --una-sola --dry-run --ignorar-ventana
"""
import argparse
import ctypes
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
    CANALES_ACTIVOS,
    TAB_EVENTOS,
    WA_CANALES,
    WA_INTERVALO_MAX_SEC,
    WA_INTERVALO_MAX_SEC_BOGOTA,
    WA_INTERVALO_MAX_SEC_PEREIRA,
    WA_INTERVALO_MIN_SEC,
    WA_INTERVALO_MIN_SEC_BOGOTA,
    WA_INTERVALO_MIN_SEC_PEREIRA,
    WA_SESSION_DIR,
    WA_VENTANA_HORARIA,
)
from sheets_client import actualizar_evento, get_client
from whatsapp_publisher import SesionWhatsApp, publicar

logger = logging.getLogger(__name__)

# Mínimo absoluto entre publicaciones. Por debajo de este umbral WhatsApp
# detecta spam y puede cerrar el canal. Aplica incluso al canal TEST.
INTERVALO_MINIMO_SPAM_SEG = 540  # 9 minutos

# Reintentos cuando WhatsApp Web no carga (ej: red aún reconectando tras wake-up)
REINTENTOS_MAX = 3
REINTENTO_DELAY_SEG = 90  # 90s entre intentos — suficiente para que la red reconecte

# Previene que Windows suspenda el PC mientras el bot está corriendo.
# Sin esto, el PC se duerme durante el time.sleep() entre publicaciones
# y WhatsApp Web falla al reconectar ("Conectando a WhatsApp...").
_ES_CONTINUOUS        = 0x80000000
_ES_SYSTEM_REQUIRED   = 0x00000001
_ES_AWAYMODE_REQUIRED = 0x00000040


def _prevent_sleep():
    if sys.platform == "win32":
        try:
            ctypes.windll.kernel32.SetThreadExecutionState(
                _ES_CONTINUOUS | _ES_SYSTEM_REQUIRED | _ES_AWAYMODE_REQUIRED
            )
            logger.info("Sleep prevention activo (PC no se suspenderá mientras el bot corre).")
        except Exception:
            pass


def _restore_sleep():
    if sys.platform == "win32":
        try:
            ctypes.windll.kernel32.SetThreadExecutionState(_ES_CONTINUOUS)
        except Exception:
            pass


def en_ventana_horaria(ahora=None, h_fin=None):
    h_inicio, m_inicio, h_fin_cfg, m_fin_cfg = WA_VENTANA_HORARIA
    ahora = ahora or datetime.now()
    ahora_min  = ahora.hour * 60 + ahora.minute
    inicio_min = h_inicio * 60 + m_inicio
    fin_min    = h_fin * 60 if h_fin else h_fin_cfg * 60 + m_fin_cfg
    return inicio_min <= ahora_min < fin_min


def _norm(s):
    """Normaliza ciudad: minúsculas sin tildes para comparación robusta."""
    import unicodedata
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().strip().lower()


_INTERVALOS = {
    "bogota":  (WA_INTERVALO_MIN_SEC_BOGOTA,  WA_INTERVALO_MAX_SEC_BOGOTA),
    "pereira": (WA_INTERVALO_MIN_SEC_PEREIRA, WA_INTERVALO_MAX_SEC_PEREIRA),
}


def _intervalo_ciudad(ciudad):
    return _INTERVALOS.get(_norm(ciudad), (WA_INTERVALO_MIN_SEC, WA_INTERVALO_MAX_SEC))


def cola_a_publicar(spreadsheet, ciudad):
    """Eventos aprobados de esa ciudad con +3 días de anticipación, ordenados por fecha asc."""
    from datetime import timedelta
    desde = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
    ws = spreadsheet.worksheet(TAB_EVENTOS)
    registros = ws.get_all_records()
    cola = [
        r for r in registros
        if str(r.get("estado", "")).strip().lower() == "aprobado"
        and _norm(str(r.get("ciudad", ""))) == _norm(ciudad)
        and str(r.get("fecha_evento", "")).strip() >= desde
    ]
    cola.sort(key=lambda e: (str(e.get("fecha_evento", "9999")), str(e.get("hora", ""))))
    return cola



def _publicar_uno(spreadsheet, evento, canal_url, dry_run, sesion=None, headless=True):
    eid = str(evento.get("byil", evento.get("id", "")))
    nombre = (evento.get("nombre_evento") or "")[:60]
    texto = generar_caption(evento)

    logger.info(f"--- {eid} · {nombre} ---")
    logger.info(f"--- caption ({len(texto)} chars) ---\n{texto}\n---")

    if dry_run:
        logger.info("DRY-RUN: no se publica.")
        return True

    ok = sesion.publicar(canal_url, texto) if sesion else publicar(canal_url, texto, headless=headless)
    if ok:
        actualizar_evento(spreadsheet, eid, {
            "estado": "publicado",
            "fecha_publicacion": datetime.now().strftime("%Y-%m-%d"),
        })
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

    import os
    log_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"bot_{args.ciudad.lower()}_{datetime.now().strftime('%Y%m%d')}.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )
    logger.info(f"Log: {log_file}")

    _prevent_sleep()

    # Verificar que la ciudad esté activa antes de arrancar.
    # Para cambiar: edita CANALES_ACTIVOS en config.py.
    ciudad_activa = next(
        (v for k, v in CANALES_ACTIVOS.items() if _norm(k) == _norm(args.ciudad)),
        None,
    )
    if ciudad_activa is False:
        logger.info(
            f"Ciudad '{args.ciudad}' está pausada en CANALES_ACTIVOS (config.py). "
            "Cambia a True para activarla."
        )
        return 0
    if ciudad_activa is None and args.canal != "TEST":
        logger.warning(
            f"Ciudad '{args.ciudad}' no figura en CANALES_ACTIVOS. Continuando de todas formas."
        )

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

    # ── Sesión WhatsApp persistente ────────────────────────────────────────
    # Cada ciudad usa su propio perfil de Chromium para evitar conflictos de
    # SingletonLock cuando Bogotá y Pereira corren simultáneamente.
    perfil_ciudad = WA_SESSION_DIR / f"user-data-{_norm(args.ciudad)}"
    sesion_ctx = None
    if not args.dry_run:
        for intento_sesion in range(1, REINTENTOS_MAX + 1):
            try:
                sesion_ctx = SesionWhatsApp(headless=not args.no_headless, user_data_dir=perfil_ciudad)
                sesion_ctx.__enter__()
                break
            except Exception as e:
                logger.warning(f"Sesión WA falló (intento {intento_sesion}/{REINTENTOS_MAX}): {e}")
                try:
                    sesion_ctx.__exit__(None, None, None)
                except Exception:
                    pass
                sesion_ctx = None
                if intento_sesion < REINTENTOS_MAX:
                    logger.info(f"Reintentando sesión en {REINTENTO_DELAY_SEG}s... (¿el teléfono está online?)")
                    time.sleep(REINTENTO_DELAY_SEG)
        if sesion_ctx is None:
            logger.error(
                f"No se pudo iniciar sesión WhatsApp tras {REINTENTOS_MAX} intentos. "
                "Verificar: 1) teléfono encendido con internet, 2) re-escanear QR con "
                "'python whatsapp_publisher.py --setup'."
            )
            return 1

    try:

        # ── Cola de publicación ────────────────────────────────────────────
        publicados = 0
        while True:
            h_fin_override = args.hora_fin or None
            if not args.ignorar_ventana and not en_ventana_horaria(h_fin=h_fin_override):
                h_ini, m_ini, h_fin_cfg, m_fin_cfg = WA_VENTANA_HORARIA
                fin_h = h_fin_override or h_fin_cfg
                fin_m = 0 if h_fin_override else m_fin_cfg
                logger.info(f"Fuera de la ventana horaria {h_ini:02d}:{m_ini:02d}-{fin_h:02d}:{fin_m:02d}. Saliendo.")
                return 0

            cola = cola_a_publicar(spreadsheet, args.ciudad)
            if not cola:
                logger.info(f"Cola vacía para {args.ciudad}. Nada que publicar.")
                return 0

            evento = cola[0]
            ok = False
            for intento in range(1, REINTENTOS_MAX + 1):
                ok = _publicar_uno(spreadsheet, evento, canal_url, args.dry_run,
                                   sesion=sesion_ctx)
                if ok:
                    break
                if intento < REINTENTOS_MAX:
                    logger.warning(
                        f"Intento {intento}/{REINTENTOS_MAX} fallido. "
                        f"Reintentando en {REINTENTO_DELAY_SEG}s..."
                    )
                    time.sleep(REINTENTO_DELAY_SEG)
            if not ok:
                logger.error(f"Abortando tras {REINTENTOS_MAX} intentos fallidos.")
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
                    f"Intervalo {delay:.0f}s por debajo del mínimo anti-spam "
                    f"({INTERVALO_MINIMO_SPAM_SEG}s / {INTERVALO_MINIMO_SPAM_SEG//60} min). "
                    f"Usando mínimo."
                )
                delay = INTERVALO_MINIMO_SPAM_SEG
            logger.info(f"Esperando {delay:.0f}s ({delay/60:.1f} min) antes del siguiente...")
            time.sleep(delay)
    finally:
        if sesion_ctx:
            sesion_ctx.__exit__(None, None, None)


if __name__ == "__main__":
    try:
        sys.exit(main())
    finally:
        _restore_sleep()
