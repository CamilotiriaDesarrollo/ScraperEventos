# Protocolo de Depuración — FUENTES_IG
**Reutilizable · Se adapta al estado actual del Sheet · Ejecutar por bloques**

**Sheet (pestaña FUENTES_IG):**
https://docs.google.com/spreadsheets/d/1c8eXsUrTask4b9HT9w9TYHTP3lxsHPtrv73mTov8Wj0/edit?gid=1605809649#gid=1605809649

---

## ★ PUNTO DE ARRANQUE — completar antes de pegar

> Editá esta línea antes de copiar el documento y pegarlo en Claude in Chrome:

**Empezar desde la fila número: `___`**
*(Si dejás ___ en blanco, Claude arranca desde la primera fila que necesite revisión)*

Ejemplos de cómo llenarlo:
- `Empezar desde la fila número: 53` → arranca exactamente en esa fila
- `Empezar desde la fila número: 80` → salta todo lo anterior
- `Empezar desde la fila número: ___` → modo automático, Claude decide

---

## Cómo usar este protocolo

Este documento funciona siempre, sin importar cuántas cuentas haya en el Sheet.
Cada vez que lo ejecutes, Claude lee el Sheet en ese momento y trabaja con lo que encuentre.

**Una sesión = un bloque de 20 cuentas.**

Pasos para cada sesión:
1. Abrí el Sheet en una pestaña de Chrome
2. Abrí Claude in Chrome
3. Pegale **todo este documento**
4. Claude identifica las primeras 20 cuentas que necesitan revisión y las procesa
5. Al terminar te da un reporte y se detiene
6. La próxima sesión retoma desde donde quedó

---

## ═══ PASO 1 — Identificar qué revisar ═══

Al abrir el Sheet, Claude debe identificar las filas que necesitan trabajo en este orden de prioridad:

### Prioridad 1 — Filas sin ID (cuentas nuevas sin procesar)
Son filas donde la columna A está vacía pero la columna D tiene una URL de Instagram.
Estas son cuentas candidatas que nunca fueron evaluadas.
→ Procesar primero, de arriba hacia abajo.

### Prioridad 2 — Filas con ID pero `ultima_revision` vacía
Registros completos que nunca fueron auditados.
→ Procesar en segundo lugar.

### Prioridad 3 — Filas con ID y `ultima_revision` de hace más de 60 días
Registros que necesitan re-auditoría periódica.
→ Procesar en tercer lugar.

### No procesar
- Filas ya revisadas hace menos de 60 días (ultima_revision reciente)
- Filas marcadas en rojo (ya fueron descartadas, el usuario las eliminará)
- Filas vacías sin ningún dato

**Tomar las primeras 20 filas que califiquen** según ese orden de prioridad. Reportar al inicio cuántas encontró de cada tipo.

---

## ═══ PASO 2 — Evaluar cada cuenta ═══

Para cada una de las 20 cuentas seleccionadas:

### 2a. Abrir el perfil
Copiá la URL de la columna D y abrila en Instagram en una nueva pestaña.

### 2b. Aplicar los 4 criterios

**MANTENER** si cumple los 4:

**Criterio 1 — Existe y es público**
- El perfil carga, tiene foto, nombre visible y posts accesibles
- NO está eliminado, suspendido ni en modo privado

**Criterio 2 — Activo en el último mes**
- Tiene al menos un post en los últimos 30 días
- Si el post más reciente es de hace más de 30 días → **ROJO**
- Si tiene menos de 3 posts en total → **ROJO**

**Criterio 3 — Publica eventos reales**
Revisá los últimos 5 posts. Un post es evento válido si tiene los 3:
- Fecha futura específica (día concreto — no "próximamente", no "todos los viernes")
- Lugar físico (venue, sala, dirección) o link de transmisión
- Nombre o título del evento

Si 3 o más de los 5 posts son eventos válidos → mantener
Si menos de 2 son eventos válidos → **ROJO**

**No son eventos válidos:**
lifestyle · fotos de comida · frases inspiracionales · promociones y descuentos
convocatorias y castings · eventos privados (grados, bodas, corporativos)
publicaciones de servicios sin fecha de evento · contenido de marca genérico

