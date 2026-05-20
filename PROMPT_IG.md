# Instrucción permanente — Scraping IG de eventos culturales

Ejecutá esta tarea completa sin pedir confirmaciones intermedias.

**Sheet:** https://docs.google.com/spreadsheets/d/1c8eXsUrTask4b9HT9w9TYHTP3lxsHPtrv73mTov8Wj0/edit
**Sheet ID:** 1c8eXsUrTask4b9HT9w9TYHTP3lxsHPtrv73mTov8Wj0
**Fecha de hoy:** (usá la fecha real del sistema)

> **PUNTO DE ARRANQUE:** ___
> (Opcional. Dejá vacío para que el script detecte automáticamente los pendientes.
> O escribí un @handle para que el script arranque desde ese perfil en adelante,
> ignorando todo lo anterior en la lista aunque esté pendiente.
> Ejemplo: `@mediatortabog`)

---

## PASO 1 — Identificar los próximos 15 perfiles a revisar

Abrí el Sheet y ejecutá este script en Apps Script (Extensiones → Apps Script):

```javascript
function getProximosPerfiles() {
  // Si hay PUNTO DE ARRANQUE definido arriba, pegalo aquí (con @ incluido).
  // Dejá vacío ('') para detección automática.
  var ARRANCAR_DESDE = '';  // Ejemplo: '@mediatortabog'

  var ss = SpreadsheetApp.openById('1c8eXsUrTask4b9HT9w9TYHTP3lxsHPtrv73mTov8Wj0');
  var sheet = ss.getSheetByName('FUENTES_IG');
  var data = sheet.getDataRange().getValues();
  var headers = data[0];
  var colActivo = headers.indexOf('activo');
  var colPerfil = headers.indexOf('perfil');
  var colUrl = headers.indexOf('url');
  var colCiudad = headers.indexOf('ciudad');
  var colRevision = headers.indexOf('ultima_revision');

  var hoy = new Date();
  var umbral = new Date(hoy.getTime() - 7 * 24 * 60 * 60 * 1000);

  // Si hay punto de arranque, saltar todo lo anterior en la lista
  var encontrado = ARRANCAR_DESDE === '';
  var pendientes = [];

  for (var i = 1; i < data.length; i++) {
    var perfil = String(data[i][colPerfil]).trim();
    if (!perfil) continue;

    // Esperar hasta encontrar el perfil de arranque
    if (!encontrado) {
      if (perfil.toLowerCase() === ARRANCAR_DESDE.toLowerCase()) {
        encontrado = true;
      } else {
        continue;
      }
    }

    var activo = String(data[i][colActivo]).trim().toLowerCase();
    if (activo !== 'sí' && activo !== 'si') continue;

    var revision = data[i][colRevision];
    var fechaRev = revision ? new Date(revision) : null;
    if (fechaRev && fechaRev >= umbral) continue;

    pendientes.push({
      fila: i + 1,
      perfil: perfil,
      url: String(data[i][colUrl]).trim(),
      ciudad: String(data[i][colCiudad]).trim(),
      revision: revision || 'nunca'
    });
    if (pendientes.length === 15) break;
  }

  var eventos = ss.getSheetByName('EVENTOS');
  var lastRow = eventos.getLastRow();
  var lastId = lastRow > 1 ? eventos.getRange(lastRow, 1).getValue() : 'EVT000';

  Logger.log('=== PROXIMOS 15 PERFILES ===');
  if (ARRANCAR_DESDE) Logger.log('(Arrancando desde: ' + ARRANCAR_DESDE + ')');
  for (var j = 0; j < pendientes.length; j++) {
    Logger.log((j+1) + '. ' + pendientes[j].perfil + ' | ' + pendientes[j].url + ' | ' + pendientes[j].ciudad);
  }
  Logger.log('Ultimo EVT: ' + lastId);
  Logger.log('Proxima fila en EVENTOS: ' + (lastRow + 1));
}
```

