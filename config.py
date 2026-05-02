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

# Ventana horaria local en la que el bot puede publicar (hora 24h)
WA_VENTANA_HORARIA = (8, 22)  # 8 AM – 10 PM

# Intervalo aleatorio entre publicaciones consecutivas
WA_INTERVALO_MIN_SEC = 25 * 60  # 25 min
WA_INTERVALO_MAX_SEC = 40 * 60  # 40 min
