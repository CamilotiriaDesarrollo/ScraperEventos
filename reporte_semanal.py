"""
Reporte semanal del estado del Sheet y proyección de eventos por semana.

Uso:
  python reporte_semanal.py                  # 6 semanas desde hoy
  python reporte_semanal.py --semanas 8
  python reporte_semanal.py --solo-resumen   # solo estado general, sin listado
"""
import argparse
import sys
from collections import defaultdict
from datetime import datetime, timedelta

from config import TAB_EVENTOS, TAB_FUENTES_WEB
from sheets_client import get_client

# Forzar UTF-8 en consola Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ESTADOS_ACTIVOS = {"pendiente", "aprobado", "activo", "confirmado"}
CAPACIDAD_SEMANAL = 21  # 3 posts/día × 7 días


def _lunes_de(fecha):
    return fecha - timedelta(days=fecha.weekday())


def _fmt_semana(lunes):
    domingo = lunes + timedelta(days=6)
    meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
             "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    ini = f"{lunes.day:02d} {meses[lunes.month - 1]}"
    fin = f"{domingo.day:02d} {meses[domingo.month - 1]}"
    return f"{ini} – {fin}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--semanas", type=int, default=6)
    parser.add_argument("--solo-resumen", action="store_true")
    args = parser.parse_args()

    print("Conectando a Google Sheets...")
    spreadsheet = get_client()

    # ── Sección 1: Estado general ──────────────────────────────────────────
    ws = spreadsheet.worksheet(TAB_EVENTOS)
    records = ws.get_all_records()

    por_estado = defaultdict(int)
    por_ciudad = defaultdict(int)
    por_fuente = defaultdict(int)

    hoy = datetime.now().date()
    manana = hoy + timedelta(days=1)
    eventos_futuros = []

    for r in records:
        estado = str(r.get("estado", "")).strip().lower() or "sin_estado"
        ciudad = str(r.get("ciudad", "")).strip() or "sin_ciudad"
        fuente = str(r.get("fuente_tipo", "")).strip() or "?"
        por_estado[estado] += 1
        por_ciudad[ciudad] += 1
        por_fuente[fuente] += 1

        if estado in ESTADOS_ACTIVOS:
            raw_fecha = str(r.get("fecha_evento", "")).strip()
            try:
                fecha = datetime.strptime(raw_fecha, "%Y-%m-%d").date()
                if fecha >= manana:
                    eventos_futuros.append({**r, "_fecha": fecha})
            except ValueError:
                pass

    print()
    print("=" * 56)
    print("  ESTADO GENERAL DEL SHEET")
    print("=" * 56)
    print(f"  Total eventos:     {len(records)}")
    print()
    print("  Por estado:")
    for estado in ["pendiente", "aprobado", "publicado", "alerta_hoy", "rechazado"]:
        n = por_estado.get(estado, 0)
        if n:
            print(f"    {estado:<15} {n:>4}")
    otros = {k: v for k, v in por_estado.items()
             if k not in {"pendiente", "aprobado", "publicado", "alerta_hoy", "rechazado"}}
    for k, v in sorted(otros.items()):
        print(f"    {k:<15} {v:>4}")
    print()
    print("  Por ciudad:")
    for ciudad, n in sorted(por_ciudad.items(), key=lambda x: -x[1]):
        print(f"    {ciudad:<15} {n:>4}")
    print()
    print("  Por fuente tipo:")
    for ft, n in sorted(por_fuente.items(), key=lambda x: -x[1]):
        print(f"    {ft:<15} {n:>4}")

    # Fuentes WEB
    ws_f = spreadsheet.worksheet(TAB_FUENTES_WEB)
    fuentes = ws_f.get_all_records()
    activas = [f for f in fuentes
               if str(f.get("activo", "")).strip().lower() in ("sí", "si", "true", "1")]
    print()
    print(f"  FUENTES_WEB: {len(fuentes)} totales | {len(activas)} activas")

    if args.solo_resumen:
        return

    # ── Sección 2: Proyección semanal ──────────────────────────────────────
    print()
    print("=" * 56)
    print("  PROYECCIÓN SEMANAL  (pendientes + aprobados)")
    print(f"  Capacidad canal: ~{CAPACIDAD_SEMANAL} eventos/semana (3/día × 7)")
    print("=" * 56)

    por_semana = defaultdict(list)
    for e in eventos_futuros:
        lunes = _lunes_de(e["_fecha"])
        por_semana[lunes].append(e)

    lunes_hoy = _lunes_de(manana)
    semanas = sorted(k for k in por_semana if k >= lunes_hoy)[:args.semanas]

    if not semanas:
        print("  (No hay eventos futuros pendientes/aprobados)")
        return

    for lunes in semanas:
        evs = sorted(por_semana[lunes], key=lambda x: x["_fecha"])
        bogota = sum(1 for e in evs if "bogot" in str(e.get("ciudad", "")).lower())
        pereira = sum(1 for e in evs if "pereira" in str(e.get("ciudad", "")).lower())
        online = sum(1 for e in evs if str(e.get("ciudad", "")).lower() == "online")

        flag = ""
        if len(evs) > CAPACIDAD_SEMANAL:
            flag = "  [!] excede capacidad"
        elif len(evs) < 7:
            flag = "  [~] pocos eventos"

        print()
        print(f"  Semana {_fmt_semana(lunes)}   =>  {len(evs)} eventos"
              f"  (Bog: {bogota} | Per: {pereira} | Online: {online}){flag}")
        print(f"  {'-' * 52}")

        for e in evs:
            fecha = str(e.get("fecha_evento", ""))
            nombre = str(e.get("nombre_evento", ""))[:48]
            ciudad = str(e.get("ciudad", ""))
            cat = str(e.get("categoria", ""))[:12]
            ciudad_abr = ciudad[:3].upper() if ciudad else "???"
            print(f"    {fecha}  {ciudad_abr}  {cat:<13} {nombre}")

    # Semanas con eventos pero fuera del rango mostrado
    semanas_extra = [k for k in por_semana if k >= lunes_hoy and k not in semanas]
    if semanas_extra:
        total_extra = sum(len(por_semana[k]) for k in semanas_extra)
        print()
        print(f"  + {len(semanas_extra)} semanas adicionales con {total_extra} eventos"
              f" (usar --semanas {args.semanas + len(semanas_extra)} para ver)")

    print()
    total_futuros = len(eventos_futuros)
    semanas_necesarias = (total_futuros + CAPACIDAD_SEMANAL - 1) // CAPACIDAD_SEMANAL
    print(f"  Total eventos futuros disponibles: {total_futuros}")
    print(f"  A 3 posts/día alcanza para ~{semanas_necesarias} semanas de contenido")
    print()


if __name__ == "__main__":
    main()
