from config import TAB_EVENTOS, TAB_FUENTES_WEB
from sheets_client import get_client


def _rangos_contiguos(filas):
    """Agrupa lista de filas en rangos [inicio, fin] para borrado batch."""
    if not filas:
        return []
    filas = sorted(filas)
    rangos = []
    inicio = fin = filas[0]
    for f in filas[1:]:
        if f == fin + 1:
            fin = f
        else:
            rangos.append((inicio, fin))
            inicio = fin = f
    rangos.append((inicio, fin))
    return rangos


def limpiar_eventos_web():
    print("Conectando al Sheet...")
    spreadsheet = get_client()
    ws = spreadsheet.worksheet(TAB_EVENTOS)

    todos = ws.get_all_values()
    if not todos:
        print("La pestaña EVENTOS está vacía.")
        return

    headers = todos[0]
    col_fuente_tipo = headers.index("fuente_tipo")

    filas_a_borrar = [
        i + 2  # fila real en Sheet: +1 por 0-based, +1 por la fila de headers
        for i, row in enumerate(todos[1:])
        if len(row) > col_fuente_tipo and row[col_fuente_tipo].strip().lower() == "web"
    ]

    ig_count = sum(
        1 for row in todos[1:]
        if len(row) > col_fuente_tipo and row[col_fuente_tipo].strip().lower() == "instagram"
    )

    print(f"Eventos Instagram encontrados (se conservan): {ig_count}")
    print(f"Eventos web a borrar: {len(filas_a_borrar)}")

    if not filas_a_borrar:
        print("No hay eventos web para borrar.")
        return

    # Borrar de abajo hacia arriba en rangos contiguos (más eficiente)
    rangos = _rangos_contiguos(filas_a_borrar)
    for inicio, fin in reversed(rangos):
        ws.delete_rows(inicio, fin)
        print(f"  Borradas filas {inicio}–{fin} ({fin - inicio + 1} filas)")

    print(f"\nListo. {len(filas_a_borrar)} eventos web eliminados.")

    # Resetear ultimo_scrape y ultimo_estado en FUENTES_WEB
    print("\nReseteando FUENTES_WEB...")
    ws_fuentes = spreadsheet.worksheet(TAB_FUENTES_WEB)
    fuentes = ws_fuentes.get_all_values()
    if not fuentes:
        return

    headers_f = fuentes[0]
    col_scrape = headers_f.index("ultimo_scrape") if "ultimo_scrape" in headers_f else None
    col_estado = headers_f.index("ultimo_estado") if "ultimo_estado" in headers_f else None

    if col_scrape is None and col_estado is None:
        print("No se encontraron columnas ultimo_scrape / ultimo_estado en FUENTES_WEB.")
        return

    updates = []
    for i in range(1, len(fuentes)):
        fila_sheet = i + 1
        if col_scrape is not None:
            updates.append({"range": f"{_col_letra(col_scrape + 1)}{fila_sheet}", "values": [[""]]})
        if col_estado is not None:
            updates.append({"range": f"{_col_letra(col_estado + 1)}{fila_sheet}", "values": [[""]]})

    if updates:
        ws_fuentes.batch_update(updates, value_input_option="RAW")
        print(f"ultimo_scrape y ultimo_estado reseteados en {len(fuentes) - 1} fuentes.")


def _col_letra(n):
    """Convierte número de columna (1-based) a letra(s): 1→A, 26→Z, 27→AA."""
    result = ""
    while n:
        n, rem = divmod(n - 1, 26)
        result = chr(65 + rem) + result
    return result


if __name__ == "__main__":
    limpiar_eventos_web()
