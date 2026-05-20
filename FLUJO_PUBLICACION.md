# Flujo de Publicación — Plan :D Bogotá / Pereira

Documento de arquitectura del proceso completo: desde el scraping hasta la publicación en canal de WhatsApp.

---

## RESUMEN DEL FLUJO SEMANAL

```
LUNES (o día de inicio de semana)
│
├── 1. SCRAPING
│   ├── python main.py --ciudad Bogotá
│   ├── python main.py --ciudad Pereira
│   └── Sesión IG con PROMPT_IG.md en Claude in Chrome (bloques de 15)
│
├── 2. VERIFICACIÓN DE CALIDAD
│   └── Revisar pestaña EVENTOS: eliminar inventados, corregir fechas/lugares
│       (ver sección abajo — puede hacerse desde el Dashboard o Claude in Chrome)
│
├── 3. APROBACIÓN MANUAL
│   └── Abrir Dashboard → aprobar eventos de la semana
│       (se puede aprobar uno a uno o masivamente por ciudad/categoría)
│
└── 4. PUBLICACIÓN AUTOMÁTICA (bot_publicador.py)
    └── Corre en segundo plano toda la semana
        Toma aprobados → publica en horarios pico → marca como publicado
```

---

## PASO 2 — VERIFICACIÓN DE CALIDAD

### Qué revisar
- Eventos con fecha pasada (ya ocurrieron)
- Eventos sin lugar o con lugar genérico ("online", "por confirmar")
- Eventos duplicados que pasaron el deduplicador (mismo evento, nombre ligeramente diferente)
- Eventos de ciudad incorrecta (Medellín, Cali, etc.)
- Eventos inventados o con información inconsistente (especialmente los de IG)

### Cómo hacerlo
**Opción A — Dashboard (recomendado):**
Filtrar por estado `pendiente` + rango de fechas de la semana.
Revisar card por card. Usar botón Rechazar para los malos, editar los que tienen error menor.

**Opción B — Claude in Chrome:**
Abrir el Sheet pestaña EVENTOS, pedirle a Claude que revise los eventos pendientes
de la semana y marque en rojo (o cambie estado a `rechazado`) los que no cumplan criterios.

---

## PASO 4 — CADENCIA DE PUBLICACIÓN

### Recomendación para canales culturales de WhatsApp

**3 publicaciones por día, en horarios pico:**

| Slot | Hora | Razón |
|------|------|-------|
| Mañana | 9:00 AM | Gente revisando el teléfono antes/durante el trabajo |
| Mediodía | 1:00 PM | Pausa de almuerzo, alto tráfico |
| Noche | 7:00 PM | Después del trabajo, planean el fin de semana |

**Espaciado mínimo entre publicaciones:** 3 horas
**Máximo por día:** 4 (añadir slot 11am en semana de muchos eventos)
**Días de mayor impacto:** Miércoles a Domingo

### Por qué NO saturar
- Los canales de WhatsApp no tienen algoritmo: todo llega como notificación
- Más de 4 posts/día genera silenciamiento del canal por parte de los suscriptores
- La consistencia diaria genera más fidelidad que los volúmenes altos

---

## PASO 4 — PRIORIZACIÓN DE EVENTOS

### Regla de anticipación mínima
- **Publicar con al menos 2 días de anticipación** al evento
- Ejemplo: evento el viernes → publicar máximo el miércoles

### Orden de prioridad para la cola
1. Eventos más próximos primero (urgencia percibida)
2. Si hay empate de fecha: eventos de mayor categoría (festival > taller)
3. Alternar ciudades: no publicar 3 Bogotá seguidos sin un Pereira

---

## PASO 4 — LÓGICA DE REPUBLICACIÓN "HOY"

### Concepto
Cada evento aprobado puede publicarse **dos veces**:

| Publicación | Cuándo | Tipo de copy |
|-------------|--------|--------------|
| **Normal** | 2+ días antes del evento | Card estándar con toda la info |
| **Alerta Hoy** | El mismo día del evento, slot de 9:00 AM | Copy de urgencia + recordatorio |

### Estados del evento (columna O en Sheet)
```
pendiente   → aprobado por curador pero no publicado aún
aprobado    → listo para publicar (primera publicación)
publicado   → ya tuvo su publicación normal
alerta_hoy  → republicado el día del evento con copy de urgencia
rechazado   → descartado, no se publica
```

### Copy de Alerta Hoy
El bot detecta que `fecha_evento == hoy` y el evento está en estado `publicado`
(ya tuvo su publicación normal), entonces lo republica con este formato:

```
🔴 HOY · [nombre del evento]

📅 Hoy, [día] de [mes]
🕐 [hora]
📍 [lugar], [ciudad]

¡Últimas horas para conseguir tu entrada!
No te lo pierdas 👇

[url del post original]
```

### Cuándo corre la Alerta Hoy
- Slot fijo: **9:00 AM del día del evento**
- Va antes de los eventos normales del día
- Solo si el evento ya fue publicado normalmente antes (estado = `publicado`)
- Solo si el evento tiene hora confirmada o es un evento de todo el día

---

## RESUMEN DE ESTADOS Y TRANSICIONES

```
pendiente
    ↓ (aprobación manual en Dashboard)
aprobado
    ↓ (bot_publicador.py — publicación normal)
publicado
    ↓ (bot_publicador.py — día del evento a las 9am)
alerta_hoy
    ↓ (automático)
[archivado — no se vuelve a publicar]
```

---

## QUÉ ESTÁ CONSTRUIDO vs QUÉ FALTA

### Construido ✅
- Scraper web (15 fuentes, main.py)
- Scraper IG manual (PROMPT_IG.md + sesiones Claude in Chrome)
- Deduplicador
- Dashboard de aprobación (dashboard.py)
- Bot publicador base (bot_publicador.py) — publica aprobados con intervalos
- Google Sheets como base de datos central

### Falta construir ⏳
- **Lógica de horarios pico** en bot_publicador.py (actualmente publica en cualquier hora dentro de ventana)
- **Estado `alerta_hoy`** en bot_publicador.py (detección y republicación del día del evento)
- **Copy diferenciado** para publicación normal vs alerta hoy (caption.py)
- **Priorización de cola** en bot_publicador.py (más próximos primero, alternar ciudades)
- **Setup de sesión WhatsApp** (python whatsapp_publisher.py --setup) — pendiente de crear canales

---

## COMANDOS DE OPERACIÓN SEMANAL

```bash
# 1. Scraping web
python main.py --ciudad Pereira
python main.py --ciudad Bogotá

# 2. Scraping IG
# → Copiar PROMPT_IG.md en Claude in Chrome, decir "siguiente bloque" por cada bloque

# 3. Dashboard de aprobación
python -m streamlit run dashboard.py
# → Abrir http://localhost:8501

# 4. Bot publicador (por ciudad)
python bot_publicador.py --canal "Plan :D Pereira" --ciudad Pereira
python bot_publicador.py --canal "Plan :D - Bogotá" --ciudad Bogotá

# 5. Bot publicador modo test (1 evento, sin publicar realmente)
python bot_publicador.py --canal "Plan :D - Test" --ciudad Bogotá --una-sola --dry-run
```
