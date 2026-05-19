# Operaciones — Flujo semanal del bot

Guía paso a paso para repetir el proceso cada semana. Cuando algo se rompa,
mirá la sección de troubleshooting al final.

> ℹ️ **Python en este equipo**: Python 3.10 instalado en:
> ```
> C:\Users\camil\AppData\Local\Programs\Python\Python310\python.exe
> ```
> El comando `python` ya funciona directamente desde la terminal de VS Code.

---

## 🗓 Antes de empezar la semana (una vez por semana, lunes)

### Paso 0 — Scraping manual de Instagram con Claude in Chrome

> **Por qué este paso es importante:** muchos eventos culturales de Pereira/Bogotá
> NO se publican en sitios web grandes — solo aparecen en Instagram (cuentas
> chicas, colectivos, espacios). Esos son justamente los que MÁS interesan al canal.
> El scraping automático no llega ahí (Instagram bloquea bots).

**Cómo se hace:** abrís [Claude en Chrome](https://claude.ai/chrome) y le pegás
el prompt maestro que está abajo. Claude entonces:
- Lee la pestaña `FUENTES_IG` del Sheet
- Toma los primeros 5 perfiles con `activo=sí` y `ultima_revision` vacía o vieja
- Abre Instagram en una pestaña nueva, revisa los posts de los últimos 7 días
- Escribe los eventos nuevos directo en `EVENTOS` (en filas vacías al final)
- Marca `ultima_revision` en `FUENTES_IG` para los perfiles que revisó
- Te da un resumen al final

**Frecuencia recomendada**: 1-2 veces por semana, **antes** de correr `python main.py`.

**Tiempo**: ~10-15 minutos por sesión (5 perfiles).

#### 📋 Prompt maestro (copiar y pegar en Claude en Chrome)

> ⚠️ Antes de pegar, abrí el Google Sheet en otra pestaña del mismo Chrome.
> Reemplazá `[PEGA AQUÍ TU URL]` por:
> `https://docs.google.com/spreadsheets/d/1c8eXsUrTask4b9HT9w9TYHTP3lxsHPtrv73mTov8Wj0/edit`

```
TAREA: Extraer eventos culturales de Instagram y registrarlos en Google Sheets.

REGLAS CRÍTICAS — LEE ANTES DE HACER CUALQUIER COSA:
- NUNCA descargues archivos. NUNCA crees CSV, Excel ni ningún archivo.
- NUNCA escribas todos los datos en una sola celda.
- NUNCA borres, modifiques ni selecciones filas que ya tienen datos.
- NUNCA uses Ctrl+A, Ctrl+Shift, ni selecciones rangos grandes.
- NUNCA elimines filas ni columnas existentes.
- SOLO escribe en filas que estén COMPLETAMENTE VACÍAS.
- SIEMPRE escribe directamente en las celdas del Google Sheet en el navegador.
- SIEMPRE usa TAB para moverte a la siguiente columna y ENTER para la siguiente fila.
- Si una imagen da error de tamaño, lee solo el caption y sigue adelante.

PASO 1 — IDENTIFICAR QUÉ PERFILES REVISAR:
Abre este Google Sheet: [PEGA AQUÍ TU URL]
Ve a la pestaña FUENTES_IG.
Busca los primeros 5 perfiles que cumplan AMBAS condiciones:
  - La columna "activo" dice "sí"
  - La columna "ultima_revision" está VACÍA o tiene una fecha de hace más de 5 días
Esos son los 5 perfiles que vas a revisar hoy. Si todos tienen fecha reciente,
dime "No hay perfiles pendientes" y termina.

PASO 2 — CARGAR EVENTOS EXISTENTES:
Ve a la pestaña EVENTOS.
Lee los eventos que ya existen para no repetirlos.
IMPORTANTE: NO toques, NO selecciones, NO modifiques ninguna fila que ya tenga datos.
Solo fíjate cuál es el último id (EVT + número) para continuar la numeración.
Identifica cuál es la primera fila COMPLETAMENTE VACÍA. Ahí vas a empezar a escribir.

PASO 3 — REVISAR INSTAGRAM:
Abre Instagram en una pestaña nueva.
Para cada uno de los 5 perfiles:
- Abre el perfil
- Revisa solo los posts de los últimos 7 días
- Si ves un post que anuncia un EVENTO con fecha futura:
  → Haz clic en el post para abrirlo
  → Lee la imagen y el caption
  → Anota mentalmente: nombre, fecha, hora, lugar, ciudad, categoría, descripción
- Ignora posts sin fecha futura específica
- Si es un carrusel con varios eventos, extrae cada uno por separado
- Espera 10 segundos entre perfil y perfil

Categorías válidas: concierto, teatro, danza, exposición, taller, festival,
fiesta, cine, gastronomía, feria, conversatorio, stand-up, lanzamiento, mercado

PASO 4 — REGISTRAR EN GOOGLE SHEET:
Vuelve a la pestaña EVENTOS del Google Sheet.
Haz scroll hacia abajo hasta encontrar la primera fila COMPLETAMENTE VACÍA.
NO toques las filas que ya tienen datos.
Haz clic en la celda de la columna A de esa primera fila vacía.

Para cada evento, llena así:

Columna A: id (EVT + número siguiente) → TAB
Columna B: fecha de hoy YYYY-MM-DD → TAB
Columna C: instagram → TAB
Columna D: instagram → TAB
Columna E: @ del perfil → TAB
Columna F: nombre del evento → TAB
Columna G: fecha del evento YYYY-MM-DD → TAB
Columna H: hora o "no especificado" → TAB
Columna I: lugar/venue → TAB
Columna J: ciudad (Pereira o Bogota) → TAB
Columna K: categoría → TAB
Columna L: descripción breve → TAB
Columna M: URL del post → TAB
Columna N: dejar vacío → TAB
Columna O: pendiente → TAB
Columna P: notas extras → ENTER

Repite para cada evento nuevo. Siempre en la siguiente fila vacía.

PASO 5 — MARCAR PERFILES COMO REVISADOS:
Ve a la pestaña FUENTES_IG.
Para cada perfil que revisaste, busca su fila, haz clic SOLO en la celda de
"ultima_revision" y escribe la fecha de hoy. No toques ninguna otra celda de esa fila.

PASO 6 — RESUMEN:
Dime en el chat:
- Perfiles revisados: cuáles y cuántos
- Eventos nuevos registrados: cuántos
- Perfiles sin eventos: cuáles y por qué (solo lifestyle, inactivo, privado, etc.)
  → Para cada uno sugiere: "mantener", "vigilar" o "desactivar"
- Problemas de carga: si algún perfil no abrió
- Perfiles pendientes: cuántos quedan sin fecha en ultima_revision
```

#### Después de correr el prompt en Claude in Chrome

Los eventos ya quedan escritos en `EVENTOS` con `estado=pendiente` y `ciudad`
en `Bogota` (sin tilde) o `Pereira`. Cuando corras `python main.py` en el paso 1,
el bot pasa esos eventos por el filtro de ciudades (que normaliza `Bogota` →
`Bogotá`) y por la dedup global por título. Si Instagram subió eventos que también
están en algún sitio web, se colapsan a uno.

> El prompt fuente vive en la pestaña `PROMPT_IG` del Sheet. Si lo modificás
> ahí, también actualizá esta sección.

#### 📋 Guía rápida — ¿qué SÍ y qué NO es evento?

(Tomada de la pestaña `GUÍA_IG` del Sheet. Útil para entrenar el ojo si alguna
sesión te queda dudosa, o para ajustar el prompt si Claude in Chrome se confunde.)

**✅ QUÉ SÍ es evento**
- Tiene fecha futura específica (no "próximamente")
- Es en un lugar físico o virtual con link
- Tiene nombre o título claro
- Palabras clave: concierto, obra, taller, exposición, festival, feria, show, presentación, lanzamiento, apertura, conversatorio, stand-up, mercado, bazar

**❌ QUÉ NO es evento**
- Promociones de productos sin fecha de evento
- Contenido lifestyle, personal o inspiracional
- Posts de hace más de 7 días
- Eventos que ya pasaron
- Posts sin fecha identificable
- "Ven esta noche" o "happy hour" sin fecha específica
- Reels de ambiente sin info textual de evento

**⏱ Filtro de tiempo**
- Solo posts de los últimos 7 días
- Si Instagram muestra "hace 8 días" o más → para, sigue al siguiente perfil
- Si no podés determinar la fecha del post → inclúyelo con nota "fecha incierta"

**🔁 Evitar duplicados**
- Antes de cada perfil → revisá pestaña EVENTOS: combo `perfil_ig + nombre_evento + fecha_evento`
- Si los 3 campos coinciden → omitir
- Si nombre parecido pero fecha distinta → SÍ incluir (otra función del mismo evento — la dedup global por título las colapsará después)

**🏷 Categorías válidas** (usar EXACTAMENTE estas, en minúscula y sin tildes salvo "exposición")

| Categoría | Cubre |
|---|---|
| `concierto` | Música en vivo: bandas, orquestas, solistas, DJs en evento |
| `teatro` | Obras teatrales, musicales, monólogos, títeres |
| `danza` | Ballet, contemporánea, folclor, urbana |
| `exposición` | Arte visual, fotografía, instalaciones, museos |
| `taller` | Masterclass, workshop, formación, clases abiertas |
| `festival` | Eventos multi-día o multi-artista |
| `fiesta` | Eventos nocturnos temáticos, raves, fiestas de bar |
| `cine` | Proyecciones, ciclos, festivales de cine, cine-foro |
| `gastronomía` | Catas, ferias gastronómicas, cenas temáticas |
| `feria` | Ferias grandes: libro, artesanía, emprendimiento |
| `conversatorio` | Charlas, paneles, conferencias, encuentros |
| `stand-up` | Comedia en vivo, open mic, shows de humor |
| `lanzamiento` | Libros, discos, marcas, inauguraciones |
| `mercado` | Bazares, mercados campesinos, pop-ups de diseño |

> Nota: el bot web normaliza algunas a sin tilde (`exposicion`, `gastronomia`)
> al insertar. Para el flujo IG manual con Claude in Chrome, usar el formato
> con tilde está OK — el filtro de ciudades/dedup en `main.py` no lo afecta.

**👤 Tipos de fuente** (cómo revisar cada perfil de IG)

| Tipo | Quiénes son | Cómo revisar |
|---|---|---|
| **A — Publicadora** | `@bogotaplan`, `@plancpereira`, `@eventospereira` | Casi todo lo que publican es evento. Extraé la mayoría. |
| **B — Venue** | `@teatromayor`, `@cinematecabta`, salas de concierto | Su programación. Lugar = el venue mismo. |
| **C — Bar / Híbrido** | `@elephant_pisocero`, bares con eventos esporádicos | Filtro estricto: solo cuando hay fecha + hora específicas. |

> Regla por defecto: si no sabés de qué tipo es un perfil, aplicale **TIPO C**
> (el más estricto). Mejor descartar dudosos que llenar el Sheet de ruido.

---

### Paso 1 — Scrapear nuevos eventos

```bash
cd "c:/Users/camil/Desktop/Scrapper EVENTOS"
python main.py
```

Tarda **2-3 minutos**. Hace:
- Lee las 53 fuentes activas del Sheet `FUENTES_WEB`
- Extrae eventos de cada una (descarta los de otras ciudades, mantiene Bogotá/Pereira/online)
- Deduplica al insertar (por nombre+fecha+lugar)
- Al final, dedup global por título: borra duplicados que entraron desde varias fuentes
- Marca cada fuente con `ultimo_scrape=<fecha>` y registra log en pestaña `LOG`

**Qué esperar**: 30-150 eventos nuevos por corrida (depende de cuántos publiquen los sitios).

### Paso 2 — Curar en el dashboard

```bash
streamlit run dashboard.py
```

Abre `http://localhost:8501`. **Por defecto te muestra eventos pendientes de hoy a +14 días en formato preview canal**.

Acciones:
1. **Filtra por rango de fechas**: usa los botones rápidos `Hoy / Esta sem. / 2 sem.` o pon fechas manualmente
2. **Filtra por ciudad**: Bogotá, Pereira, online (uno o varios)
3. Para cada evento:
   - **✅ Aprobar** si está bien y querés publicarlo
   - **❌ Rechazar** si es ruido o irrelevante
   - **✏️ Editar campos** si querés ajustar nombre, lugar, hora, notas, categoría
4. **Aprobación masiva**: si todo el rango filtrado se ve OK, marcás el checkbox "Confirmar aprobación de N eventos" → botón rojo "Aprobar los N pendientes"

**Cuándo dejarlo**: cuando los pendientes en el rango "2 sem." estén todos en aprobado o rechazado.

### Paso 3 — (Una vez) crear los canales reales de producción

Si todavía solo tenés "Test Eventos", **crear desde tu teléfono**:
1. WhatsApp → tab "Actualizaciones" → "+" arriba a la derecha → "Nuevo canal"
2. Nombre exacto sugerido: **"Eventos Bogotá"**
3. Repetir para **"Eventos Pereira"**

Luego pasame los **nombres exactos** y los configuro en `.env`:

```
WA_CANAL_BOGOTA=Eventos Bogotá
WA_CANAL_PEREIRA=Eventos Pereira
```

> El nombre debe coincidir LITERAL con el que aparece en la pestaña Canales de
> WhatsApp Web. Cuidado con espacios al final.

---

## 🚀 Durante la semana (publicación automática)

### Modo manual: arrancar el bot publicador

Una sola vez por día (idealmente lunes en la mañana):

```bash
python bot_publicador.py --canal Bogotá --ciudad Bogotá
```

Lo que hace:
- Lee eventos `aprobados` de Bogotá del Sheet
- Los ordena por fecha de evento ascendente (los más cercanos primero)
- Publica el primero al canal "Eventos Bogotá"
- Marca ese evento como `publicado`
- Espera **25-40 minutos aleatorios**
- Publica el siguiente
- Se autodetiene fuera de la **ventana 8 AM – 10 PM**

Para Pereira (en otra terminal, en paralelo):

```bash
python bot_publicador.py --canal Pereira --ciudad Pereira
```

### Modo automático: tarea programada

**Una sola vez** registrá la tarea para que arranque sola cada mañana:

```bash
powershell -ExecutionPolicy Bypass -File install_scheduled_task.ps1
```

Eso registra una tarea que corre `main.py` (scrapeo) diariamente a las **08:00 AM**.

Para que el **publicador** también corra automáticamente, podés crear tareas similares
modificando el `.bat` y registrando con un nombre distinto (ej. `ScraperEventos_PublicadorBogota`).

> Recomendación inicial: dejá la publicación en manual durante 1-2 semanas hasta
> que confirmés que el formato y la cadencia se sienten bien. Después automatizás.

---

## 🛠 Comandos de prueba y troubleshooting

### Ver el caption que publicaría el bot sin enviarlo

```bash
python bot_publicador.py --canal TEST --ciudad Bogotá --una-sola --dry-run --ignorar-ventana
```

### Publicar 1 solo evento al canal TEST (validar formato)

```bash
python bot_publicador.py --canal TEST --ciudad Bogotá --una-sola --ignorar-ventana
```

### Publicar N eventos seguidos con intervalo corto (testing)

```bash
python bot_publicador.py --canal TEST --ciudad Bogotá --n 3 --intervalo 8 --ignorar-ventana
```

### Mostrar el navegador en vez de headless (debug visual)

Agregá `--no-headless` a cualquier comando del bot.

### Re-correr dedup global manualmente (si por alguna razón hay duplicados)

```bash
python -c "from sheets_client import get_client; from deduplicator import deduplicar_por_titulo_en_sheet; from config import TAB_EVENTOS; print(deduplicar_por_titulo_en_sheet(get_client(), TAB_EVENTOS))"
```

### Re-escanear QR de WhatsApp Web (cuando expire la sesión, ~14 días)

```bash
python whatsapp_publisher.py --setup
```

### Borrar la sesión actual de WhatsApp Web

```bash
rm -rf wa_session/user-data/
```

Luego re-ejecutar `--setup`.

---

## 🐛 Problemas comunes

### "WhatsApp Web no cargó (sigue en pantalla de inicio)"

La sesión expiró o se invalidó. Solución:

```bash
rm -rf wa_session/user-data/
python whatsapp_publisher.py --setup
```

### "No encontré el canal 'X' en la pestaña Canales"

El nombre en `.env` no coincide con el nombre real en WhatsApp. Verificá:
1. Abrir WhatsApp Web → click en "Canales" del sidebar
2. Mirar el nombre exacto del canal (incluyendo mayúsculas, espacios, emojis)
3. Copiar ese nombre LITERAL en `.env` como `WA_CANAL_TEST=NombreExacto`

### El dashboard no actualiza tras aprobar/rechazar

Cache de Streamlit. Solución:
- Click en el botón "🔄 Recargar desde el Sheet" en el sidebar
- O esperar 60s (TTL de la caché)

### Una corrida del scraper falla con un sitio específico

Mirar `logs/scraper.log` para ver el sitio que falló. La caída de un solo
scraper no detiene los demás, así que la corrida sigue.

Si un sitio cambia su HTML, hay que actualizar los selectores del scraper
correspondiente en `scrapers/sitios/<nombre>.py`.

### El preview de WhatsApp no carga imagen para algunos enlaces

Esperado. Depende de los metatags Open Graph del sitio (no del bot).
- Instagram: casi siempre genera preview con imagen ✅
- Eventbrite: a veces sin imagen ⚠️
- Sitios .gov.co: depende, varios no tienen og:image ❌

Si querés garantía de imagen, hay que migrar a "subir imagen como adjunto"
en lugar de URL preview. Eso es un cambio de ~2-3 horas de trabajo.

---

## 📊 Métricas que tu Sheet debería mostrar después de unas semanas

- **EVENTOS** crece ~50-150 filas por corrida diaria
- **LOG** crece 1 fila por corrida con stats (eventos nuevos, duplicados, dedup global)
- **FUENTES_WEB** se actualiza con `ultimo_scrape` y `ultimo_estado` por fuente

Si una fuente lleva muchos días con `ultimo_estado=error`, abrí el sitio en el
navegador para ver si cambió la estructura.

---

## 🔮 Mejoras futuras (no urgentes)

- **Subir imagen como adjunto** en lugar de URL preview, para asegurar imagen en TODOS los posts
- **Mejorar TaquillaLive** con scroll infinito (carga más eventos)
- **Agregar scrapers** para sitios pendientes: Banrepcultural, Teatro Nacional, Casa E Borrero
- **Notificar errores por email/Slack** si el bot falla varios días seguidos
- **Métricas de canal**: cuántos seguidores ganamos por publicación
