"""
Importa eventos desde el JSON de salida de Claude in Chrome al Google Sheet.

Uso:
    python importar_eventos_ig.py sesion_output.json

Qué hace:
    1. Lee el JSON generado por Claude
    2. Deduplica contra eventos existentes en el Sheet
    3. Escribe los eventos nuevos en la pestaña EVENTOS
    4. Actualiza ultima_revision en FUENTES_IG para los perfiles revisados
    5. Escribe una entrada en el LOG
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from deduplicator import es_duplicado, generar_hash
from sheets_client import agregar_eventos, escribir_log, get_client, get_eventos_existentes

TAB_FUENTES_IG = "FUENTES_IG"
CIUDADES_PERMITIDAS = {"bogotá", "bogota", "pereira", "online"}


def normalizar_ciudad(ciudad):
    c = str(ciudad).strip().lower()
    if c in ("bogotá", "bogota"):
        return "Bogotá"
    if c == "pereira":
        return "Pereira"
    if c == "online":
        return "online"
    return None


def actualizar_ultima_revision(spreadsheet, perfiles_revisados, fecha):
    if not perfiles_revisados:
        return 0

    ws = spreadsheet.worksheet(TAB_FUENTES_IG)
    encabezados = ws.row_values(1)

    if "ultima_revision" not in encabezados:
        print("⚠  Columna ultima_revision no encontrada en FUENTES_IG")
        return 0
    if "perfil" not in encabezados:
        print("⚠  Columna perfil no encontrada en FUENTES_IG")
        return 0

    col_rev = encabezados.index("ultima_revision") + 1
    col_perfil = encabezados.index("perfil") + 1

    todos = ws.get_all_values()
    perfiles_set = {p.strip().lower() for p in perfiles_revisados}

    from gspread.utils import rowcol_to_a1

    batch = []
    for i, fila in enumerate(todos[1:], start=2):
        perfil = fila[col_perfil - 1].strip().lower() if len(fila) >= col_perfil else ""
        if perfil in perfiles_set:
            batch.append({"range": rowcol_to_a1(i, col_rev), "values": [[fecha]]})

    if batch:
        ws.batch_update(batch, value_input_option="USER_ENTERED")

    return len(batch)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("archivo_json", help="Archivo JSON con la salida de Claude")
    args = parser.parse_args()

    ruta = Path(args.archivo_json)
    if not ruta.exists():
        print(f"Error: no se encontró el archivo '{ruta}'")
        sys.exit(1)

    with open(ruta, encoding="utf-8") as f:
        datos = json.load(f)

    hoy = datetime.now().strftime("%Y-%m-%d")
    fecha_sesion = datos.get("fecha_sesion", hoy)
    perfiles_revisados = datos.get("perfiles_revisados", [])
    eventos_raw = datos.get("eventos", [])
    perfiles_sin_eventos = datos.get("perfiles_sin_eventos", [])
    perfiles_con_error = datos.get("perfiles_con_error", [])

    print(f"Conectando al Sheet...")
    spreadsheet = get_client()

    hashes_existentes, ultimo_id = get_eventos_existentes(spreadsheet)
    print(f"Eventos existentes: {len(hashes_existentes)} | Último ID: EVT{ultimo_id:03d}")

    hora_inicio = datetime.now()
    eventos_nuevos = []
    duplicados = 0
    ciudad_invalida = 0
    id_counter = ultimo_id

    for e in eventos_raw:
        ciudad = normalizar_ciudad(e.get("ciudad", ""))
        if not ciudad:
            print(f"  AVISO Ciudad invalida en '{e.get('nombre_evento', '?')}' ({e.get('ciudad', '')}), omitido")
            ciudad_invalida += 1
            continue

        e["ciudad"] = ciudad

        if es_duplicado(e, hashes_existentes):
            duplicados += 1
            continue

        id_counter += 1
        evento = {
            "id": f"EVT{id_counter:03d}",
            "fecha_extraccion": hoy,
            "fuente_tipo": "instagram",
            "fuente": "instagram",
            "perfil_ig": e.get("perfil_ig", ""),
            "nombre_evento": e.get("nombre_evento", ""),
            "fecha_evento": e.get("fecha_evento", ""),
            "hora": e.get("hora", "no especificado"),
            "lugar": e.get("lugar", ""),
            "ciudad": ciudad,
            "categoria": e.get("categoria", ""),
            "descripcion": e.get("descripcion", ""),
            "url_post": e.get("url_post", ""),
            "imagen_url": "",
            "estado": "pendiente",
            "notas": e.get("notas", f"Fuente: {e.get('fuente_id', '')}"),
        }

        hashes_existentes.add(generar_hash(evento["nombre_evento"], evento["fecha_evento"], evento["lugar"]))
        eventos_nuevos.append(evento)

    if eventos_nuevos:
        agregar_eventos(spreadsheet, eventos_nuevos)

    revisados = actualizar_ultima_revision(spreadsheet, perfiles_revisados, hoy)

    hora_fin = datetime.now()
    duracion = round((hora_fin - hora_inicio).total_seconds() / 60, 1)

    errores_str = ", ".join(p.get("perfil", "") for p in perfiles_con_error) if perfiles_con_error else "ninguno"
    notas = (
        f"Perfiles revisados: {len(perfiles_revisados)} | "
        f"Sin eventos: {len(perfiles_sin_eventos)} | "
        f"Con error: {len(perfiles_con_error)} | "
        f"ultima_revision actualizada: {revisados}"
    )

    escribir_log(spreadsheet, {
        "flujo": "instagram",
        "fecha_sesion": fecha_sesion,
        "hora_inicio": hora_inicio.strftime("%H:%M"),
        "hora_fin": hora_fin.strftime("%H:%M"),
        "duracion_min": duracion,
        "fuentes_revisadas": len(perfiles_revisados),
        "eventos_nuevos": len(eventos_nuevos),
        "eventos_omitidos": duplicados,
        "fuentes_con_error": errores_str,
        "notas": notas,
    })

    print(f"\n{'='*45}")
    print(f"  Eventos nuevos escritos:   {len(eventos_nuevos)}")
    print(f"  Duplicados omitidos:       {duplicados}")
    print(f"  Ciudad inválida omitidos:  {ciudad_invalida}")
    print(f"  Perfiles marcados:         {revisados}")
    if perfiles_con_error:
        print(f"  Perfiles con error:        {errores_str}")
    print(f"{'='*45}")


if __name__ == "__main__":
    main()
