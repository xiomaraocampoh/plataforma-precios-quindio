# Evidencias del cierre del corte 2 · 2026-11-16

Rama `feat/cierre-corte-2`. Las pruebas usan **SQLite en memoria**: el equipo donde se generaron no
tiene Docker y no pudo levantar PostgreSQL ni Redis. El CI de GitHub Actions las repite contra
PostgreSQL 16.

| Archivo | Contenido |
|---|---|
| `01-inicial-*` | Línea base antes de los cambios: pytest (unitarias, integración, cobertura), Ruff e import-linter |
| `02-tdd1-confianza-mediana-cero.txt` | Prueba de caracterización de la mediana cero (`confianza.py`) |
| `03-tdd2-duplicados-rojo.txt` | D-05 en rojo: el módulo no existe |
| `04-tdd2-duplicados-verde.txt` | D-05 en verde: código mínimo |
| `05-tdd2-duplicados-refactor.txt` | D-05 tras el refactor, sin cambio de comportamiento |
| `06-ruff-ampliado-despues.txt` | Perfil ampliado de Ruff: solo quedan los hallazgos aceptados |
| `07-final-*` | Corrida final: pytest, cobertura (`coverage.xml`), Ruff e import-linter |
| `08-cobertura-dominio.txt` | Cobertura de `apps/*/domain` por módulo |
| `09-complejidad.txt` | Complejidad ciclomática (McCabe) de las funciones más complejas |
| `sonarqube.md` y `sonarqube/` | SonarQube **ejecutado**: informe, capturas reales del panel y antes/después de los hallazgos |
| `carga-k6/` | Prueba de carga con k6 (500 usuarios, 9 min): salida de terminal, resumen, reporte HTML y capturas reales |
| `10-m22-e2e-rojo.txt` | Rama `feat/registro-sin-conexion`: prueba de navegador en rojo (aún sin `cola-registros.js`) |
| `10-m22-e2e-verde.txt` | La misma prueba en verde (Playwright 1.65, Chromium) |
| `10-m22-resultado.json` | **M-22** con 10 registros simulados (5 con la respuesta perdida y 5 sin señal): 10/10 sincronizados = 100 %, 0 duplicados. Umbral aceptable ≥ 98 % |

| Indicador | Inicial | Final |
|---|---|---|
| Pruebas unitarias | 37 aprobadas | 55 aprobadas, 0 fallidas |
| Pruebas de integración | 21 aprobadas | 21 aprobadas, 0 fallidas |
| Cobertura total (líneas + ramas) | 79 % | 80 % (líneas 553/681 = 81,2 %) |
| Cobertura del dominio | — | 100 % de líneas (148/148), 99 % con ramas |
| Ruff, perfil del proyecto | 0 hallazgos | 0 hallazgos |
| Ruff, perfil ampliado | 46 | 38, todos aceptados |
| Complejidad máxima | — | 6 (`registrar_reporte`, `_calcular_comparacion`); umbral 10 |
| import-linter | 6/6 contratos | 6/6 contratos |
