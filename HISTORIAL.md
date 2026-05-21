# Historial del proyecto — Scraper de Eventos Culturales

Registro cronológico de todo lo construido. Sirve como contexto para retomar,
automatizar o delegar partes del sistema en el futuro.

---

## Resumen ejecutivo

| Métrica | Valor al cierre de esta fase |
|---|---|
| Scrapers web activos | 28 (10 estáticos + 18 con Playwright) |
| Fuentes en FUENTES_WEB | 35 activas |
| Fuentes IG en FUENTES_IG | 136 cuentas |
| Eventos en Sheet | 1.009 (EVT001–EVT1009) |
| Eventos futuros disponibles | 860 (aprox. 41 semanas de contenido a 3 posts/día) |
| Ciudades cubiertas | Bogotá (696), Pereira (312), online (1) |
| Horas estimadas de desarrollo | ~40–45 horas |

---

## Línea de tiempo

### Fase 0 — Arquitectura base (1 mayo 2026)
**Commit:** `77ed6f7` — Initial commit

Punto de partida: proyecto Python vacío con:
- `config.py`, `sheets_client.py`, `deduplicator.py`
- `BaseScraper` (requests + BS4) y `BasePlaywrightScraper` (Chromium headless)
- `main.py` con orquestador básico
- Primeros scrapers: IDARTES, PlanCPereira, BogotaAgenda, TeatroMayor, TeatroLibre,
  TuBoleta, Eventbrite, Fever, LaTicketera, eTicketablanca, TaquillaLive,
  BibloRed, Planetario, VisitBogota, Fuga

**Google Sheet configurado con pestañas:**
- `EVENTOS` — 16 columnas: id, fecha_extraccion, fuente_tipo, fuente, perfil_ig,
  nombre_evento, fecha_evento, hora, lugar, ciudad, categoria, descripcion,
  url_post, imagen_url, estado, notas
- `FUENTES_WEB` — id, nombre, dominio, url, ciudad, activo, requiere_js, ultimo_scrape
- `FUENTES_IG` — perfil, activo, ultima_revision, tipo, notas
- `LOG` — flujo, fecha, hora_inicio, hora_fin, duracion, fuentes, nuevos, omitidos

---

### Fase 1 — Dashboard y bot publicador (entre 1 mayo y 19 mayo)

**Archivos creados:**
- `dashboard.py` — Streamlit con vista previa estilo canal WhatsApp, aprobación masiva,
  edición inline de campos, filtros por fecha/ciudad/categoría/estado
- `bot_publicador.py` — publica eventos `aprobados` al canal WhatsApp con
  intervalos aleatorios 25–40 min dentro de ventana 8 AM–10 PM
- `whatsapp_publisher.py` — Playwright sobre WhatsApp Web con sesión persistente,
  espera el preview de enlace antes de avanzar
- `caption.py` — genera el texto formateado para WhatsApp por evento
- `install_scheduled_task.ps1` + `run_scraper.bat` — tarea programada Windows

**Flujo de estados definido:**
```
pendiente → aprobado → publicado → alerta_hoy
```

---

### Fase 2 — Sistema de scraping IG manual (19–20 mayo 2026)
**Commits:** `67f7302`, `e271165`, `2f30615`, `75efe06`, `0cb7ecb`

El scraping automático no puede entrar a Instagram (bloquea bots). Solución:
sesión manual asistida por Claude in Chrome, con un prompt maestro reutilizable.

**Lo que se construyó:**
- `PROMPT_IG.md` — prompt permanente para sesiones en Claude in Chrome.
  Lee `FUENTES_IG` del Sheet, abre Instagram perfil por perfil, escribe eventos
  directo en `EVENTOS`. Diseñado para bloques de 10 perfiles por sesión.
- `generar_sesion_ig.py` — genera el bloque del día con los perfiles pendientes
- `importar_eventos_ig.py` — Apps Script auxiliar para inserción rápida
- 136 cuentas de Instagram catalogadas en `FUENTES_IG` (Bogotá + Pereira)

