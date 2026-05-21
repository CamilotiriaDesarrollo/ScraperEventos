# Contexto completo — Automatización del Scraping de Instagram

> Este documento es para que Claude (en cualquier sesión futura) entienda qué estamos construyendo, qué ya existe, qué problemas hemos tenido y qué falta. Leerlo antes de proponer o implementar cualquier cosa.

---

## Qué es este proyecto

Un sistema para recopilar eventos culturales de **Bogotá y Pereira (Colombia)** desde ~180 fuentes (Instagram + webs), curarlos manualmente en un dashboard, y publicarlos automáticamente en canales de WhatsApp.

**Google Sheet central:** `1c8eXsUrTask4b9HT9w9TYHTP3lxsHPtrv73mTov8Wj0`
Pestañas: `EVENTOS`, `FUENTES_IG`, `FUENTES_WEB`, `LOG`

---

## Estado actual del sistema (al 2026-05-20)

### Lo que YA funciona

| Componente | Archivo | Estado |
|---|---|---|
| Scraper web | `main.py` + `scrapers/sitios/` | ✅ Corre solo, 20 scrapers activos |
| Dashboard de curación | `dashboard.py` (Streamlit) | ✅ Funciona en `localhost:8501` |
| Bot publicador WhatsApp | `bot_publicador.py` | ✅ Validado en canal TEST |
| Fuentes IG registradas | Sheet pestaña `FUENTES_IG` | ✅ 136 cuentas activas (F001–F138) |
| Eventos en el Sheet | Sheet pestaña `EVENTOS` | ✅ ~100+ eventos, último EVT051 (al 2026-05-19) |

### Lo que se hace manualmente (y queremos automatizar)

**El flujo de Instagram:** cada semana hay que abrir Claude in Chrome, pegarle el `PROMPT_IG.md`, y revisar los perfiles de Instagram uno a uno. Claude los lee, extrae eventos y los escribe en el Sheet vía Google Apps Script.

Este flujo funciona pero tiene fricciones:
- Requiere abrir el navegador y pegar el prompt manualmente
- Claude se "cuelga" o pierde contexto con bloques grandes (>10 perfiles por sesión)
- No es activable desde el celular
- Depende de que alguien esté en la computadora

---

## El problema que estamos resolviendo ahora

**Queremos que el scraping de IG se dispare solo (o con un tap desde el celular) sin necesidad de estar en la computadora.**

La sesión del 2026-05-19 tenía 79 perfiles pendientes en bloques de 15. Claude se colgaba frecuentemente. Por eso ya bajamos los bloques a **10 perfiles**. Pero la raíz del problema es que el proceso sigue siendo manual.

---

## Arquitectura objetivo (lo que queremos construir)

```
Celular (tú)
  └── activa (un tap o cron)
        │
        ▼
Script Python orquestador (local o en Railway)
  ├── lee Google Sheets → identifica perfiles sin ultima_revision (o con fecha > 7 días)
  ├── divide en bloques de 10
  ├── POST al endpoint de la Routine de Claude (bloque 1 con sus 10 perfiles)
  ├── espera que termine (polling o webhook)
  ├── POST al endpoint de la Routine de Claude (bloque 2)
  ├── ... hasta completar todos los pendientes
  └── Google Sheets se va llenando automáticamente
```

### Cómo se activa desde el celular — dos opciones en evaluación

**Opción A — HTML minimalista en Vercel:**
- Un archivo HTML estático con un botón "▶ Iniciar scraping hoy"
- Llama via fetch a una API mínima (FastAPI en Railway o similar)
- La API dispara el orquestador Python

**Opción B — Botón en el Google Sheet (Apps Script):**
- Un botón en el mismo Sheet que ejecuta un Apps Script
- El Apps Script hace HTTP POST al orquestador
- Sin depender de hosting externo

Todavía no hemos decidido cuál. Ambas son viables.

---

## Cómo funciona el flujo IG manual actual (lo que hay que replicar)

El `PROMPT_IG.md` en la raíz del proyecto es el prompt maestro. Define 5 pasos:

