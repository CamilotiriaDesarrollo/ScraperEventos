"""Dashboard de aprobación de eventos.

Uso:
    streamlit run dashboard.py
"""
import base64
import html
import random
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

import streamlit as st

from sheets_client import (
    actualizar_evento,
    actualizar_eventos_en_lote,
    get_client,
)
from config import TAB_EVENTOS

st.set_page_config(page_title="Aprobación de eventos", layout="wide")

_LOGOS_DIR = Path(__file__).parent / "assets" / "logos"

def _cargar_logos_b64():
    logos = []
    for f in sorted(_LOGOS_DIR.glob("*.png")):
        data = base64.b64encode(f.read_bytes()).decode()
        logos.append(f"data:image/png;base64,{data}")
    return logos

def _logo_aleatorio(seed: str) -> str:
    logos = _cargar_logos_b64()
    if not logos:
        return ""
    return random.Random(seed).choice(logos)

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


@st.cache_resource
def conectar():
    return get_client()


@st.cache_data(ttl=60, show_spinner="Cargando eventos del Sheet…")
def _cargar_todos(_spreadsheet):
    ws = _spreadsheet.worksheet(TAB_EVENTOS)
    return ws.get_all_records()


def cargar_eventos(spreadsheet, estado_filtro):
    registros = _cargar_todos(spreadsheet)
    if estado_filtro == "todos":
        return registros
    return [r for r in registros if str(r.get("estado", "")).strip().lower() == estado_filtro]


def _setear_rango_fechas(desde, hasta):
    """Callback para botones de rango rápido — actualiza ambos date_inputs."""
    st.session_state["fecha_desde"] = desde
    st.session_state["fecha_hasta"] = hasta


def _en_rango_fecha(evento, desde, hasta):
    f = str(evento.get("fecha_evento", "")).strip()
    if not f:
        return False
    try:
        fd = datetime.strptime(f, "%Y-%m-%d").date()
    except ValueError:
        return False
    return desde <= fd <= hasta


def _fecha_amigable(fecha_iso):
    if not fecha_iso:
        return ""
    try:
        d = datetime.strptime(fecha_iso, "%Y-%m-%d")
    except ValueError:
        return fecha_iso
    return f"{DIAS_ES[d.weekday()]} {d.day} de {MESES_ES[d.month - 1]}"


def _emoji_para(cat):
    return EMOJI_CATEGORIA.get((cat or "").strip().lower(), "📣")


