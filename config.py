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

# Ventana horaria local en la que el bot puede publicar
# Formato: (hora_inicio, min_inicio, hora_fin, min_fin)
WA_VENTANA_HORARIA = (8, 30, 20, 30)  # 8:30 AM – 8:30 PM

# Intervalos por ciudad (segundos entre publicaciones consecutivas)
# Bogotá: ~200-250 eventos/semana → intervalo corto para cubrir todo
WA_INTERVALO_MIN_SEC_BOGOTA = 14 * 60   # 14 min
WA_INTERVALO_MAX_SEC_BOGOTA = 16 * 60   # 16 min

# Burst matutino: eventos de HOY se publican rápido para cubrir el día temprano
WA_INTERVALO_MIN_SEC_BURST = 6 * 60     # 6 min
WA_INTERVALO_MAX_SEC_BURST = 8 * 60     # 8 min

# Pereira: ~50-100 eventos/semana → intervalo más largo
WA_INTERVALO_MIN_SEC_PEREIRA = 55 * 60  # 55 min
WA_INTERVALO_MAX_SEC_PEREIRA = 70 * 60  # 70 min

# Fallback para ciudades no configuradas
WA_INTERVALO_MIN_SEC = 19 * 60
WA_INTERVALO_MAX_SEC = 22 * 60