1. **PASO 1** — Apps Script `getProximosPerfiles()`: lee `FUENTES_IG`, detecta los 10 perfiles con `activo=sí` y `ultima_revision` vacía o > 7 días. Imprime la lista en el log.
2. **PASO 2** — Claude abre cada perfil en Instagram, mira posts de los últimos 7 días, identifica eventos válidos (fecha futura + lugar + nombre).
3. **PASO 3** — Apps Script `addEventosToSheet()`: escribe todos los eventos del bloque en `EVENTOS` de una vez.
4. **PASO 4** — Apps Script `updateRevision()`: marca `ultima_revision = hoy` en `FUENTES_IG` para los perfiles revisados.
5. **PASO 5** — Claude reporta y espera. Al "siguiente bloque", vuelve al PASO 1.

**Criterios de evento válido:**
- Fecha futura específica (día concreto)
- Lugar físico o link
- Nombre del evento
- NO son eventos: lifestyle, comida, frases, promociones, convocatorias, eventos privados

**Categorías válidas:** concierto · teatro · danza · exposición · taller · festival · fiesta · cine · gastronomía · feria · conversatorio · stand-up · lanzamiento · mercado

---

## Estructura del Sheet — columnas de EVENTOS

```
A: id (EVT001, EVT002, ...)
B: fecha_extraccion (YYYY-MM-DD)
C: fuente_tipo ("instagram")
D: fuente ("instagram")
E: perfil_ig (@handle)
F: nombre_evento
G: fecha_evento (YYYY-MM-DD)
H: hora ("20:00" o "no especificado")
I: lugar
J: ciudad ("Bogotá" o "Pereira" o "online")
K: categoria
L: descripcion
M: url_post
N: imagen_url (generalmente vacío desde IG)
O: estado ("pendiente" al insertar)
P: notas
```

## Estructura del Sheet — columnas de FUENTES_IG

```
A: id (F001, F002, ...)
B: tipo ("instagram")
C: perfil (@handle)
D: url (https://instagram.com/handle)
E: nombre_real
F: ciudad
G: categoria
H: seguidores_aprox
I: activo ("sí" / "no")
J: ultima_revision (YYYY-MM-DD o vacío)
K: notas
```

---

## Problemas encontrados y soluciones aplicadas

### 1. Claude se cuelga con bloques grandes

**Problema:** Con bloques de 15 perfiles, Claude perdía contexto o se "colgaba" alrededor del paso 270 (perfil 9-10 del bloque). La sesión se volvía inutilizable.

**Solución aplicada:** Reducir el bloque a **10 perfiles** (`PROMPT_IG.md` ya actualizado). El script `getProximosPerfiles()` ahora tiene `if (pendientes.length === 10) break;`.

**Raíz del problema real:** el proceso sigue siendo síncrono y lineal dentro de una misma sesión de Claude. Con la automatización, cada bloque de 10 perfiles sería una llamada independiente a la Routine, lo que elimina el problema de contexto.

### 2. Claude modificaba filas existentes del Sheet

**Problema:** En versiones anteriores del prompt, Claude a veces sobreescribía eventos ya registrados al escribir en el Sheet celda a celda (usando el prompt de "Claude in Chrome" que escribía directo en el navegador).

**Solución aplicada:** Migrar a Apps Script para todas las escrituras. El script usa `sheet.getLastRow() + 1` para siempre escribir desde el final, nunca tocando datos existentes. Las reglas críticas del prompt prohíben explícitamente Ctrl+A y selecciones de rangos grandes.

### 3. Duplicados entre fuentes IG y fuentes web

**Problema:** Un mismo evento podía llegar tanto desde Instagram como desde el scraper web de un venue.

**Solución existente:** `deduplicator.py` corre al final de `main.py` y colapsa eventos con mismo título. Los eventos de IG entran con `estado=pendiente`; la dedup global los detecta y elimina el duplicado más viejo.

### 4. Sesiones de Instagram que expiran / perfiles privados

**Problema:** Algunos perfiles de la lista están inactivos, fueron privados, o cambiaron de handle.

**Solución:** El `DEPURACIÓN_FUENTES_IG.md` es un protocolo para hacer auditoría periódica de las 136 cuentas. Las que fallan se marcan en rojo en el Sheet y se excluyen. Nuevas cuentas aprobadas van desde `F200` en adelante.

