"""Genera el texto plano que el bot publica al canal de WhatsApp.

WhatsApp markdown:
    *negrita*  _cursiva_  ~tachado~  ```mono```
"""
from datetime import datetime

DIAS_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
MESES_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
            "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

EMOJI_CATEGORIA = {
    "concierto": "🎵",
    "teatro": "🎭",
    "danza": "💃",
    "exposicion": "🎨",
    "taller": "🛠️",
    "festival": "🎉",
    "fiesta": "🎉",
    "cine": "🎬",
    "gastronomia": "🍽️",
    "feria": "🛍️",
    "conversatorio": "💬",
    "stand-up": "🎤",
    "lanzamiento": "🚀",
    "mercado": "🛒",
}


def _fecha_amigable(fecha_iso):
    if not fecha_iso:
        return ""
    try:
        d = datetime.strptime(fecha_iso, "%Y-%m-%d")
    except ValueError:
        return fecha_iso
    return f"{DIAS_ES[d.weekday()]} {d.day} de {MESES_ES[d.month - 1]}"


def generar_caption_alerta(evento):
    """Copy de urgencia para el día del evento (estado alerta_hoy).

    Formato:
        🔴 HOY 🎭
        *Título*
        📅 Hoy, Viernes 5 de junio · 🕐 8:00 PM
        📍 Lugar, Ciudad
        ¡Últimas horas para conseguir tu entrada!
        No te lo pierdas 👇
        🔗 URL
    """
    titulo = (evento.get("nombre_evento") or "").strip()
    cat = (evento.get("categoria") or "").strip()
    hora = (evento.get("hora") or "").strip()
    lugar = (evento.get("lugar") or "").strip()
    ciudad = (evento.get("ciudad") or "").strip()
    url = (evento.get("url_post") or "").strip()

    emoji = EMOJI_CATEGORIA.get(cat.lower(), "📣")
    hoy = datetime.now()
    fecha_str = f"{DIAS_ES[hoy.weekday()]} {hoy.day} de {MESES_ES[hoy.month - 1]}"

    lineas = [f"🔴 HOY {emoji}", "", f"*{titulo}*", ""]

    if hora and hora.lower() != "no especificado":
        lineas.append(f"📅 Hoy, {fecha_str} · 🕐 {hora}")
    else:
        lineas.append(f"📅 Hoy, {fecha_str}")

    if lugar:
        ubic = lugar
        if ciudad and ciudad.lower() not in lugar.lower():
            ubic += f", {ciudad}"
        lineas.append(f"📍 {ubic}")
    elif ciudad:
        lineas.append(f"📍 {ciudad}")

    lineas.extend(["", "¡Últimas horas para conseguir tu entrada!", "No te lo pierdas 👇"])

    if url:
        lineas.extend(["", f"🔗 {url}"])

    while lineas and lineas[-1] == "":
        lineas.pop()

    return "\n".join(lineas)


def generar_caption(evento):
    """Devuelve el texto listo para enviar a WhatsApp.

    Estructura:
        #Categoría 🎭

        *Título del evento*

        📅 Sábado 3 de mayo · 🕐 8:00 PM
        📍 Lugar, Ciudad

        Descripción (≤250 chars)

        💡 Notas (boletería / precio)

        🔗 URL
    """
    titulo = (evento.get("nombre_evento") or "").strip()
    cat = (evento.get("categoria") or "").strip()
    fecha = _fecha_amigable(evento.get("fecha_evento", ""))
    hora = (evento.get("hora") or "").strip()
    lugar = (evento.get("lugar") or "").strip()
    ciudad = (evento.get("ciudad") or "").strip()
    desc = (evento.get("descripcion") or "").strip()
    notas = (evento.get("notas") or "").strip()
    url = (evento.get("url_post") or "").strip()

    lineas = []

    if cat:
        emoji = EMOJI_CATEGORIA.get(cat.lower(), "📣")
        lineas.append(f"#{cat.capitalize()} {emoji}")
        lineas.append("")

    lineas.append(f"*{titulo}*")
    lineas.append("")

    info = []
    if fecha and hora and hora.lower() != "no especificado":
        info.append(f"📅 {fecha} · 🕐 {hora}")
    elif fecha:
        info.append(f"📅 {fecha}")
    elif hora and hora.lower() != "no especificado":
        info.append(f"🕐 {hora}")

    if lugar:
        ubic = lugar
        if ciudad and ciudad.lower() not in lugar.lower():
            ubic += f", {ciudad}"
        info.append(f"📍 {ubic}")
    elif ciudad:
        info.append(f"📍 {ciudad}")

    if info:
        lineas.extend(info)
        lineas.append("")

    if desc:
        desc_corto = desc if len(desc) <= 250 else desc[:247] + "..."
        lineas.append(desc_corto)
        lineas.append("")

    if notas:
        lineas.append(f"💡 {notas}")
        lineas.append("")

    if url:
        lineas.append(f"🔗 {url}")

    # Limpiar líneas en blanco al final
    while lineas and lineas[-1] == "":
        lineas.pop()

    return "\n".join(lineas)
