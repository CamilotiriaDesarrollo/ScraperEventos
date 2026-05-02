# Scraper de Eventos — Pereira & Bogotá

Bot que extrae eventos culturales de ~50 fuentes web, permite curarlos manualmente
y los publica automáticamente a canales de WhatsApp con cadencia humana.

## Estado actual

- **20 scrapers** funcionando (10 estáticos + 6 con Playwright para sitios JS)
- **~395 eventos curables** en el Sheet (Bogotá, Pereira y online)
- **Dashboard de curación** con vista previa estilo canal de WhatsApp
- **Bot publicador** validado contra canal de prueba

Falta: crear canales de producción y migrar la publicación del canal TEST a esos.

## Las 5 fases del proyecto

| Fase | Estado | Qué hace |
|---|---|---|
| 0. Definición | ✅ | Plan, columnas del Sheet, ciudades objetivo |
| 1. Base de fuentes | ✅ | 107 fuentes en `FUENTES_WEB` |
| 2. Flujo IG (Claude Chrome) | ✅ | 78 eventos cargados manualmente desde IG |
| 3. Bot WEB de scraping | ✅ | `main.py` corre 20 scrapers, dedup global, filtro Bogotá/Pereira |
| 4. Dashboard de aprobación | ✅ | `dashboard.py` con preview estilo canal y filtros por fecha/ciudad/categoría |
| 5. Bot publicador WhatsApp | ✅ (validado en TEST) | `bot_publicador.py` con orden por fecha y cadencia 25-40 min |

## Stack