def main():
    st.title("Eventos — panel de aprobación")
    spreadsheet = conectar()

    sidebar = st.sidebar
    sidebar.header("Filtros")

    sidebar.markdown("**📅 Rango de fechas del evento**")
    hoy = date.today()
    default_hasta = hoy + timedelta(days=14)

    # Inicializar session_state la primera vez
    if "fecha_desde" not in st.session_state:
        st.session_state["fecha_desde"] = hoy
    if "fecha_hasta" not in st.session_state:
        st.session_state["fecha_hasta"] = default_hasta

    col_d, col_h = sidebar.columns(2)
    desde = col_d.date_input("Desde", format="YYYY-MM-DD", key="fecha_desde")
    hasta = col_h.date_input("Hasta", format="YYYY-MM-DD", key="fecha_hasta")

    if desde > hasta:
        sidebar.warning("⚠️ La fecha 'Desde' es posterior a 'Hasta'.")

    rangos_rapidos = sidebar.columns(3)
    finde = hoy + timedelta(days=(6 - hoy.weekday()))
    rangos_rapidos[0].button(
        "Hoy", key="btn_hoy", width="stretch",
        on_click=_setear_rango_fechas, args=(hoy, hoy),
    )
    rangos_rapidos[1].button(
        "Esta sem.", key="btn_semana", width="stretch",
        on_click=_setear_rango_fechas, args=(hoy, finde),
    )
    rangos_rapidos[2].button(
        "2 sem.", key="btn_2sem", width="stretch",
        on_click=_setear_rango_fechas, args=(hoy, hoy + timedelta(days=14)),
    )

    sidebar.markdown("---")
    estado_opt = sidebar.radio(
        "Estado",
        ["pendiente", "aprobado", "publicado", "rechazado", "todos"],
        index=0,
    )

    sidebar.markdown("---")
    sidebar.markdown("**🎨 Vista**")
    modo = sidebar.radio(
        "Modo",
        ["Curaduría (datos)", "Preview canal"],
        index=1,
        label_visibility="collapsed",
    )

    eventos = cargar_eventos(spreadsheet, estado_opt)

    ciudades = sorted({str(e.get("ciudad", "")).strip() for e in eventos if e.get("ciudad")})
    fuentes = sorted({str(e.get("perfil_ig", "")).strip() for e in eventos if e.get("perfil_ig")})
    categorias = sorted({str(e.get("categoria", "")).strip() for e in eventos if e.get("categoria")})

    sidebar.markdown("---")
    ciudad_sel = sidebar.multiselect("Ciudad", ciudades, default=[])
    fuente_sel = sidebar.multiselect("Fuente / dominio", fuentes, default=[])
    categoria_sel = sidebar.multiselect("Categoría", categorias, default=[])
    busqueda = sidebar.text_input("Buscar en nombre o lugar", "")

    eventos = [e for e in eventos if _en_rango_fecha(e, desde, hasta)]
    if ciudad_sel:
        eventos = [e for e in eventos if str(e.get("ciudad", "")).strip() in ciudad_sel]
    if fuente_sel:
        eventos = [e for e in eventos if str(e.get("perfil_ig", "")).strip() in fuente_sel]
    if categoria_sel:
        eventos = [e for e in eventos if str(e.get("categoria", "")).strip() in categoria_sel]
    if busqueda:
        q = busqueda.lower()
        eventos = [
            e for e in eventos
            if q in str(e.get("nombre_evento", "")).lower()
            or q in str(e.get("lugar", "")).lower()
        ]

    eventos.sort(key=lambda e: (str(e.get("fecha_evento", "9999")), str(e.get("hora", ""))))

    sidebar.markdown("---")
    sidebar.metric("Eventos en vista", len(eventos))

    pendientes = [e for e in eventos if str(e.get("estado", "")).strip().lower() == "pendiente"]
    if pendientes:
        sidebar.markdown("**🚀 Acciones masivas**")
        confirmar = sidebar.checkbox(
            f"Confirmar aprobación de {len(pendientes)} eventos",
            key="confirm_aprobar_todos",
        )
        if sidebar.button(
            f"✅ Aprobar los {len(pendientes)} pendientes",
            type="primary",
            width="stretch",
            disabled=not confirmar,
        ):
            updates = {str(e.get("id")): {"estado": "aprobado"} for e in pendientes if e.get("id")}
            n = actualizar_eventos_en_lote(spreadsheet, updates)
            _cargar_todos.clear()
            st.session_state["confirm_aprobar_todos"] = False
            st.success(f"✅ {n} eventos aprobados")
            st.rerun()

    sidebar.markdown("---")
    if sidebar.button("🔄 Recargar desde el Sheet"):
        _cargar_todos.clear()
        st.rerun()

    if not eventos:
        st.info("No hay eventos para los filtros seleccionados.")
        return

    if modo == "Curaduría (datos)":
        for evento in eventos:
            _render_card_curaduria(spreadsheet, evento)
    else:
        # Grilla de 3 columnas
        for i in range(0, len(eventos), 3):
            cols = st.columns(3, gap="small")
            for j, col in enumerate(cols):
                if i + j < len(eventos):
                    with col:
                        _render_celda_preview(spreadsheet, eventos[i + j])