**Resultado:** ~162 eventos de Instagram en el Sheet (categoría fuente_tipo=instagram)

---

### Fase 3 — Documentación del flujo de publicación (20 mayo 2026)
**Commits:** `a21d3a8`, `0cb7ecb`

- `FLUJO_PUBLICACION.md` — arquitectura completa del ciclo semanal:
  scraping → curación → aprobación → publicación → alerta_hoy
- `OPERACIONES.md` — guía operativa semana a semana con comandos exactos,
  troubleshooting, y el prompt maestro de IG embebido
- `CONTEXTO_AUTOMATIZACION_IG.md` — contexto técnico del límite de IG y
  por qué se eligió el enfoque manual asistido

---

### Fase 4 — Scrapers adicionales: última tanda (21 mayo 2026)
**Commits:** `f1d8727`, `0fc4377`, `b5a6ccb`, `247772d`, `d3fe75e`, `9f59df3`, `e5c5a55`

9 scrapers nuevos en ~90 minutos de trabajo:

| Scraper | Tipo | Ciudad | Notas |
|---|---|---|---|
| `cinemateca.py` | BS4 | Bogotá | Cinemateca de Bogotá, ciclos y proyecciones |
| `teatronacional.py` | Playwright | Bogotá | 61 eventos/corrida |
| `eneldelia.py` | BS4 | Bogotá | Centro Nacional de las Artes Delia Zapata |
| `maloka.py` | BS4 | Bogotá | Maloka — ciencia y tecnología |
| `culturarecreacion.py` | BS4 | Bogotá | Secretaría de Cultura y Recreación |
| `comfamiliar.py` | BS4 | Pereira | Comfamiliar Risaralda |
| `distritoch.py` | Playwright | Bogotá | Distrito CH — agenda de Chapinero |
| `masartemasciudad.py` | Playwright | Bogotá | Tribe Events Calendar, 3 meses |
| `camarapereira.py` | BS4 | Pereira | Cámara de Comercio de Pereira |
| `expofuturo.py` | BS4 | Pereira | Expo Futuro — eventos empresariales |
| `eventario.py` | Playwright | Bogotá + Pereira | 296 Bogotá + ~40 Pereira; paginación por click |
| `coliseomedplus.py` | Playwright | Bogotá | Coliseo MedPlus — conciertos grandes |
| `museodeartepereira.py` | BS4 | Pereira | Museo de Arte de Pereira (Tribe Events) |

**SCRAPER_MAP en main.py**: 28 entradas, cubre todos los scrapers activos.

**Filtro de ciudades en main.py** (`_filtrar_y_normalizar_ciudades`):
solo pasan eventos con ciudad = Bogotá / Pereira / online.
Todo lo demás se descarta en origen.

---

### Fase 5 — Pipeline de curaduría y limpieza (21 mayo 2026)
**Commit:** `1025e52`

**Problema:** después del scraping masivo el Sheet tenía:
- Fuentes no viables que nunca tendrán scraper (Wix, CAPTCHA, 404, desactualizadas)
- Eventos etiquetados como Bogotá/Pereira pero que ocurrían en Medellín u otra ciudad
- Eventos online en inglés/italiano sin relevancia local
- Eventos online sin ninguna referencia a Colombia/Bogotá/Pereira

**Solución: dos scripts nuevos**

#### `limpiar_fuentes.py`
- Elimina 20 dominios no viables de `FUENTES_WEB`
- Renumera F-IDs (F001…F035)
- CLI: `python limpiar_fuentes.py [--dry-run]`

Dominios eliminados (muestra):
`banrepcultural.org/bogota`, `museonacional.gov.co/eventos`, `teatrocolon.gov.co`,
`jbb.gov.co`, `corferias.com`, `parque93.com`, `casaeborrero.com`, y 13 más.

