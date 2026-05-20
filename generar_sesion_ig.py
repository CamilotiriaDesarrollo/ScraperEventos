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

PROMPT_INSTRUCCIONES = """---

## TU TAREA — LEE COMPLETO ANTES DE ABRIR INSTAGRAM

Vas a revisar los perfiles de Instagram listados arriba y extraer eventos culturales con fecha futura.

### Qué es un evento válido
Un post es evento válido si tiene los 3:
- Fecha futura específica (día concreto — no "próximamente", no "todos los viernes")
- Lugar físico (venue, sala, dirección) o link de transmisión
- Nombre o título del evento

No son eventos válidos: lifestyle · fotos de comida · frases · promociones · convocatorias · eventos privados (grados, bodas) · publicaciones de servicios sin fecha.

### Cómo revisar cada perfil
1. Abre la URL del perfil en una pestaña nueva
2. Revisa solo los posts de los **últimos 7 días**
3. Por cada post que sea evento válido: haz clic, lee imagen y caption, anota los datos
4. Si es carrusel con varios eventos, extrae cada uno por separado
5. Si el perfil no carga o está privado, anótalo en `perfiles_con_error`
6. Espera 5 segundos entre perfil y perfil

Categorías válidas: {categorias}

---

## FORMATO DE SALIDA — MUY IMPORTANTE

Cuando termines de revisar TODOS los perfiles, escribe en el chat UN SOLO bloque JSON con este formato exacto. No escribas nada antes del bloque, no expliques cada perfil mientras avanzas — espera al final.

```json
{{
  "fecha_sesion": "{hoy}",
  "perfiles_revisados": [
    "@handle1",
    "@handle2"
  ],
  "perfiles_sin_eventos": [
    {{"perfil": "@handle", "razon": "solo lifestyle / inactivo / privado / sin fecha"}}
  ],
  "perfiles_con_error": [
    {{"perfil": "@handle", "razon": "no cargó / cuenta eliminada"}}
  ],
  "eventos": [
    {{
      "perfil_ig": "@handle",
      "fuente_id": "F001",
      "nombre_evento": "Nombre del evento",
      "fecha_evento": "YYYY-MM-DD",
      "hora": "HH:MM o no especificado",
      "lugar": "Nombre del venue o dirección",
      "ciudad": "Bogotá o Pereira",
      "categoria": "una categoría válida de la lista",
      "descripcion": "1-2 líneas del caption",
      "url_post": "https://www.instagram.com/p/..."
    }}
  ]
}}
```

Si no encontraste ningún evento, igual devuelve el JSON con `"eventos": []`.
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
    parser.add_argument("--perfiles", type=int, default=20, help="Número de perfiles a revisar (default: 20)")
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
        PROMPT_INSTRUCCIONES.format(hoy=hoy, categorias=CATEGORIAS_VALIDAS)
    )

    SALIDA.write_text("\n".join(lineas), encoding="utf-8")

    print(f"OK Archivo generado: {SALIDA}")
    print(f"   Perfiles pendientes: {len(fuentes)}")
    print(f"   Proximo EVT ID: {proximo_evt}")
    print(f"\n-> Abre Claude in Chrome y pega el contenido de '{SALIDA}'")


if __name__ == "__main__":
    main()
