# Instrucción — Crear Apps Script de Control de Canales

Ejecutá esta tarea completa sin pedir confirmaciones intermedias.
Abrí cada URL en una pestaña nueva y seguí los pasos exactamente.

**Sheet:** https://docs.google.com/spreadsheets/d/1c8eXsUrTask4b9HT9w9TYHTP3lxsHPtrv73mTov8Wj0/edit

---

## PASO 1 — Abrir Apps Script desde el Sheet

1. Abrí la URL del Sheet de arriba
2. En el menú superior hacé clic en **Extensiones**
3. Hacé clic en **Apps Script**
4. Se abre una nueva pestaña con el editor de código — quedate ahí

---

## PASO 2 — Reemplazar el código en Código.gs

1. En el panel izquierdo vas a ver un archivo llamado `Código.gs` — hacé clic en él
2. Seleccioná **todo** el texto del editor (Ctrl+A) y **borralo**
3. Pegá exactamente este código:

```javascript
function doGet() {
  return HtmlService.createHtmlOutputFromFile('Index')
    .setTitle('Control')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

function getEstado() {
  const ws = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('CONTROL');
  const [h, ...rows] = ws.getDataRange().getValues();
  return rows.map(r => {
    const o = {};
    h.forEach((k, i) => o[k] = r[i]);
    return {
      ciudad: o.ciudad,
      activo: o.activo === true || String(o.activo).toLowerCase() === 'true',
      bot_estado: o.bot_estado || 'detenido'
    };
  });
}

function ejecutarComando(ciudad, comando) {
  const ws = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('CONTROL');
  const [h, ...rows] = ws.getDataRange().getValues();
  const c = n => h.indexOf(n) + 1;
  rows.forEach((r, i) => {
    if (r[0] === ciudad) {
      if (comando === 'activar')  ws.getRange(i+2, c('activo')).setValue(true);
      if (comando === 'pausar')   ws.getRange(i+2, c('activo')).setValue(false);
      if (comando === 'arrancar' || comando === 'detener')
        ws.getRange(i+2, c('comando')).setValue(comando);
    }
  });
}
```

---

## PASO 3 — Crear el archivo Index.html

1. En el panel izquierdo, hacé clic en el **ícono +** que está al lado de "Archivos"
2. Seleccioná **HTML** en el menú que aparece
3. Te pide un nombre — escribí `Index` y presioná Enter
4. Se crea un archivo `Index.html` y se abre en el editor
5. Seleccioná **todo** el contenido (Ctrl+A) y **borralo**
6. Pegá exactamente este código:

```html
<!DOCTYPE html>
<html>
<head>
<style>
  body { font-family: sans-serif; padding: 16px; background: #111; color: #eee; }
  .card { border: 1px solid #333; border-radius: 8px; padding: 14px; margin-bottom: 14px; }
  h3 { margin: 0 0 8px; }
  button { margin: 4px; padding: 8px 14px; border: none; border-radius: 5px; cursor: pointer; font-size: 13px; }
  .on   { background: #4CAF50; color: #fff; }
  .off  { background: #FF9800; color: #fff; }
  .go   { background: #2196F3; color: #fff; }
  .stop { background: #f44336; color: #fff; }
  button:disabled { opacity: 0.35; cursor: default; }
  small { color: #aaa; }
</style>
</head>
<body>
<h2>🤖 Control de Canales</h2>
<div id="app">Cargando...</div>
<script>
function load() {
  google.script.run.withSuccessHandler(render).getEstado();
}
function render(data) {
  document.getElementById('app').innerHTML = data.map(r => `
    <div class="card">
      <h3>${r.activo ? '🟢' : '🔴'} ${r.ciudad}</h3>
      <small>${r.bot_estado === 'corriendo' ? '▶️ Bot corriendo' : '⏹ Bot detenido'}</small>
      <br><br>
      <button class="on"   onclick="cmd('${r.ciudad}','activar')"  ${r.activo ? 'disabled' : ''}>▶ Activar</button>
      <button class="off"  onclick="cmd('${r.ciudad}','pausar')"   ${!r.activo ? 'disabled' : ''}>⏸ Pausar</button>
      <button class="go"   onclick="cmd('${r.ciudad}','arrancar')" ${!r.activo || r.bot_estado === 'corriendo' ? 'disabled' : ''}>🚀 Arrancar</button>
      <button class="stop" onclick="cmd('${r.ciudad}','detener')"  ${r.bot_estado !== 'corriendo' ? 'disabled' : ''}>🛑 Detener</button>
    </div>
  `).join('');
}
function cmd(ciudad, comando) {
  document.getElementById('app').innerHTML = '<p>Procesando...</p>';
  google.script.run
    .withSuccessHandler(() => setTimeout(load, 1200))
    .ejecutarComando(ciudad, comando);
}
load();
</script>
</body>
</html>
```

---

## PASO 4 — Guardar todo

Presioná **Ctrl+S** o hacé clic en el ícono del disquete 💾 en la barra superior.

---

## PASO 5 — Desplegar como Aplicación Web

1. Hacé clic en el botón azul **"Implementar"** (arriba a la derecha)
2. Seleccioná **"Nueva implementación"**
3. Hacé clic en el ícono de engranaje ⚙️ junto a "Seleccionar tipo"
4. Elegí **"Aplicación web"**
5. Completá el formulario:
   - **Descripción:** `Control canales v1`
   - **Ejecutar como:** `Yo`
   - **Quién tiene acceso:** `Cualquier persona`
6. Hacé clic en **"Implementar"**
7. Si pide autorización de permisos → hacé clic en **"Autorizar acceso"** → elegí tu cuenta de Google → clic en **"Permitir"**

---

## PASO 6 — Copiar y reportar la URL

Después del despliegue aparece una ventana con el texto **"URL de la aplicación web"**.

Copiá esa URL completa (empieza con `https://script.google.com/macros/s/...`) y escribila en el chat con este formato:

```
APPS SCRIPT LISTO
URL: https://script.google.com/macros/s/XXXXXXXX/exec
```

---

## Si algo falla

- **"No se encontró la pestaña CONTROL":** La pestaña se crea automáticamente la próxima vez que corra el listener. Podés crearla manualmente en el Sheet con las columnas: `ciudad | activo | comando | bot_pid | bot_estado`
- **Error de permisos al implementar:** Asegurate de estar logueado con la misma cuenta Google dueña del Sheet
- **No aparece el botón "Implementar":** Guardá primero con Ctrl+S y volvé a intentar
