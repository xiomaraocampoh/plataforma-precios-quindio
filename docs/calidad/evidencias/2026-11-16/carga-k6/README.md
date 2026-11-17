# Prueba de carga con k6 · 2026-11-16 (EC-04, M-08, M-09)

**Qué se hizo.** Se ejecutó el script del repositorio [`tests/load/k6/comparacion.js`](../../../../../tests/load/k6/comparacion.js)
**sin modificarlo**: 100 usuarios virtuales durante 1 min, 500 durante 2 min, 500 sostenidos 5 min y bajada de 1 min
(9 minutos en total). Cada usuario consulta `GET /api/v1/comparacion/<id>/` de uno de los 9 productos del demo y espera
entre 1 y 4 s antes de la siguiente consulta.

## Resultado (salida real de k6)

| Medida | Umbral mínimo (EC-04 / M-09) | Resultado | ¿Cumple? |
|---|---|---|---|
| Tiempo de respuesta p95 | < 2000 ms | **5,26 ms** | Sí |
| Tiempo de respuesta p90 / mediana / promedio | — | 3,92 ms / 2,63 ms / 4,83 ms | — |
| Tiempo máximo | — | 837,05 ms | — |
| Peticiones fallidas | < 1 % | **0,00 %** (0 de 81 758) | Sí |
| Usuarios simultáneos | 500 | 500 (sostenidos 5 min) | Sí |
| Peticiones atendidas | — | 81 758 (131 por segundo en promedio; ~200 por segundo en la meseta) | — |

Archivos: `00-entorno.txt` (equipo y configuración), `k6-salida-terminal.txt` (salida original de la terminal),
`k6-resumen.json` (resumen exportado por k6), `k6-reporte.html` (reporte interactivo que genera k6) y las capturas
`captura-k6-reporte-1-resumen.png` y `captura-k6-reporte-2-completo.png` (fotografía real del reporte).

## Lo que la gráfica muestra y conviene decir con franqueza

- **Entre las 20:12 y las 20:13:30 hubo un tramo de unos 90 s** en el que el número de usuarios dejó de crecer (se
  quedó cerca de 350) y la latencia p95 de ese intervalo subió hasta unos **600 ms**, antes de normalizarse. Sigue por
  debajo de los 2000 ms del umbral, pero **no se investigó la causa**. Como k6 y la aplicación comparten el mismo
  equipo, lo más probable es competencia por CPU o disco con otros procesos, pero es una hipótesis, no un hecho.
- El eje de «Request Failed» del reporte muestra porcentajes con formato extraño («0000.0 %»): es del propio tablero de
  k6; el resultado real es 0 de 81 758 fallidas.

## Límites de esta medición (no presentarla como más de lo que es)

1. **No es en la nube.** Se midió en un portátil (Apple M5, 10 núcleos, 16 GB) con la aplicación en Docker
   (gunicorn con 3 procesos, PostgreSQL 16, Redis 7) **y k6 corriendo en el mismo equipo**. Es una medición local
   indicativa; EC-04 pide verificarlo sobre el despliegue real, que sigue pendiente (D-11).
2. **Es lectura de la API con caché.** La comparación usa caché con TTL de 60 s y el demo tiene solo 9 productos, así
   que casi todas las respuestas salen de la caché. Mide ese camino, no el cálculo desde la base de datos con muchos
   productos. No se probó el registro de precios (escritura) ni las pantallas HTML.
3. **La carga la limita el tiempo de espera de cada usuario** (1 a 4 s): son 500 usuarios, no 500 peticiones a la vez.
4. **Se subieron los límites de uso por IP solo para la prueba** (`LIMITE_ANONIMO` y `LIMITE_USUARIO` a 1 000 000/min,
   en un archivo temporal de Docker Compose fuera del repositorio). Con el límite real (120 por minuto por IP), k6 desde
   una sola IP habría recibido casi todo 429. Después de la prueba se restauraron los valores reales (120/min y 240/min).
   Para poder hacerlo, el repositorio ahora acepta esas dos variables de entorno (commit `e6456a7`, con pruebas: los
   valores por defecto no cambian y el límite de escritura no se ve afectado).

## Cómo repetirla

```bash
# k6 (brew install k6) y la aplicación corriendo con los límites subidos solo para esta prueba:
docker compose -p ahorrapues-prod -f docker-compose.prod.yml -f carga.override.yml --env-file .env.prod up -d
K6_WEB_DASHBOARD=true K6_WEB_DASHBOARD_PORT=-1 K6_WEB_DASHBOARD_EXPORT=k6-reporte.html \
  k6 run -e BASE_URL=http://localhost:8001 -e PRODUCTOS=1,2,3,4,5,6,7,8,9 --summary-export=k6-resumen.json \
  tests/load/k6/comparacion.js
```