### 5. El bloque "desde el celular" no existe aún

**Problema actual:** No hay forma de disparar el proceso desde el celular. Todo requiere estar en la computadora con el navegador abierto.

**Lo que estamos diseñando:** Un orquestador Python que llama a la Claude API (Routines) con el contexto del bloque, sin necesidad de interfaz de usuario.

---

## Archivos clave del proyecto

| Archivo | Para qué sirve |
|---|---|
| `PROMPT_IG.md` | Prompt maestro del flujo IG (los 5 pasos + scripts Apps Script) |
| `OPERACIONES.md` | Guía semanal completa: web scraping + IG + publicación |
| `CONTEXTO_FUENTES.md` | Lista de las 136 cuentas IG y 53 webs ya registradas (para no duplicar al buscar nuevas) |
| `DEPURACIÓN_FUENTES_IG.md` | Protocolo para auditar y limpiar la lista de fuentes IG |
| `sesion_ig_hoy.md` | Archivo temporal que se genera para cada sesión manual de IG (no permanente) |
| `main.py` | Orquestador del scraping web (corre los 20 scrapers) |
| `dashboard.py` | Panel Streamlit para aprobar/rechazar eventos |
| `bot_publicador.py` | Cola de publicación al canal de WhatsApp |
| `sheets_client.py` | Wrapper de gspread para leer/escribir el Sheet |
| `deduplicator.py` | Dedup al insertar (hash) + dedup global por título |

---

## Stack técnico

- **Python 3.10** en `C:\Users\camil\AppData\Local\Programs\Python\Python310\`
- `requests` + `beautifulsoup4` + `lxml` — scrapers estáticos
- `playwright` (Chromium headless) — scrapers JS + WhatsApp Web
- `gspread` + Google Service Account — leer/escribir el Sheet
- `streamlit` — dashboard de curación
- Google Sheet ID: `1c8eXsUrTask4b9HT9w9TYHTP3lxsHPtrv73mTov8Wj0`
- Credenciales en `credentials/service-account.json` (gitignored)
- Config en `.env` con `SHEET_ID`, `WA_CANAL_TEST`, etc.

---

## Próximos pasos (lo que falta construir)

### Prioridad 1 — Orquestador Python para bloques IG automáticos

Un script `ig_orchestrator.py` que:
1. Lee `FUENTES_IG` del Sheet (via `sheets_client.py`)
2. Filtra perfiles activos con `ultima_revision` vacía o > 7 días
3. Los divide en bloques de 10
4. Por cada bloque: llama a la Claude API (Routine) pasando el contexto del bloque
5. Cuando la Routine termina, lee el resultado, escribe en `EVENTOS` y actualiza `ultima_revision`
6. Pasa al siguiente bloque

### Prioridad 2 — Endpoint de activación

Para poder disparar el orquestador desde el celular:
- **Opción A:** FastAPI minimalista en Railway con un endpoint `POST /iniciar-sesion-ig`
- **Opción B:** Apps Script en el Sheet con un botón "▶ Scraping IG hoy"

### Prioridad 3 — Canales de producción en WhatsApp

Crear los canales reales "Eventos Bogotá" y "Eventos Pereira" en WhatsApp (hoy solo existe el canal TEST). Configurar los nombres exactos en `.env`.

---

## Restricciones importantes a recordar

- Instagram bloquea bots. El scraping de IG **solo funciona con Claude in Chrome** (que tiene sesión real del usuario) o via Claude API con acceso a navegador real (Computer Use / Routine con browser).
- El Sheet se escribe siempre via Apps Script o `gspread`, nunca celda a celda desde el navegador en la automatización.
- Los bloques son de **10 perfiles** — más que eso y Claude pierde contexto.
- El umbral de revisión es **7 días** — un perfil revisado hace menos de 7 días se salta.
- Los IDs de eventos son correlativos: `EVT001`, `EVT002`, ... El último registrado hay que leerlo del Sheet antes de insertar.
- Los IDs de fuentes nuevas van desde `F200` en adelante (F001–F138 ya están en uso).
