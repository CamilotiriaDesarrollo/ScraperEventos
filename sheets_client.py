from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials

from config import (
    CREDENTIALS_PATH,
    SHEET_ID,
    TAB_CONTROL,
    TAB_EVENTOS,
    TAB_FUENTES_WEB,
    TAB_LOG,
)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def get_client():
    if not SHEET_ID:
        raise RuntimeError("SHEET_ID no configurado en .env")
    creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
    gc = gspread.authorize(creds)
    return gc.open_by_key(SHEET_ID)


def get_fuentes_web_activas(spreadsheet, incluir_js=False):
    ws = spreadsheet.worksheet(TAB_FUENTES_WEB)
    registros = ws.get_all_records()
    activos = ("sí", "si", "true", "1")
    fuentes = [r for r in registros if str(r.get("activo", "")).strip().lower() in activos]
    if not incluir_js:
        fuentes = [r for r in fuentes if str(r.get("requiere_js", "")).strip().lower() not in activos]
    return fuentes


def get_eventos_existentes(spreadsheet):
    ws = spreadsheet.worksheet(TAB_EVENTOS)
    registros = ws.get_all_records()
    hashes = set()
    ultimo_id = 0
    for r in registros:
        nombre = str(r.get("nombre_evento", "")).strip().lower()
        fecha = str(r.get("fecha_evento", "")).strip()
        lugar = str(r.get("lugar", "")).strip().lower()
        if nombre:
            hashes.add(f"{nombre}|{fecha}|{lugar}")
        id_str = str(r.get("byil", r.get("id", ""))).strip()
        if id_str.startswith("EVT"):
            try:
                ultimo_id = max(ultimo_id, int(id_str.replace("EVT", "")))
            except ValueError:
                pass
    return hashes, ultimo_id


def agregar_eventos(spreadsheet, eventos):
    if not eventos:
        return 0
    ws = spreadsheet.worksheet(TAB_EVENTOS)
    filas = []
    for e in eventos:
        filas.append([
            e.get("id", ""),
            e.get("fecha_extraccion", ""),
            e.get("fuente_tipo", "web"),
            e.get("fuente", "web"),
            e.get("perfil_ig", ""),
            e.get("nombre_evento", ""),
            e.get("fecha_evento", ""),
            e.get("hora", "no especificado"),
            e.get("lugar", ""),
            e.get("ciudad", ""),
            e.get("categoria", ""),
            e.get("descripcion", ""),
            e.get("url_post", ""),
            e.get("imagen_url", ""),
            e.get("estado", "pendiente"),
            e.get("notas", ""),
        ])
    ws.append_rows(filas, value_input_option="USER_ENTERED")
    return len(filas)


def actualizar_ultimo_scrape(spreadsheet, fuente_id, estado):
    ws = spreadsheet.worksheet(TAB_FUENTES_WEB)
    encabezados = ws.row_values(1)
    try:
        col_ultimo_scrape = encabezados.index("ultimo_scrape") + 1
    except ValueError:
        col_ultimo_scrape = 12
    try:
        col_ultimo_estado = encabezados.index("ultimo_estado") + 1
    except ValueError:
        col_ultimo_estado = 13

    cell = ws.find(str(fuente_id), in_column=1)
    if not cell:
        return False
    hoy = datetime.now().strftime("%Y-%m-%d")
    ws.update_cell(cell.row, col_ultimo_scrape, hoy)
    ws.update_cell(cell.row, col_ultimo_estado, estado)
    return True


def actualizar_evento(spreadsheet, event_id, campos):
    """Actualiza columnas específicas (dict {nombre_columna: valor}) del evento con id dado."""
    ws = spreadsheet.worksheet(TAB_EVENTOS)
    encabezados = ws.row_values(1)
    cell = ws.find(str(event_id), in_column=1)
    if not cell:
        return False
    fila = cell.row
    for col_nombre, valor in campos.items():
        if col_nombre not in encabezados:
            continue
        col_idx = encabezados.index(col_nombre) + 1
        ws.update_cell(fila, col_idx, valor)
    return True


def actualizar_eventos_en_lote(spreadsheet, updates_por_id):
    """
    updates_por_id: dict {event_id: {col_nombre: valor}}
    Hace un único batch_update en lugar de N update_cell. Mucho más rápido para
    operaciones masivas (ej. aprobar 50 eventos a la vez).
    """
    if not updates_por_id:
        return 0
    ws = spreadsheet.worksheet(TAB_EVENTOS)
    encabezados = ws.row_values(1)

    registros = ws.get_all_records()
    fila_por_id = {}
    for idx, r in enumerate(registros, start=2):
        eid = str(r.get("byil", r.get("id", ""))).strip()
        if eid:
            fila_por_id[eid] = idx

    from gspread.utils import rowcol_to_a1
    batch = []
    actualizados = 0
    for event_id, campos in updates_por_id.items():
        fila = fila_por_id.get(str(event_id))
        if not fila:
            continue
        for col_nombre, valor in campos.items():
            if col_nombre not in encabezados:
                continue
            col_idx = encabezados.index(col_nombre) + 1
            cell_ref = rowcol_to_a1(fila, col_idx)
            batch.append({"range": cell_ref, "values": [[valor]]})
        actualizados += 1

    if batch:
        ws.batch_update(batch, value_input_option="USER_ENTERED")
    return actualizados


def get_control(spreadsheet):
    """Devuelve los registros de la pestaña CONTROL."""
    ws = spreadsheet.worksheet(TAB_CONTROL)
    return ws.get_all_records()


def actualizar_control(spreadsheet, ciudad, campos):
    """Actualiza columnas del registro de `ciudad` en la pestaña CONTROL."""
    ws = spreadsheet.worksheet(TAB_CONTROL)
    encabezados = ws.row_values(1)
    registros = ws.get_all_records()
    for idx, row in enumerate(registros, start=2):
        if str(row.get("ciudad", "")).strip() == ciudad:
            for col_nombre, valor in campos.items():
                if col_nombre in encabezados:
                    ws.update_cell(idx, encabezados.index(col_nombre) + 1, valor)
            return True
    return False


def escribir_log(spreadsheet, log_data):
    ws = spreadsheet.worksheet(TAB_LOG)
    ws.append_row([
        log_data.get("flujo", "web"),
        log_data.get("fecha_sesion", ""),
        log_data.get("hora_inicio", ""),
        log_data.get("hora_fin", ""),
        log_data.get("duracion_min", ""),
        log_data.get("fuentes_revisadas", 0),
        log_data.get("eventos_nuevos", 0),
        log_data.get("eventos_omitidos", 0),
        log_data.get("fuentes_con_error", ""),
        log_data.get("notas", ""),
    ], value_input_option="USER_ENTERED")