- **Python 3.13** (instalado en `C:\Users\ZenBook\AppData\Local\Programs\Python\Python313\`)
- `requests` + `beautifulsoup4` + `lxml` para HTML estático
- `playwright` (Chromium headless) para sitios JS y para WhatsApp Web
- `gspread` + Google Service Account para leer/escribir el Sheet
- `streamlit` para el dashboard
- Google Sheet único: `eventos_canal_whatsapp` con pestañas EVENTOS, FUENTES_WEB, LOG

## Estructura del proyecto

```
scraper-eventos/
├── main.py                       # Orquestador del scraping
├── config.py                     # Constantes y env vars (SHEET_ID, WA_*)
├── sheets_client.py              # Wrapper de gspread
├── deduplicator.py               # Dedup local (al insertar) + global por título
├── caption.py                    # Generador de texto para WhatsApp
├── dashboard.py                  # Streamlit — panel de curación
├── whatsapp_publisher.py         # Playwright sobre WhatsApp Web
├── bot_publicador.py             # Cola de publicación al canal
│
├── scrapers/
│   ├── base.py                   # BaseScraper con requests + BS4
│   ├── base_playwright.py        # BasePlaywrightScraper para sitios JS
│   ├── simple.py                 # Scraper genérico configurable
│   └── sitios/
│       ├── idartes.py            # ~38 eventos
│       ├── plancpereira.py       # ~59 eventos
│       ├── bogota_agenda.py
│       ├── teatromayor.py
│       ├── teatrolibre.py
│       ├── tuboleta.py           # Playwright
│       ├── eventbrite.py         # Playwright
│       ├── fever.py              # Playwright (parsea JSON de astro-island)
│       ├── latiquetera.py        # Playwright
│       ├── eticketablanca.py     # Playwright (213 eventos)
│       ├── taquillalive.py       # Playwright
│       ├── biblored.py
│       ├── planetario.py
│       ├── visitbogota.py
│       └── fuga.py               # Playwright
│
├── credentials/
│   └── service-account.json      # Credenciales Google (gitignored)
│
├── wa_session/
│   └── user-data/                # Perfil persistente Chromium con login WA
│
├── logs/
│   └── scraper.log               # Log de cada corrida
│
├── .env                          # SHEET_ID, WA_CANAL_*
├── requirements.txt
├── run_scraper.bat               # Wrapper para Task Scheduler
├── install_scheduled_task.ps1    # Registra tarea diaria 08:00 AM
└── OPERACIONES.md                # Paso a paso semanal recurrente
```

## Comandos principales

| Necesidad | Comando |
|---|---|
| Scrapear todo (modo manual) | `python main.py` |
| Curar eventos | `streamlit run dashboard.py` |
| Probar caption sin publicar | `python bot_publicador.py --canal TEST --ciudad Bogotá --una-sola --dry-run --ignorar-ventana` |
| Publicar 1 evento al canal TEST | `python bot_publicador.py --canal TEST --ciudad Bogotá --una-sola --ignorar-ventana` |
| Modo cola completo | `python bot_publicador.py --canal Bogotá --ciudad Bogotá` |
| Setup QR de WhatsApp Web | `python whatsapp_publisher.py --setup` |
| Re-correr dedup global manualmente | ver `OPERACIONES.md` |

## Setup desde cero (si quisieras instalar en otra máquina)

1. Instalar **Python 3.13** desde python.org marcando "Add to PATH"
2. Clonar el proyecto en una carpeta
3. `pip install -r requirements.txt`
4. `playwright install chromium`
5. Crear Google Service Account, descargar JSON a `credentials/service-account.json`, compartir el Sheet con el email del service account
6. Crear `.env` con `SHEET_ID`, `WA_CANAL_TEST`, etc.
7. `python whatsapp_publisher.py --setup` y escanear QR
8. Listo. Usar comandos de la tabla anterior.

## Para el operativo del día a día

**Mira [OPERACIONES.md](OPERACIONES.md)** — tiene el flujo semanal exacto, qué correr cada lunes, cómo aprobar, cómo dejar el bot publicando, troubleshooting común.

---

## 📜 Diseño original del proyecto (de las pestañas del Sheet)

El Google Sheet tiene 4 pestañas de documentación que sirvieron como brief
del proyecto. Este código las implementa en su mayoría.

### `PROMPT_WEB` — Spec del bot web

Brief original del bot que hoy es `main.py`:

- **Objetivo**: Python diario que rellena `EVENTOS` desde URLs de `FUENTES_WEB`
- **Output**: filas en EVENTOS con `fuente_tipo='web'`, actualización de `ultimo_scrape`/`ultimo_estado`, fila en LOG
- **Estructura propuesta**: `main.py`, `config.py`, `sheets_client.py`, `deduplicator.py`, `scrapers/`, `parsers/`, `credentials/`, `.env`
- **Dedup**: hash compuesto `nombre_evento + fecha_evento + lugar` (implementado en `deduplicator.es_duplicado`)
- **Deployment sugerido**: cron 8 AM local o Railway/Render. Implementado con Task Scheduler de Windows en `install_scheduled_task.ps1`.
- **Fases de implementación**: F1 baja complejidad (req+BS4), F2 paginación, F3 Playwright, F4 APIs
- **Estado actual**: F1+F2+F3 implementadas. F4 (APIs Eventbrite/Fever) no — usamos Playwright porque las APIs requieren approval de Meta/Eventbrite.

### `GUÍA_WEB` — Cómo funciona el flujo automatizado

Recomendaciones de implementación del bot web. Resumen:

- **Stack**: Python 3.11+, requests + BS4, Playwright para JS pesado, gspread, feedparser (no usado), APScheduler/cron
- **Estrategia por complejidad**:
  - **BAJA** (~30 sitios): requests + BS4 — gov.co, museos, teatros
  - **MEDIA** (~10 sitios): paginación o headers especiales — Plan C, Comfamiliar
  - **ALTA** (~10 sitios): Playwright — boleterías con JS pesado (TuBoleta, Eventbrite, Fever, Latiquetera, eTicketablanca, TaquillaLive)
  - **API**: Eventbrite y Fever tienen APIs públicas → usamos scraping en su lugar por simplicidad
- **Reglas del bot**: respetar robots.txt, delay 3s entre requests al mismo dominio, User-Agent identificable, ignorar fechas pasadas, mínimo capturar `nombre/fecha/lugar/ciudad/url`, marcar `activo=no` automáticamente si una fuente falla 3 veces seguidas (mejora futura)
- **Observabilidad**: cada corrida escribe a LOG con métricas

### `PROMPT_IG` y `GUÍA_IG` — Flujo manual con Claude in Chrome

`PROMPT_IG` es el prompt maestro para extracción manual de Instagram con Claude
in Chrome. `GUÍA_IG` es la guía operativa de qué cuenta como evento y qué no.
Ambas integradas en [OPERACIONES.md](OPERACIONES.md) sección "Paso 0".
