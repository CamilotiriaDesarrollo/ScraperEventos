import time
import unicodedata
from collections import defaultdict


def generar_hash(nombre, fecha, lugar):
    nombre = str(nombre).strip().lower()
    fecha = str(fecha).strip()
    lugar = str(lugar).strip().lower()
    return f"{nombre}|{fecha}|{lugar}"


def es_duplicado(evento, hashes_existentes):
    h = generar_hash(
        evento.get("nombre_evento", ""),
        evento.get("fecha_evento", ""),
        evento.get("lugar", ""),
    )
    return h in hashes_existentes


def normalizar_titulo(texto):
    if not texto:
        return ""
    texto = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode("ascii")
    return " ".join(texto.lower().strip().split())


_PRIORIDAD_ESTADO = {"aprobado": 0, "publicado": 1, "pendiente": 2, "rechazado": 3}


def _ranking_para_mantener(registro):
    """Tupla de orden — el primero (menor) es el que se conserva."""
    estado = str(registro.get("estado", "")).strip().lower() or "pendiente"
    prioridad = _PRIORIDAD_ESTADO.get(estado, 99)
    fecha = str(registro.get("fecha_evento", "9999")).strip() or "9999"
    id_str = str(registro.get("id", "ZZZZ")).strip() or "ZZZZ"
    return (prioridad, fecha, id_str)


def deduplicar_por_titulo_en_sheet(spreadsheet, sheet_name, dry_run=False):
    """
    Recorre la pestaña, agrupa por título normalizado y borra duplicados
    manteniendo uno por grupo según el ranking (estado > fecha más cercana > ID).

    Returns: dict con stats {grupos_duplicados, filas_borradas, ids_borrados}.
    Si dry_run=True no toca el Sheet.
    """
    ws = spreadsheet.worksheet(sheet_name)
    registros = ws.get_all_records()

    grupos = defaultdict(list)
    for idx, r in enumerate(registros, start=2):  # fila 1 = header
        clave = normalizar_titulo(r.get("nombre_evento", ""))
        if not clave:
            continue
        grupos[clave].append((idx, r))

    filas_a_borrar = []
    ids_borrados = []
    for clave, items in grupos.items():
        if len(items) <= 1:
            continue
        items_orden = sorted(items, key=lambda it: _ranking_para_mantener(it[1]))
        for fila, registro in items_orden[1:]:
            filas_a_borrar.append(fila)
            ids_borrados.append(registro.get("id", ""))

    stats = {
        "grupos_duplicados": sum(1 for v in grupos.values() if len(v) > 1),
        "filas_borradas": len(filas_a_borrar),
        "ids_borrados": ids_borrados,
    }

    if dry_run or not filas_a_borrar:
        return stats

    # Borrar de abajo hacia arriba en rangos contiguos
    filas_a_borrar.sort(reverse=True)
    rangos = []
    inicio = fin = filas_a_borrar[0]
    for n in filas_a_borrar[1:]:
        if n == fin - 1:
            fin = n
        else:
            rangos.append((fin, inicio))
            inicio = fin = n
    rangos.append((fin, inicio))

    for i, (start, end) in enumerate(rangos, 1):
        ws.delete_rows(start, end)
        if i % 20 == 0:
            time.sleep(2)

    return stats