def _render_card_curaduria(spreadsheet, evento):
    eid = str(evento.get("id", ""))
    nombre = evento.get("nombre_evento", "(sin nombre)")
    estado = str(evento.get("estado", "")).strip().lower() or "pendiente"
    color_estado = {"pendiente": "🟡", "aprobado": "🟢", "publicado": "🔵", "rechazado": "🔴"}.get(estado, "⚪")

    with st.container(border=True):
        cols = st.columns([1, 4])
        with cols[0]:
            img = (evento.get("imagen_url") or "").strip()
            if img.startswith("http"):
                st.image(img, width="stretch")
            else:
                st.markdown("🖼️ *(sin imagen)*")
        with cols[1]:
            st.markdown(f"### {color_estado} {nombre}")
            meta_cols = st.columns(4)
            meta_cols[0].markdown(f"**📅 Fecha**\n{evento.get('fecha_evento', '—')}")
            meta_cols[1].markdown(f"**🕐 Hora**\n{evento.get('hora', '—')}")
            meta_cols[2].markdown(f"**📍 Lugar**\n{evento.get('lugar', '—')}")
            meta_cols[3].markdown(f"**🏙️ Ciudad**\n{evento.get('ciudad', '—')}")

            cat = evento.get("categoria", "")
            fuente = evento.get("perfil_ig", "") or evento.get("fuente", "")
            st.markdown(
                f"**Categoría:** `{cat or '—'}` · **Fuente:** `{fuente or '—'}` · **ID:** `{eid}`"
            )

            desc = (evento.get("descripcion") or "").strip()
            if desc:
                st.markdown(f"📝 {desc}")
            notas = (evento.get("notas") or "").strip()
            if notas:
                st.markdown(f"💬 *{notas}*")

            url = (evento.get("url_post") or "").strip()
            if url:
                st.markdown(f"🔗 [Abrir publicación original]({url})")

            _editar(spreadsheet, evento, eid, nombre, cat, notas)
            _botones_acciones(spreadsheet, eid, estado, ancho=3)


def _render_celda_preview(spreadsheet, evento):
    eid = str(evento.get("id", ""))
    estado = str(evento.get("estado", "")).strip().lower() or "pendiente"

    color_estado = {"pendiente": "🟡", "aprobado": "🟢", "publicado": "🔵", "rechazado": "🔴"}.get(estado, "⚪")
    st.caption(f"{color_estado} `{eid}` · {estado}")

    _preview_canal(evento)
    _botones_acciones(spreadsheet, eid, estado, ancho=2)


