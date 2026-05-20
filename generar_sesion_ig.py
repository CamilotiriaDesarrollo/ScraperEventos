"""
Genera el archivo de sesión para el scraping manual de Instagram.

Uso:
    python generar_sesion_ig.py              # 20 perfiles, umbral 7 días
    python generar_sesion_ig.py --perfiles 30
    python generar_sesion_ig.py --dias 14    # re-revisar perfiles de hace 2 semanas

Salida: sesion_ig_hoy.md  (pégalo completo en Claude in Chrome)
"""
import argparse
from datetime import datetime, timedelta
from pathlib import Path

from sheets_client import get_client, get_eventos_existentes

TAB_FUENTES_IG = "FUENTES_IG"
SALIDA = Path("sesion_ig_hoy.md")

CATEGORIAS_VALIDAS = (
    "concierto · teatro · danza · exposición · taller · festival · fiesta · "
    "cine · gastronomía · feria · conversatorio · stand-up · lanzamiento · mercado"
)

SHEET_URL = "https://docs.google.com/spreadsheets/d/1c8eXsUrTask4b9HT9w9TYHTP3lxsHPtrv73mTov8Wj0/edit"

PROMPT_INSTRUCCIONES = """---

## TU TAREA

Extraer eventos culturales de los perfiles de Instagram listados arriba y registrarlos directamente en Google Sheets.

**Sheet:** {sheet_url}
**Pestaña:** EVENTOS
**Próximo ID:** {proximo_evt}
**Fecha de hoy:** {hoy}

---

## REGLAS CRÍTICAS
- NUNCA borres ni modifiques filas que ya tienen datos
- NUNCA uses Ctrl+A ni selecciones rangos grandes
- SOLO escribe en filas completamente vacías
- Usá TAB para pasar de columna, ENTER para nueva fila

---

## PASO 1 — Preparar el Sheet (una sola vez al inicio)

Abre el Sheet, ve a la pestaña EVENTOS.
Hace scroll hasta el final y fijate en qué fila está la primera celda vacía de la columna A.
Haz clic ahí. Esa es tu posición de escritura. No la muevas hasta terminar todos los perfiles.

---

## PASO 2 — Revisar cada perfil de Instagram

Para cada perfil de la lista:

1. Abrilo en una pestaña nueva
2. Mirá solo los posts de los **últimos 7 días** — no necesitás hacer scroll más abajo
3. Para decidir si un post es evento: **mirá la imagen primero** (fecha visible, flyer, etc.). Solo abrí el post si necesitás confirmar la fecha o el lugar
4. Si es carrusel con varios eventos, extraé cada uno por separado
5. Cerrá la pestaña y seguí con el siguiente

**Un post ES evento válido si tiene los 3:**
- Fecha futura específica (día concreto)
- Lugar físico o link de transmisión
- Nombre del evento

**NO son eventos:** lifestyle · comida · frases · promociones · convocatorias · eventos privados

Categorías válidas: {categorias}

---

## PASO 3 — Registrar cada evento en el Sheet inmediatamente

Cada vez que encontrés un evento válido, volvé al Sheet y escribí en la siguiente fila vacía:

| Col | Campo | Valor |
|-----|-------|-------|
| A | id | {proximo_evt} (incrementar por cada evento) |
| B | fecha_extraccion | {hoy} |
| C | fuente_tipo | instagram |
| D | fuente | instagram |
| E | perfil_ig | @handle del perfil |
| F | nombre_evento | nombre del evento |
| G | fecha_evento | YYYY-MM-DD |
| H | hora | HH:MM o "no especificado" |
| I | lugar | venue o dirección |
| J | ciudad | Bogotá o Pereira |
| K | categoria | categoría válida |
| L | descripcion | 1 línea del caption |
| M | url_post | URL del post |
| N | imagen_url | dejar vacío |
| O | estado | pendiente |
| P | notas | dejar vacío |

Usá TAB entre columnas y ENTER al terminar cada fila.

---

## PASO 4 — Actualizar ultima_revision

Cuando termines todos los perfiles del bloque, ve a la pestaña FUENTES_IG.
Para cada perfil que revisaste, buscá su fila y escribí {hoy} en la columna `ultima_revision`.
No toques ninguna otra celda de esas filas.

---

## PASO 5 — Reportar y detenerse

Cuando termines el bloque completo, escribí en el chat:

```
BLOQUE COMPLETADO
Perfiles revisados: N
Eventos registrados: N
Sin eventos: @handle (razón), @handle (razón)
Con error: @handle (razón)
```

Luego **detenete y esperá** la orden "siguiente bloque" antes de continuar.
"""


def get_fuentes_ig_pendientes(spreadsheet, max_perfiles, dias_umbral):
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
    return candidatos[:max_perfiles]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--perfiles", type=int, default=30, help="Número de perfiles a revisar (default: 30)")
    parser.add_argument("--dias", type=int, default=7, help="Días mínimos desde última revisión (default: 7)")
    args = parser.parse_args()

    print("Conectando al Sheet...")
    spreadsheet = get_client()

    fuentes = get_fuentes_ig_pendientes(spreadsheet, args.perfiles, args.dias)
    if not fuentes:
        print("No hay perfiles pendientes de revisión (todos fueron revisados recientemente).")
        return

    _, ultimo_id = get_eventos_existentes(spreadsheet)
    hoy = datetime.now().strftime("%Y-%m-%d")
    proximo_evt = f"EVT{ultimo_id + 1:03d}"

    lineas = [
        f"# Sesión IG — {hoy}",
        f"",
        f"**Fecha de hoy:** {hoy}  ",
        f"**Próximo ID de evento:** {proximo_evt}  ",
        f"**Perfiles a revisar:** {len(fuentes)}",
        f"",
        f"---",
        f"",
        f"## Perfiles a revisar",
        f"",
        f"| # | Fuente ID | Perfil | URL | Ciudad | Categoría | Última revisión |",
        f"|---|-----------|--------|-----|--------|-----------|-----------------|",
    ]

    for i, f in enumerate(fuentes, 1):
        ultima = f.get("ultima_revision", "") or "nunca"
        lineas.append(
            f"| {i} | {f.get('id','')} | {f.get('perfil','')} | {f.get('url','')} "
            f"| {f.get('ciudad','')} | {f.get('categoria','')} | {ultima} |"
        )

    lineas.append("")
    lineas.append(
        PROMPT_INSTRUCCIONES.format(
            hoy=hoy,
            categorias=CATEGORIAS_VALIDAS,
            proximo_evt=proximo_evt,
            sheet_url=SHEET_URL,
        )
    )

    SALIDA.write_text("\n".join(lineas), encoding="utf-8")

    print(f"OK Archivo generado: {SALIDA}")
    print(f"   Perfiles pendientes: {len(fuentes)}")
    print(f"   Proximo EVT ID: {proximo_evt}")
    print(f"\n-> Abre Claude in Chrome y pega el contenido de '{SALIDA}'")


if __name__ == "__main__":
    main()
