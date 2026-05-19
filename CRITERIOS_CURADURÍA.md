# Criterios de Curaduría — Eventos Canal WhatsApp

## Contexto

Este documento es la guía para depurar la pestaña `EVENTOS` del Google Sheet.
El canal publica eventos culturales de **Bogotá** y **Pereira** para una audiencia
interesada en cultura, arte, música y planes de ciudad. No es una agenda masiva:
queremos calidad y relevancia sobre cantidad.

Sheet: https://docs.google.com/spreadsheets/d/1c8eXsUrTask4b9HT9w9TYHTP3lxsHPtrv73mTov8Wj0/edit

---

## Columnas del Sheet (referencia)

| Columna | Campo | Descripción |
|---------|-------|-------------|
| A | id | EVT + número |
| B | fecha_extraccion | Cuándo lo capturó el bot |
| C | fuente_tipo | `web` o `instagram` |
| D | fuente | dominio o plataforma |
| E | perfil_ig | @ si viene de Instagram |
| F | nombre_evento | Nombre del evento |
| G | fecha_evento | YYYY-MM-DD |
| H | hora | HH:MM o "no especificado" |
| I | lugar | Venue o dirección |
| J | ciudad | Bogotá / Pereira / online |
| K | categoría | Ver categorías válidas |
| L | descripción | Resumen breve |
| M | url_post | Link al evento o post |
| N | imagen_url | URL de imagen (puede estar vacío) |
| O | estado | `pendiente` → cambiar a `aprobado` o `rechazado` |
| P | notas | Razón del rechazo o aclaración |

---

## Categorías válidas

`concierto` · `teatro` · `danza` · `exposición` · `taller` · `festival`
`fiesta` · `cine` · `gastronomía` · `feria` · `conversatorio` · `stand-up`
`lanzamiento` · `mercado`

---

## ✅ CRITERIOS PARA APROBAR

Un evento se aprueba si cumple **los 5 criterios obligatorios**:

### 1. Fecha futura específica
- Tiene una fecha concreta (día, mes, año)
- La fecha es **posterior a hoy** (2026-05-17)
- NO: "próximamente", "mayo 2026" sin día, "todos los viernes"
- SÍ: "2026-05-24", "sábado 30 de mayo"

### 2. Lugar identificable
- Tiene un venue, sala, dirección o link de stream
- NO: "lugar por confirmar", "sede a definir", solo una ciudad genérica
- SÍ: "Teatro Mayor", "Matik Matik", "Teatro Santiago Londoño", "Zoom — link en bio"

### 3. Nombre claro del evento
- El nombre permite saber de qué se trata
- NO: "Evento especial", "Sorpresa", "No te lo pierdas"
- SÍ: "Concierto de Jazz con Trio Bogotá", "Obra: La Casa de Bernarda Alba"

### 4. Ciudad válida
- Bogotá, Pereira o online/virtual
- Eventos de otras ciudades → rechazar (salvo que sean online)
- Medellín, Cali, Barranquilla → rechazar

### 5. Categoría cultural válida
- Debe corresponder a una de las 14 categorías del canal
- Eventos corporativos, ferias de emprendimiento sin componente cultural → rechazar
- Lanzamientos de productos sin valor artístico → rechazar

---

## ❌ CRITERIOS PARA RECHAZAR

Rechazar automáticamente si cumple **cualquiera** de estas condiciones:

### Fecha
- [ ] Fecha ya pasó (anterior a 2026-05-17)
- [ ] Sin fecha específica ("próximamente", "próximas fechas")
- [ ] Evento recurrente sin fecha concreta ("todos los jueves")

### Contenido
- [ ] Es publicidad de producto sin evento asociado
- [ ] Es convocatoria o casting (no es un evento para el público)
- [ ] Es contenido institucional sin fecha de evento (inauguraciones de oficinas, rendiciones de cuentas)
- [ ] Es concurso o premio sin función pública
- [ ] Es solo una promoción ("2x1 esta semana", "happy hour")

### Relevancia
- [ ] Ciudad fuera del alcance (no es Bogotá, Pereira ni online)
- [ ] Evento masivo de entretenimiento sin componente cultural (peleas de boxeo, eventos deportivos masivos)
- [ ] Evento privado (bodas, grados, eventos corporativos cerrados)
- [ ] Evento ya publicado en el canal (duplicado por nombre + fecha + lugar)