**Criterio 4 — Ciudad correcta**
- Los eventos son principalmente de Bogotá o Pereira
- Cuentas de Medellín, Cali u otras ciudades → **ROJO**
- Cuentas nacionales sin foco en Bogotá/Pereira → **ROJO**

---

## ═══ PASO 3 — Actuar en el Sheet ═══

### Si la cuenta NO pasa (cualquier criterio fallido)
1. Seleccionar toda la fila en el Sheet
2. Formato → Color de fondo → **Rojo**
3. En columna K escribir la razón en máximo 4 palabras:
   - `no existe / privada`
   - `inactiva +30 días`
   - `no publica eventos`
   - `ciudad incorrecta`
   - `menos de 3 posts`
   - `solo publicidad`
   - `cuenta personal`

### Si la cuenta SÍ pasa y ya tiene ID (registro completo)
1. Verificar que todos los campos estén llenos. Completar lo que falte.
2. Actualizar columna J (`ultima_revision`) con la fecha de hoy
3. No cambiar el color de la fila

### Si la cuenta SÍ pasa y NO tiene ID (cuenta nueva)
Completar todos los campos:

| Columna | Campo | Cómo obtenerlo |
|---------|-------|----------------|
| A | id | Ver instrucción de IDs abajo |
| B | tipo | `instagram` |
| C | perfil | @handle extraído de la URL (ej: `/tallerlarva/` → `@tallerlarva`) |
| D | url | Ya está |
| E | nombre_real | El nombre visible en el perfil (no el @handle) |
| F | ciudad | `Bogotá` o `Pereira` |
| G | categoria | Ver lista de categorías válidas abajo |
| H | seguidores_aprox | Número de seguidores del perfil (con K si aplica: 12K, 1.5K) |
| I | activo | `sí` |
| J | ultima_revision | Fecha de hoy en formato YYYY-MM-DD |
| K | notas | Una línea: qué tipo de contenido publica |

**Instrucción de IDs:**
- Los IDs F001–F138 ya están en uso en FUENTES_IG (136 cuentas activas, filas F081 y F129 vacías)
- Los IDs de FUENTES_WEB son independientes y están en su propia pestaña
- Las cuentas nuevas aprobadas van desde **F200** en adelante
- Antes de asignar, mirar el ID más alto que exista en la columna A y continuar desde ahí
- Si el más alto es F212, el siguiente es F213

---

## ═══ PASO 4 — Reporte al terminar el bloque ═══

Cuando termines las 20 cuentas, reportar en el chat:

```
BLOQUE COMPLETADO — [fecha]
─────────────────────────────
Cuentas revisadas: 20
  · Aprobadas y actualizadas: N
  · Aprobadas y completadas (eran nuevas): N
  · Marcadas en rojo: N

Rechazadas:
  @handle — razón
  @handle — razón
  ...

Cuentas grises (duda): 
  @handle — explicación

Pendientes para próxima sesión:
  Quedan aprox. N cuentas sin revisar en el Sheet
  Siguiente prioridad: [tipo de fila que toca]
```

Después de dar el reporte, **detenerse**. No continuar con más cuentas sin que el usuario lo indique.

---

## ═══ REFERENCIA — Categorías válidas ═══

```
agenda cultural          bar / música en vivo      bar / shows
bar / fiestas            bar / rock                cine / festivales
cultural / música        discoteca                 discoteca / electrónica
discoteca / techno       espacio cultural          espacio cultural oficial
ferias / mercados        gastronomía / música      música / festival
música alternativa       música / promotor         oficial cultural
teatro                   teatro / conciertos       teatro / festivales
turismo oficial          arte / exposiciones
```

---

## ═══ REFERENCIA — Decisión en 30 segundos ═══

```
¿Perfil existe y es público?         NO → rojo ("no existe / privada")
¿Publicó en los últimos 30 días?     NO → rojo ("inactiva +30 días")
¿Tiene 3+ posts en total?            NO → rojo ("menos de 3 posts")
¿3 de 5 posts son eventos válidos?   NO → rojo ("no publica eventos")
¿Eventos son de Bogotá o Pereira?    NO → rojo ("ciudad incorrecta")

Todo OK + tiene ID   → actualizar ultima_revision, completar campos vacíos
Todo OK + sin ID     → completar todos los campos, asignar ID desde F200+
```