#### `curar_eventos.py`
Tres filtros en cascada, diseñados para correr al final de cada sesión de scraping:

**Filtro A — Ciudad errónea (con verificación en URL):**
1. Detecta eventos sospechosos: `lugar`/`nombre`/`descripcion` menciona otra ciudad
2. Para cada sospechoso, visita el `url_post` real y verifica si la ciudad declarada
   aparece en la página. Si la ciudad real es otra (Medellín, Cali, etc.) → eliminar.
   Si no se puede verificar → conservar (postura conservadora).

**Filtro B — Idioma no español:**
Solo para eventos `ciudad=online`. Detecta títulos con ≥2 tokens en inglés
o ≥1 token en italiano de conjuntos curados. Eliminar.

**Filtro C — Online sin contexto local:**
Eventos `ciudad=online` que no mencionan Colombia/Bogotá/Pereira en ningún campo.
Eliminar.

**`renumerar_ids_eventos()`**: reescribe EVT001…EVTxxx en orden consecutivo
después de cualquier eliminación (batch_update en chunks de 500).

**Resultado de la primera corrida:**
- 46 eventos ciudad errónea eliminados
- 4 eventos en otro idioma eliminados
- 10 eventos online sin contexto eliminados
- **60 filas totales eliminadas**
- IDs renumerados: EVT001–EVT1009

**Integración automática en `main.py`:**
Al final de cada sesión de scraping, después del dedup global, se llama a:
```
curar_eventos(spreadsheet) → renumerar_ids_eventos(spreadsheet)
```
El log ya incluye los stats de curaduría en cada sesión.

---

### Fase 6 — Reporte semanal (21 mayo 2026, sesión actual)

#### `reporte_semanal.py`
Script de diagnóstico/planificación que muestra:
- Estado general del Sheet (totales por estado, ciudad, fuente tipo)
- Resumen de FUENTES_WEB (activas)
- Eventos pendientes/aprobados agrupados por semana (lunes a domingo)
  con conteo por ciudad y listado detallado
- Cálculo de alcance: cuántas semanas cubre el contenido disponible

CLI: `python reporte_semanal.py [--semanas N] [--solo-resumen]`

**Resultado de la primera corrida:**
- 860 eventos futuros disponibles
- Semana 18–24 May: 318 eventos
- Semana 25–31 May: 186 eventos
- Semana 1–7 Jun: 79 eventos
- Alcance total: ~41 semanas de contenido a 3 posts/día

---

## Estado al cierre de esta fase

### ✅ Construido y funcionando

| Componente | Archivo | Estado |
|---|---|---|
| Scraping web automático | `main.py` + 28 scrapers | ✅ |
| Deduplicación al insertar | `deduplicator.py` | ✅ |
| Dedup global por título | `deduplicator.deduplicar_por_titulo_en_sheet` | ✅ |
| Curaduría automática | `curar_eventos.py` | ✅ |
| Limpieza de fuentes | `limpiar_fuentes.py` | ✅ |
| Reporte semanal | `reporte_semanal.py` | ✅ |
| Dashboard de aprobación | `dashboard.py` | ✅ |
| Bot publicador WhatsApp | `bot_publicador.py` | ✅ (validado en TEST) |
| Scraping IG manual asistido | `PROMPT_IG.md` + Claude in Chrome | ✅ |
| Tarea programada Windows | `install_scheduled_task.ps1` | ✅ |

### ⏳ Pendiente para próximas semanas

| Tarea | Descripción |
|---|---|
| Crear canales WhatsApp reales | Crear canal "Eventos Bogotá" y "Eventos Pereira" desde el teléfono |
| Configurar `.env` canales | `WA_CANAL_BOGOTA`, `WA_CANAL_PEREIRA` con nombres exactos |
| Aprobación masiva inicial | Pasar por dashboard y aprobar ~21 eventos/semana del backlog |
| Lógica horarios pico | `bot_publicador.py` actualmente publica en cualquier hora de la ventana |
| Estado `alerta_hoy` | Republicación del día del evento con copy de urgencia |
| Priorización de cola | Más próximos primero, alternar Bogotá/Pereira |
| Sesiones IG regulares | ~2 sesiones/semana con el PROMPT_IG.md para mantener el flujo |