def _preview_canal(evento):
    """Estilo Telegram/WhatsApp channel: dark bg + link preview card + caption + URL + hora."""
    eid = str(evento.get("id", ""))
    img = (evento.get("imagen_url") or "").strip()
    titulo_raw = evento.get("nombre_evento", "").strip()
    titulo = html.escape(titulo_raw)
    cat_raw = (evento.get("categoria") or "").strip()
    cat_pill = html.escape(cat_raw.capitalize()) if cat_raw else ""
    emoji = _emoji_para(cat_raw)
    fecha_str = _fecha_amigable(evento.get("fecha_evento", ""))
    fecha = html.escape(fecha_str)
    hora = html.escape(evento.get("hora", "").strip())
    lugar_raw = evento.get("lugar", "").strip()
    lugar = html.escape(lugar_raw)
    ciudad_raw = evento.get("ciudad", "").strip()
    ciudad = html.escape(ciudad_raw)
    desc_raw = (evento.get("descripcion") or "").strip()
    notas_raw = (evento.get("notas") or "").strip()
    url = (evento.get("url_post") or "").strip()

    dominio = ""
    if url:
        try:
            dominio = urlparse(url).netloc.replace("www.", "")
        except Exception:
            dominio = ""

    # Imagen rectangular o placeholder con logo Divergente
    if img.startswith("http"):
        img_block = (
            f'<img src="{html.escape(img, quote=True)}" '
            f'style="width:100%;height:170px;object-fit:cover;display:block;background:#222;">'
        )
    else:
        logo_src = _logo_aleatorio(eid)
        if logo_src:
            img_block = (
                f'<div style="width:100%;height:170px;background:#111;display:flex;'
                f'align-items:center;justify-content:center;">'
                f'<img src="{logo_src}" style="height:120px;width:120px;object-fit:contain;opacity:0.85;">'
                f'</div>'
            )
        else:
            img_block = (
                '<div style="width:100%;height:170px;background:#222;display:flex;'
                'align-items:center;justify-content:center;color:#666;font-size:12px;">'
                'Sin imagen</div>'
            )

    # === CARD PREVIEW DE LINK (lo que IG/WA renderiza al detectar la URL) ===
    # Solo título + bajada corta + dominio. Estilo Open Graph.
    titulo_card = titulo_raw[:65] + ("..." if len(titulo_raw) > 65 else "")
    bajada_card = ""
    if desc_raw:
        bajada_card = desc_raw[:90] + ("..." if len(desc_raw) > 90 else "")
    elif lugar_raw:
        bajada_card = f"En {lugar_raw}" + (f", {ciudad_raw}" if ciudad_raw else "")
    else:
        bajada_card = "Más información en el sitio."

    # === BODY DEL MENSAJE (lo que el canal "escribe") ===
    # Header: hashtag + emoji
    body_lines = []
    if cat_pill:
        body_lines.append(
            f'<span style="font-weight:700;color:#FFF;">#{cat_pill}</span> {emoji}'
        )

    # Título destacado
    body_lines.append(f'<span style="font-weight:700;color:#FFF;font-size:13.5px;">{titulo}</span>')

    # Bloque de datos clave (1-2 líneas)
    info_lines = []
    if fecha and hora:
        info_lines.append(f"📅 {fecha} · 🕐 {hora}")
    elif fecha:
        info_lines.append(f"📅 {fecha}")
    elif hora:
        info_lines.append(f"🕐 {hora}")
    if lugar_raw:
        ubic = lugar
        if ciudad_raw and ciudad_raw.lower() not in lugar_raw.lower():
            ubic += f", {ciudad}"
        info_lines.append(f"📍 {ubic}")
    elif ciudad_raw:
        info_lines.append(f"📍 {ciudad}")
    if info_lines:
        body_lines.append("<br>".join(info_lines))

    # Descripción (~250 chars máx)
    if desc_raw:
        desc_limpia = desc_raw if len(desc_raw) <= 250 else desc_raw[:247] + "..."
        body_lines.append(html.escape(desc_limpia))

    # Notas (info de boletería, precios) — gris
    if notas_raw:
        body_lines.append(
            f'<span style="color:#B0B3B8;font-size:12.5px;">💡 {html.escape(notas_raw)}</span>'
        )

    body_html = '<br><br>'.join(body_lines)

    # URL clickeable verde
    url_block = ""
    if url:
        url_corto = url if len(url) <= 55 else url[:52] + "..."
        url_block = (
            f'<div style="margin-top:10px;">'
            f'<a href="{html.escape(url, quote=True)}" target="_blank" '
            f'style="color:#4FC76A;font-size:12.5px;text-decoration:underline;'
            f'word-break:break-all;">{html.escape(url_corto)}</a></div>'
        )

    hora_msg = datetime.now().strftime("%I:%M %p").lstrip("0").lower()

    html_str = f"""
    <div style="background:#0F0F0F;border-radius:14px;padding:10px 10px 8px;margin-bottom:10px;
                font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#E4E6EB;
                box-shadow:0 2px 8px rgba(0,0,0,0.3);">
      <div style="background:#1A1A1A;border-radius:10px;overflow:hidden;margin-bottom:9px;
                  border-left:3px solid #4FC76A;">
        {img_block}
        <div style="padding:9px 11px;">
          <div style="font-weight:700;font-size:13px;line-height:1.3;color:#FFF;
                      display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;
                      overflow:hidden;margin-bottom:4px;">{html.escape(titulo_card)}</div>
          <div style="color:#B0B3B8;font-size:11.5px;line-height:1.35;
                      display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;
                      overflow:hidden;margin-bottom:5px;">{html.escape(bajada_card)}</div>
          <div style="color:#90A0AB;font-size:10.5px;text-transform:lowercase;">{html.escape(dominio)}</div>
        </div>
      </div>
      <div style="font-size:13px;line-height:1.5;color:#E4E6EB;padding:0 4px;">{body_html}</div>
      {url_block}
      <div style="display:flex;justify-content:flex-end;align-items:center;
                  margin-top:8px;padding:0 4px;">
        <span style="color:#90A0AB;font-size:10px;">{html.escape(hora_msg)}</span>
      </div>
    </div>
    """
    st.markdown(html_str, unsafe_allow_html=True)


