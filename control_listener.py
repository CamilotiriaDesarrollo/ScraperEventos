"""Listener de control remoto.

Corre cada minuto via Task Scheduler (PlanD_ControlListener).
Lee la pestaña CONTROL del Sheet, sincroniza canal_state.json,
y arranca/detiene bot_publicador.py según los comandos recibidos.

Uso manual (prueba):
    python control_listener.py
"""
import json
import logging
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PYTHON   = r"C:\Users\camil\AppData\Local\Programs\Python\Python310\python.exe"
BOT      = str(BASE_DIR / "bot_publicador.py")

_log_dir = BASE_DIR / "logs"
_log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(_log_dir / "listener.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# Columnas esperadas en la pestaña CONTROL
_COLUMNAS_CONTROL = ["ciudad", "activo", "comando", "bot_pid", "bot_estado"]


def _asegurar_pestaña(spreadsheet):
    """Crea la pestaña CONTROL con encabezados si no existe."""
    from config import TAB_CONTROL
    try:
        spreadsheet.worksheet(TAB_CONTROL)
    except Exception:
        ws = spreadsheet.add_worksheet(title=TAB_CONTROL, rows=10, cols=6)
        ws.append_row(_COLUMNAS_CONTROL)
        ws.append_row(["Bogotá",  "TRUE",  "", "", "detenido"])
        ws.append_row(["Pereira", "FALSE", "", "", "detenido"])
        logger.info("Pestaña CONTROL creada con filas iniciales.")


def _pid_corriendo(pid):
    if not pid:
        return False
    try:
        r = subprocess.run(
            ["tasklist", "/FI", f"PID eq {int(pid)}", "/NH"],
            capture_output=True, text=True, encoding="cp850",
        )
        return str(int(pid)) in r.stdout
    except Exception:
        return False


def _matar(pid):
    try:
        subprocess.run(["taskkill", "/PID", str(int(pid)), "/F"], capture_output=True)
        logger.info(f"PID {pid} terminado.")
    except Exception as e:
        logger.warning(f"No se pudo terminar PID {pid}: {e}")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    from sheets_client import get_client
    from config import TAB_CONTROL

    sp = get_client()
    _asegurar_pestaña(sp)

    ws   = sp.worksheet(TAB_CONTROL)
    rows = ws.get_all_records()
    enc  = ws.row_values(1)

    def col(name):
        return enc.index(name) + 1

    canal_state = {}

    for idx, row in enumerate(rows, start=2):
        ciudad = str(row.get("ciudad", "")).strip()
        if not ciudad:
            continue

        activo  = str(row.get("activo",  "")).lower() in ("true", "1", "si", "sí")
        comando = str(row.get("comando", "")).strip().lower()
        try:
            pid = int(row.get("bot_pid") or 0)
        except (ValueError, TypeError):
            pid = 0

        canal_state[ciudad] = activo
        corriendo = _pid_corriendo(pid)

        if comando == "arrancar":
            if not corriendo and activo:
                proc = subprocess.Popen(
                    [PYTHON, BOT, "--canal", ciudad, "--ciudad", ciudad],
                    cwd=str(BASE_DIR),
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                pid = proc.pid
                corriendo = True
                logger.info(f"Bot {ciudad} iniciado PID={pid}")
            elif corriendo:
                logger.info(f"Bot {ciudad} ya corre (PID={pid}), arrancar ignorado.")
            else:
                logger.warning(f"Arrancar {ciudad}: canal pausado, ignorado.")
            ws.update_cell(idx, col("comando"), "")
            ws.update_cell(idx, col("bot_pid"), pid or "")

        elif comando == "detener":
            if corriendo:
                _matar(pid)
            corriendo = False
            pid = ""
            ws.update_cell(idx, col("comando"), "")
            ws.update_cell(idx, col("bot_pid"), "")

        ws.update_cell(idx, col("bot_estado"), "corriendo" if corriendo else "detenido")

    state_file = BASE_DIR / "canal_state.json"
    state_file.write_text(
        json.dumps(canal_state, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info(f"canal_state.json → {canal_state}")


if __name__ == "__main__":
    main()