---

## Estimación de horas invertidas

| Bloque de trabajo | Horas estimadas |
|---|---|
| Arquitectura base: Sheet, `config.py`, `sheets_client.py`, `deduplicator.py` | 4 h |
| Scrapers iniciales (15): IDARTES, PlanC, BogotaAgenda, boletería | 8 h |
| `BaseScraper` + `BasePlaywrightScraper` + debugging JS | 4 h |
| Dashboard `dashboard.py` (Streamlit, preview WA, edición inline) | 5 h |
| Bot publicador (`bot_publicador.py` + `whatsapp_publisher.py`) | 5 h |
| Sistema IG: prompt maestro, `PROMPT_IG.md`, 136 cuentas catalogadas | 5 h |
| Documentación: `FLUJO_PUBLICACION.md`, `OPERACIONES.md`, README | 3 h |
| Scrapers nuevos (13 en sesión del 21 mayo) | 3 h |
| Pipeline de curaduría (`curar_eventos.py`, `limpiar_fuentes.py`) | 3 h |
| Debugging, sesiones de test, corridas reales, fixes | 6 h |
| **Total** | **~46 horas** |

---

## Comandos de operación rápida

```bash
# Scraping web completo (incluye curaduría y renumeración al final)
python main.py

# Sólo Bogotá o Pereira
python main.py --ciudad Bogotá
python main.py --ciudad Pereira

# Ver estado del Sheet y proyección semanal
python reporte_semanal.py
python reporte_semanal.py --solo-resumen

# Curaduría manual (sin esperar el ciclo de scraping)
python curar_eventos.py
python curar_eventos.py --dry-run

# Limpiar fuentes no viables (ya corrió una vez; correr si se agregan nuevas)
python limpiar_fuentes.py

# Dashboard de aprobación
python -m streamlit run dashboard.py

# Bot publicador (una vez configurados los canales reales)
python bot_publicador.py --canal "Eventos Bogotá" --ciudad Bogotá
python bot_publicador.py --canal "Eventos Pereira" --ciudad Pereira

# Test sin publicar
python bot_publicador.py --canal TEST --ciudad Bogotá --una-sola --dry-run --ignorar-ventana
```

---

## Notas técnicas para futuros desarrollos

- **Scrapers que requieren Playwright**: eTicketablanca, TuBoleta, Eventbrite, Fever,
  LaTicketera, TaquillaLive, Fuga, MasArteMasCiudad, TeatroNacional, DistritoCH,
  Eventario, ColiseoMedPlus (total 12 de 28)
- **Eventario**: paginación por click en `.ts-load-more`, hasta 20 clicks, no por URL
- **Chía**: hay 1 evento con ciudad=Chía que los filtros no eliminan (no es Bogotá/Pereira/online).
  Los filtros de curaduría solo inspeccionan ciudades declaradas Bogotá/Pereira.
- **Estados no estándar**: el Sheet tiene 74 eventos con estado `activo` o `confirmado`
  (importados desde flujos anteriores). El bot publicador espera `aprobado`.
  Migrar con: `actualizar_eventos_en_lote` si se quieren publicar.
- **Dedup hash**: `generar_hash(nombre_evento, fecha_evento, lugar)` — tres campos
  normalizados a lowercase. Un mismo evento con ligeras variantes de nombre no se dedup
  en inserción pero sí lo captura el dedup global por título (Levenshtein).
- **Python en este equipo**: 3.10 en `C:\Users\camil\AppData\Local\Programs\Python\Python310\`