### Calidad de datos
- [ ] Nombre del evento es genérico o ambiguo y no se puede deducir de la descripción
- [ ] Sin lugar Y sin link, no hay forma de asistir
- [ ] La URL del post no existe o da 404

---

## ⚠️ CASOS GRISES — cómo resolverlos

### "Todos los viernes" / eventos recurrentes
→ **Rechazar**. El canal publica eventos con fecha puntual.
Si el venue tiene función específica esa semana con artista anunciado → **Aprobar** con la fecha concreta.

### Evento sin hora
→ **Aprobar** si todo lo demás está bien. Dejar hora como "no especificado".

### Evento gratuito sin URL
→ **Aprobar** si el lugar es claro. Agregar en notas "gratuito, sin link".

### Exposición que dura varias semanas
→ **Aprobar** con la fecha de **inauguración** como fecha_evento.
Si ya está en curso, aprobar con la fecha de **cierre** como referencia.

### Precio muy alto (>$500.000)
→ **Aprobar igual**. El canal informa, no filtra por precio.

### Evento con nombre en inglés
→ **Aprobar** si el resto de datos están completos.

### Descripción vacía o muy corta
→ **Aprobar** si nombre + lugar + fecha son suficientemente claros.

### Fuente poco confiable o cuenta pequeña de IG
→ **Aprobar** si los datos del evento son verificables. El tamaño de la cuenta no importa.

---

## Escala de prioridad editorial

Dentro de los eventos aprobados, los más valiosos para el canal son:

1. **Alta prioridad** — Eventos únicos, irrepetibles, de artistas reconocidos o con alta demanda. Teatro, conciertos de sala, festivales con cartel.
2. **Media prioridad** — Talleres con cupo, exposiciones de artistas locales, fiestas temáticas con DJ confirmado.
3. **Baja prioridad** — Eventos recurrentes con artista sin especificar, happy hours con música de fondo, eventos con información mínima.

> Esta escala no se registra en el Sheet, es solo orientación para decidir cuándo publicar primero.

---

## Tarea para Claude in Chrome

**Objetivo**: revisar los eventos con `estado = pendiente` en la pestaña `EVENTOS` y cambiar el estado a `aprobado` o `rechazado`.

**Pasos**:

1. Abrir el Sheet → pestaña `EVENTOS`
2. Filtrar por columna O = `pendiente`
3. Para cada evento pendiente:
   - Leer columnas F (nombre), G (fecha), H (hora), I (lugar), J (ciudad), K (categoría), L (descripción)
   - Aplicar los criterios de esta guía
   - Si **aprueba**: escribir `aprobado` en columna O
   - Si **rechaza**: escribir `rechazado` en columna O + razón breve en columna P
4. Trabajar de a **10 eventos por ronda** para no perder el hilo
5. Al final de cada ronda, reportar: cuántos aprobados, cuántos rechazados, cuántos casos grises y cómo los resolviste

**Razones de rechazo sugeridas para columna P** (copiar textual):
- `fecha pasada`
- `sin fecha específica`
- `ciudad fuera de alcance`
- `publicidad sin evento`
- `duplicado`
- `evento privado`
- `sin lugar ni link`
- `convocatoria/casting`
- `datos insuficientes`

---

## Ejemplo de evento APROBADO

| Campo | Valor |
|-------|-------|
| nombre_evento | Cuarteto de Jazz — Tributo a Coltrane |
| fecha_evento | 2026-05-23 |
| hora | 19:30 |
| lugar | Matik Matik — Cra 5 #26B-26, Bogotá |
| ciudad | Bogotá |
| categoría | concierto |
| descripción | Noche de jazz con el Cuarteto Bogotano interpretando clásicos de Coltrane. Entrada $30.000. |
| estado | **aprobado** |

## Ejemplo de evento RECHAZADO

| Campo | Valor |
|-------|-------|
| nombre_evento | Lanzamiento nueva colección primavera |
| fecha_evento | 2026-05-20 |
| hora | no especificado |
| lugar | Centro Comercial Unicentro |
| ciudad | Bogotá |
| categoría | lanzamiento |
| descripción | Ven a conocer nuestra nueva línea de ropa y disfruta de música en vivo. |
| estado | **rechazado** |
| notas | publicidad sin evento — lanzamiento comercial sin componente artístico |
