# Prueba de carga con k6 contra Render · 2026-11-16 (EC-04, M-08, M-09, M-10)

**Qué se hizo.** Se midió la aplicación desplegada en
`https://plataforma-precios-quindio.onrender.com` (plan Free de Render) con el script
[`pc01.js`](pc01.js), que sube la carga por escalones para encontrar hasta dónde se cumplen los
umbrales, en lugar de lanzar directamente los 500 usuarios del EC-04. Es el complemento de la
[medición local](../carga-k6/README.md) del mismo día.

## Condiciones

| Elemento | Valor |
|---|---|
| Aplicación | Render, Web Service Docker, plan Free (0,1 CPU, 512 MB); Gunicorn con `WEB_CONCURRENCY=1` (valor por defecto de `scripts/start.sh`) |
| Datos | 11 productos con precios en Armenia; entre 1 y 12 resultados por comparación |
| Generador de carga | k6 en un portátil con Windows, red doméstica en Colombia |
| Escenario | Solo lectura: 70 % `GET /api/v1/comparacion/<id>/?municipio=Armenia`, 20 % `GET /api/v1/catalogo/productos/?q=`, 10 % `GET /api/v1/establecimientos/?municipio=Armenia`; pausa de 1 a 3 s entre peticiones |
| Perfil | Escalones de 10, 25, 50 y 100 usuarios virtuales: 1 min de subida y 2 min sostenidos en cada uno, más 1 min de bajada (13 min) |
| Umbrales del script | `http_req_duration{escenario:comparacion}` p95 < 2000 ms; `http_req_failed` < 1 % |

## Ejecución 1: con el límite de uso real

Archivos: [`informe-ejecucion-1.html`](informe-ejecucion-1.html) y
[`captura-ejecucion-1-umbrales.png`](captura-ejecucion-1-umbrales.png).

| Medida | Resultado |
|---|---|
| Peticiones | 14 814 (18,96 por segundo) |
| Peticiones fallidas | **71,49 %** (10 591) |
| p95 de las respuestas exitosas | 371,8 ms (máximo 1,85 s) |

El **diagnóstico** con [`diagnostico.js`](diagnostico.js) (2 min, hasta 25 usuarios) contó **450
respuestas 200, 251 respuestas 429 y ningún error 5xx**. El cuerpo de las 429 era *«Solicitud fue
regulada (throttled)»*. Causa: el límite de lectura anónima es de 120 consultas por minuto **por
IP** ([ADR-0006](../../../../adr/0006-confiabilidad-del-dato-colaborativo.md)) y k6 genera toda la
carga desde una sola IP. Para la aplicación, la prueba equivalía a una sola persona haciendo unas 19
peticiones por segundo. Esta ejecución verifica que el límite funciona, pero no mide la capacidad.

## Ejecución 2: con el límite elevado solo durante la prueba

En Render se definieron temporalmente `LIMITE_ANONIMO=1000000/min` y `LIMITE_USUARIO=1000000/min`,
los mismos valores de la medición local, y se borraron al terminar. Archivos:
[`informe-ejecucion-2.html`](informe-ejecucion-2.html),
[`captura-ejecucion-2-resumen.png`](captura-ejecucion-2-resumen.png) y
[`ejecucion-2-por-tramos-de-10s.csv`](ejecucion-2-por-tramos-de-10s.csv) (datos de cada intervalo de
10 s, extraídos del informe).

| Medida | Umbral mínimo | Resultado | ¿Cumple? |
|---|---|---|---|
| Peticiones fallidas (M-09) | < 1 % | **0,00 %** (0 de 12 365) | Sí, en todos los escalones |
| p95 de la comparación, toda la prueba (M-08) | < 2000 ms | 1,76 s (p90 1,58 s; mediana 0,28 s; máximo 3,13 s) | Sí en el total, pero ver por escalón |
| CPU y memoria (M-10) | ≤ 80 % | **No medible:** el plan Free solo muestra el ancho de banda, con un punto por hora | — |

**Por escalón** (p95 de todas las peticiones en cada intervalo de 10 s):

| Usuarios | Peticiones por segundo | p95 por intervalo | ¿p95 < 2 s? |
|---|---|---|---|
| 10 | ~4,5 | 245–285 ms | Sí |
| 25 | ~11 | 250–325 ms | Sí |
| 50 | ~22 | 300–670 ms | Sí |
| 100 | **~28 (tope)** | **1,66–2,91 s** | No en 7 de los 12 intervalos |

## Interpretación

- Con 90 y 100 usuarios el servidor despachó las mismas ~28 peticiones por segundo mientras la
  latencia subía y no había errores: es **saturación de la CPU** de la instancia (0,1 CPU, un
  proceso), no fallas de la aplicación.
- El p95 de toda la prueba (1,76 s) queda bajo el umbral solo porque mezcla los escalones livianos.
  La comparación cumple **hasta unos 50 usuarios** concurrentes en el plan Free.
- Alcanzar los 500 usuarios del EC-04 requiere más CPU o más procesos
  ([ADR-0017](../../../../adr/0017-despliegue-en-paas-de-contenedores.md)). La vista materializada
  del [ADR-0004](../../../../adr/0004-cqrs-ligero-y-cache.md) no se necesita, porque el cuello de
  botella no fue la base de datos.
- Riesgo encontrado: muchos usuarios de redes móviles comparten una misma IP pública (CGNAT), así
  que un límite bajo por IP en las lecturas públicas podría frenar a consumidores reales en horas
  pico.

## Límites de esta medición

1. Instancia gratuita: no representa la capacidad prevista para producción.
2. Base de datos pequeña (11 productos), con casi todas las comparaciones servidas desde la caché.
3. Generador de carga en una red doméstica: la latencia incluye internet y HTTPS.
4. Solo lectura: no se midió el registro de precios.
5. Sin datos de CPU ni memoria (M-10).

## Cómo repetirla

1. En Render → *Environment*, agregar `LIMITE_ANONIMO=1000000/min` y `LIMITE_USUARIO=1000000/min` y
   desplegar (*Save, rebuild and deploy*).
2. Verificar que no aparezcan respuestas 429: `k6 run diagnostico.js`.
3. Despertar el servicio (abrir `/healthz/`) y correr:

   ```powershell
   $env:K6_WEB_DASHBOARD="true"; $env:K6_WEB_DASHBOARD_EXPORT="informe.html"; k6 run pc01.js
   ```

4. **Borrar las dos variables** y volver a desplegar, para restaurar los límites reales (120 y 240
   por minuto).
