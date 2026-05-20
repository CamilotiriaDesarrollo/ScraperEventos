"""
Genera el archivo de sesión para el scraping manual de Instagram.

Uso:
    python generar_sesion_ig.py           # todos los perfiles pendientes (umbral 7 días)
    python generar_sesion_ig.py --dias 1  # forzar todos aunque sean recientes

Salida: sesion_ig_hoy.md
→ Pegalo UNA SOLA VEZ en Claude in Chrome al inicio de la semana.
→ Luego solo decí "siguiente bloque" para continuar.
"""
import argparse
from datetime import datetime, timedelta
from pathlib import Path

from sheets_client import get_client, get_eventos_existentes

TAB_FUENTES_IG = "FUENTES_IG"
SALIDA = Path("sesion_ig_hoy.md")
SHEET_URL = "https://docs.google.com/spreadsheets/d/1c8eXsUrTask4b9HT9w9TYHTP3lxsHPtrv73mTov8Wj0/edit"
BLOQUE_SIZE = 15

CATEGORIAS_VALIDAS = (
    "concierto · teatro · danza · exposición · taller · festival · fiesta · "
    "cine · gastronomía · feria · conversatorio · stand-up · lanzamiento · mercado"
)

PROMPT = """---

## CONTEXTO Y REGLAS — LEÉ ANTES DE EMPEZAR

**Sheet:** {sheet_url}
**Fecha de hoy:** {hoy}
**Perfiles totales en esta sesión:** {total}
**Tamaño de cada bloque:** {bloque_size} perfiles

Vas a revisar los {total} perfiles de la lista de arriba en bloques de {bloque_size}.
Procesás el primer bloque ahora. Cuando el usuario diga "siguiente bloque", continuás con los siguientes {bloque_size}, y así hasta terminar la lista completa.

### Reglas críticas para el Sheet
- NUNCA borres ni modifiques filas con datos
- NUNCA uses Ctrl+A ni selecciones rangos grandes
- SOLO escribí en filas completamente vacías

---

## AL INICIO DE CADA BLOQUE — siempre hacer esto primero

Antes de revisar Instagram, abrí el Sheet y ejecutá este script de Apps Script para saber dónde escribir:

```javascript
function getSheetState() {{
  var ss = SpreadsheetApp.openById('{sheet_id}');
  var eventos = ss.getSheetByName('EVENTOS');
  var lastRow = eventos.getLastRow();
  var nextRow = lastRow + 1;
  var lastId = '';
  if (lastRow > 1) {{
    lastId = eventos.getRange(lastRow, 1).getValue();
  }}
  Logger.log('Proxima fila vacia: ' + nextRow);
  Logger.log('Ultimo ID registrado: ' + lastId);
}}
```

Ese script te dice:
- En qué fila del Sheet escribir los eventos de este bloque
- Cuál es el último ID (EVT...) para continuar la numeración

---

## REVISAR INSTAGRAM — para cada perfil del bloque actual

1. Abrí la URL del perfil en una pestaña nueva
2. Mirá solo los posts de los **últimos 7 días**
3. Para evaluar un post: **mirá la imagen primero**. Solo abrí el post si necesitás confirmar fecha o lugar
4. Si es carrusel con varios eventos, extraé cada uno por separado
5. Cerrá la pestaña y seguí con el siguiente

**Post ES evento válido si tiene los 3:**
- Fecha futura específica (día concreto, no "próximamente")
- Lugar físico o link de transmisión
- Nombre del evento

**NO son eventos:** lifestyle · comida · frases · promociones · convocatorias · eventos privados

Categorías válidas: {categorias}

---

## REGISTRAR EN EL SHEET — usar Apps Script para escribir todos los eventos del bloque de una vez

Cuando termines de revisar los {bloque_size} perfiles del bloque, escribí todos los eventos juntos con este script. Reemplazá el array `eventos` con los datos reales:

```javascript
function addEventosToSheet() {{
  var ss = SpreadsheetApp.openById('{sheet_id}');
  var sheet = ss.getSheetByName('EVENTOS');
  var hoy = '{hoy}';

  var eventos = [
    // ["EVT026", hoy, "instagram", "instagram", "@perfil", "Nombre evento", "2026-05-25", "20:00", "Venue", "Bogotá", "concierto", "Descripción", "https://instagram.com/p/...", "", "pendiente", ""],
    // Agregá una línea por cada evento encontrado
  ];

  if (eventos.length === 0) {{
    Logger.log('No hay eventos para registrar en este bloque.');
    return;
  }}

  var lastRow = sheet.getLastRow();
  sheet.getRange(lastRow + 1, 1, eventos.length, 16).setValues(eventos);
  Logger.log('Agregados ' + eventos.length + ' eventos desde la fila ' + (lastRow + 1));
}}
```

---

## ACTUALIZAR ULTIMA_REVISION — también con Apps Script

Después de escribir los eventos, actualizá los perfiles revisados en FUENTES_IG:

```javascript
function updateUltimaRevision() {{
  var ss = SpreadsheetApp.openById('{sheet_id}');
  var sheet = ss.getSheetByName('FUENTES_IG');
  var hoy = '{hoy}';

  // Reemplazá con los @handles del bloque que revisaste
  var perfilesRevisados = [
    // "@handle1", "@handle2", ...
  ];

  var data = sheet.getDataRange().getValues();
  var headers = data[0];
  var colPerfil = headers.indexOf('perfil');
  var colRevision = headers.indexOf('ultima_revision');

  var updates = [];
  for (var i = 1; i < data.length; i++) {{
    if (perfilesRevisados.indexOf(data[i][colPerfil]) !== -1) {{
      sheet.getRange(i + 1, colRevision + 1).setValue(hoy);
    }}
  }}
  Logger.log('ultima_revision actualizada para ' + perfilesRevisados.length + ' perfiles.');
}}
```

---

## AL TERMINAR CADA BLOQUE — reportar y esperar

Escribí en el chat:

```
BLOQUE N/M COMPLETADO
Perfiles revisados: X (perfiles #N a #M de la lista)
Eventos registrados: X
Sin eventos: @handle (razón breve)
Con error: @handle (razón)
```

Luego **detenete y esperá** que el usuario diga "siguiente bloque".

Cuando llegue "siguiente bloque":
1. Ejecutá `getSheetState()` para ver la posición actual del Sheet
2. Continuá con los siguientes {bloque_size} perfiles de la lista
3. Repetí el proceso

---

## PRIMER BLOQUE — arrancá ahora con los perfiles #1 al #{bloque_size}
"""


