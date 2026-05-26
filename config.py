import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

SHEET_ID = os.getenv("SHEET_ID")
CREDENTIALS_PATH = str(BASE_DIR / "credentials" / "service-account.json")

TAB_EVENTOS = "EVENTOS"
TAB_FUENTES_WEB = "FUENTES_WEB"
TAB_LOG = "LOG"
TAB_CONTROL = "CONTROL"

REQUEST_TIMEOUT = 15
DELAY_BETWEEN_REQUESTS = 3
MAX_RETRIES = 2

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/121.0.0.0 Safari/537.36"
)

CATEGORIAS_VALIDAS = [
    "concierto", "teatro", "danza", "exposicion", "taller",
    "festival", "fiesta", "cine", "gastronomia", "feria",
    "conversatorio", "stand-up", "lanzamiento", "mercado",
]

# === FASE 5 — Bot publicador a canales de WhatsApp ===
WA_SESSION_DIR = BASE_DIR / "wa_session"  # storage_state.json persistente

# Nombres EXACTOS de los canales de WhatsApp tal como aparecen en la pestaña
# "Canales" de WhatsApp Web. El bot navega: sidebar Canales > click en este nombre.
# Las URLs públicas (whatsapp.com/channel/<id>) NO funcionan como deep link en WA Web.
WA_CANALES = {
    "TEST": os.getenv("WA_CANAL_TEST", ""),
    "Bogotá": os.getenv("WA_CANAL_BOGOTA", ""),
    "Pereira": os.getenv("WA_CANAL_PEREIRA", ""),
}

# Ciudades habilitadas para publicar.
# El estado se gestiona desde el dashboard (canal_state.json) — no editar aquí.
import json as _json
_CANAL_STATE_FILE = BASE_DIR / "canal_state.json"
try:
    with open(_CANAL_STATE_FILE, encoding="utf-8") as _f:
        CANALES_ACTIVOS = _json.load(_f)
except Exception:
    CANALES_ACTIVOS = {"Bogotá": True, "Pereira": False}

# Ventana horaria local en la que el bot puede publicar
# Formato: (hora_inicio, min_inicio, hora_fin, min_fin)
# Inicio en 0:00 = el bot arranca cuando el usuario lo lance; se detiene solo a las 22:00.
WA_VENTANA_HORARIA = (0, 0, 22, 0)  # cualquier hora – 10 PM

# Intervalos por ciudad — calculados para agotar la semana en 6 días (11h/día)
WA_INTERVALO_MIN_SEC_BOGOTA  = 35 * 60   # 35 min
WA_INTERVALO_MAX_SEC_BOGOTA  = 45 * 60   # 45 min

WA_INTERVALO_MIN_SEC_PEREIRA = 65 * 60   # 65 min
WA_INTERVALO_MAX_SEC_PEREIRA = 80 * 60   # 80 min

# Fallback para ciudades no configuradas
WA_INTERVALO_MIN_SEC = 35 * 60
WA_INTERVALO_MAX_SEC = 45 * 60