def _editar(spreadsheet, evento, eid, nombre, cat, notas):
    with st.expander("✏️ Editar campos"):
        col_e1, col_e2 = st.columns(2)
        edit_nombre = col_e1.text_input("Nombre", value=nombre, key=f"n_{eid}")
        edit_categoria = col_e2.text_input("Categoría", value=cat, key=f"c_{eid}")
        edit_lugar = col_e1.text_input("Lugar", value=evento.get("lugar", ""), key=f"l_{eid}")
        edit_ciudad = col_e2.text_input("Ciudad", value=evento.get("ciudad", ""), key=f"ci_{eid}")
        edit_hora = col_e1.text_input("Hora", value=evento.get("hora", ""), key=f"h_{eid}")
        edit_notas = col_e2.text_input("Notas", value=notas, key=f"nt_{eid}")
        if st.button("💾 Guardar cambios", key=f"save_{eid}"):
            actualizar_evento(spreadsheet, eid, {
                "nombre_evento": edit_nombre,
                "categoria": edit_categoria,
                "lugar": edit_lugar,
                "ciudad": edit_ciudad,
                "hora": edit_hora,
                "notas": edit_notas,
            })
            _cargar_todos.clear()
            st.success("Cambios guardados.")
            st.rerun()


def _botones_acciones(spreadsheet, eid, estado, ancho=2):
    """ancho=2 para grid (solo Aprobar/Rechazar), ancho=3 para curaduría (incluye Volver)."""
    if ancho == 3:
        c1, c2, c3 = st.columns(3)
        if estado != "aprobado" and c1.button("✅ Aprobar", key=f"ok_{eid}", width="stretch"):
            actualizar_evento(spreadsheet, eid, {"estado": "aprobado"})
            _cargar_todos.clear()
            st.rerun()
        if estado != "rechazado" and c2.button("❌ Rechazar", key=f"no_{eid}", width="stretch"):
            actualizar_evento(spreadsheet, eid, {"estado": "rechazado"})
            _cargar_todos.clear()
            st.rerun()
        if estado != "pendiente" and c3.button("↩️ Pendiente", key=f"pe_{eid}", width="stretch"):
            actualizar_evento(spreadsheet, eid, {"estado": "pendiente"})
            _cargar_todos.clear()
            st.rerun()
    else:
        c1, c2 = st.columns(2)
        if estado != "aprobado" and c1.button("✅", key=f"ok_{eid}", width="stretch", help="Aprobar"):
            actualizar_evento(spreadsheet, eid, {"estado": "aprobado"})
            _cargar_todos.clear()
            st.rerun()
        if estado != "rechazado" and c2.button("❌", key=f"no_{eid}", width="stretch", help="Rechazar"):
            actualizar_evento(spreadsheet, eid, {"estado": "rechazado"})
            _cargar_todos.clear()
            st.rerun()


if __name__ == "__main__":
    main()