def get_fuentes_ig_pendientes(spreadsheet, dias_umbral):
    ws = spreadsheet.worksheet(TAB_FUENTES_IG)
    registros = ws.get_all_records()

    activos = ("sí", "si", "true", "1")
    hoy = datetime.now().date()
    umbral = hoy - timedelta(days=dias_umbral)

    candidatos = []
    for r in registros:
        if str(r.get("activo", "")).strip().lower() not in activos:
            continue
        if not r.get("perfil", "").strip():
            continue

        ultima = str(r.get("ultima_revision", "")).strip()
        if not ultima:
            prioridad = 0
            fecha_rev = None
        else:
            try:
                fecha_rev = datetime.strptime(ultima, "%Y-%m-%d").date()
                if fecha_rev >= umbral:
                    continue
                prioridad = 1
            except ValueError:
                prioridad = 0
                fecha_rev = None

        candidatos.append({**r, "_prioridad": prioridad, "_fecha_rev": fecha_rev})

    candidatos.sort(key=lambda x: (x["_prioridad"], x["_fecha_rev"] or datetime.min.date()))
    return candidatos


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dias", type=int, default=7, help="Dias minimos desde ultima revision (default: 7)")
    args = parser.parse_args()

    print("Conectando al Sheet...")
    spreadsheet = get_client()

    fuentes = get_fuentes_ig_pendientes(spreadsheet, args.dias)
    if not fuentes:
        print("No hay perfiles pendientes (todos revisados recientemente).")
        return

    _, ultimo_id = get_eventos_existentes(spreadsheet)
    hoy = datetime.now().strftime("%Y-%m-%d")
    sheet_id = "1c8eXsUrTask4b9HT9w9TYHTP3lxsHPtrv73mTov8Wj0"

    lineas = [
        f"# Sesion IG — {hoy}",
        f"",
        f"**Fecha de hoy:** {hoy}",
        f"**Perfiles pendientes:** {len(fuentes)}",
        f"**Bloques de:** {BLOQUE_SIZE} perfiles",
        f"**Ultimo EVT registrado:** EVT{ultimo_id:03d}",
        f"",
        f"---",
        f"",
        f"## Lista completa de perfiles",
        f"",
        f"| # | ID | Perfil | URL | Ciudad | Categoria | Ultima revision |",
        f"|---|----|--------|-----|--------|-----------|-----------------|",
    ]

    for i, f in enumerate(fuentes, 1):
        ultima = f.get("ultima_revision", "") or "nunca"
        lineas.append(
            f"| {i} | {f.get('id','')} | {f.get('perfil','')} | {f.get('url','')} "
            f"| {f.get('ciudad','')} | {f.get('categoria','')} | {ultima} |"
        )

    lineas.append("")
    lineas.append(PROMPT.format(
        sheet_url=SHEET_URL,
        sheet_id=sheet_id,
        hoy=hoy,
        total=len(fuentes),
        bloque_size=BLOQUE_SIZE,
        categorias=CATEGORIAS_VALIDAS,
    ))

    SALIDA.write_text("\n".join(lineas), encoding="utf-8")

    bloques = (len(fuentes) + BLOQUE_SIZE - 1) // BLOQUE_SIZE
    print(f"OK Archivo generado: {SALIDA}")
    print(f"   Perfiles pendientes: {len(fuentes)}")
    print(f"   Bloques necesarios:  {bloques} (de {BLOQUE_SIZE} perfiles cada uno)")
    print(f"   Proximo EVT ID:      EVT{ultimo_id + 1:03d}")
    print(f"\n-> Pega '{SALIDA}' en Claude in Chrome UNA SOLA VEZ.")
    print(f"   Luego solo di 'siguiente bloque' para continuar.")


if __name__ == "__main__":
    main()