Ejecutá `getProximosPerfiles()` y leé el log. Esos son los perfiles a revisar en este bloque.

---

## PASO 2 — Revisar cada perfil en Instagram

Para cada perfil del log:

1. Abrí la URL en una pestaña nueva
2. Mirá solo los posts de los **últimos 7 días**
3. Evaluá mirando la imagen primero — solo abrí el post si necesitás confirmar fecha o lugar
4. Si es carrusel con varios eventos, extraé cada uno por separado
5. Cerrá la pestaña y seguí con el siguiente

**Evento válido = tiene los 3:**
- Fecha futura específica (día concreto)
- Lugar físico o link
- Nombre del evento

**No son eventos:** lifestyle · comida · frases · promociones · convocatorias · eventos privados

**Categorías válidas:** concierto · teatro · danza · exposición · taller · festival · fiesta · cine · gastronomía · feria · conversatorio · stand-up · lanzamiento · mercado

---

## PASO 3 — Escribir los eventos en el Sheet

Cuando termines los 15 perfiles, escribí todos los eventos de una vez con Apps Script:

```javascript
function addEventosToSheet() {
  var ss = SpreadsheetApp.openById('1c8eXsUrTask4b9HT9w9TYHTP3lxsHPtrv73mTov8Wj0');
  var sheet = ss.getSheetByName('EVENTOS');
  var hoy = Utilities.formatDate(new Date(), 'America/Bogota', 'yyyy-MM-dd');

  // REEMPLAZÁ con los eventos encontrados. Una fila por evento.
  // Formato: [id, fecha_extraccion, fuente_tipo, fuente, perfil_ig, nombre_evento,
  //           fecha_evento, hora, lugar, ciudad, categoria, descripcion, url_post,
  //           imagen_url, estado, notas]
  var eventos = [
    // ["EVT052", hoy, "instagram", "instagram", "@perfil", "Nombre evento",
    //  "2026-05-25", "20:00", "Venue", "Bogotá", "concierto", "Descripción",
    //  "https://instagram.com/p/...", "", "pendiente", ""],
  ];

  if (eventos.length === 0) {
    Logger.log('Sin eventos en este bloque.');
    return;
  }

  var lastRow = sheet.getLastRow();
  sheet.getRange(lastRow + 1, 1, eventos.length, 16).setValues(eventos);
  Logger.log('OK: ' + eventos.length + ' eventos agregados desde fila ' + (lastRow + 1));
}
```

---

## PASO 4 — Actualizar ultima_revision

```javascript
function updateRevision() {
  var ss = SpreadsheetApp.openById('1c8eXsUrTask4b9HT9w9TYHTP3lxsHPtrv73mTov8Wj0');
  var sheet = ss.getSheetByName('FUENTES_IG');
  var hoy = Utilities.formatDate(new Date(), 'America/Bogota', 'yyyy-MM-dd');

  // REEMPLAZÁ con los handles del bloque que revisaste
  var revisados = [
    // "@handle1", "@handle2", ...
  ];

  var data = sheet.getDataRange().getValues();
  var headers = data[0];
  var colPerfil = headers.indexOf('perfil');
  var colRevision = headers.indexOf('ultima_revision');

  for (var i = 1; i < data.length; i++) {
    if (revisados.indexOf(String(data[i][colPerfil]).trim()) !== -1) {
      sheet.getRange(i + 1, colRevision + 1).setValue(hoy);
    }
  }
  Logger.log('ultima_revision actualizada para ' + revisados.length + ' perfiles.');
}
```

---

## PASO 5 — Reportar y esperar

Escribí en el chat:

```
BLOQUE COMPLETADO
Perfiles revisados: N
Eventos registrados: N
Sin eventos: @handle (razón), ...
Con error: @handle (razón), ...
```

Luego **esperá**. Cuando el usuario diga **"siguiente bloque"**, volvé al PASO 1 y ejecutá `getProximosPerfiles()` de nuevo — el script automáticamente detecta cuáles perfiles siguen según la fecha de ultima_revision.
