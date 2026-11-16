# Evidencias del núcleo completo · 2026-11-16

Rama `feat/nucleo-completo`. Pruebas contra **PostgreSQL 16 y Redis 7 en Docker**
(`docker compose up -d db redis`).

## Ciclos TDD del dominio

| Ciclo | Rojo | Verde | Refactor |
|---|---|---|---|
| D-05 duplicados (traído del PR #4) | `../03-tdd2-duplicados-rojo.txt` | `../04-…-verde.txt` | `../05-…-refactor.txt` |
| 01 formato de cantidades («5E+2 g») | `01-formato-cantidad-rojo.txt` | `01-…-verde.txt` | — |
| 02 renovación de vigencia (RF-14) | `02-renovacion-vigencia-rojo.txt` | `02-…-verde.txt` | — |
| 03 filtros por ubicación (RF-19) | `03-filtros-ubicacion-rojo.txt` | `03-…-verde.txt` | `03-…-refactor.txt` |
| 04 enlace a OpenStreetMap (RF-09) | `04-enlace-mapa-rojo.txt` | `04-…-verde.txt` | — |
| 05 valores de SIPSA (RF-07) | `05-sipsa-valores-rojo.txt` | `05-…-verde.txt` | — |

## Corrida final

| Archivo | Contenido |
|---|---|
| `final-pytest-unit.txt` | 98 aprobadas, 0 fallidas |
| `final-pytest-integracion.txt` | 115 aprobadas, 0 fallidas |
| `final-pytest-cobertura.txt` y `final-coverage.xml` | Cobertura total: 96 % (líneas y ramas) |
| `final-cobertura-dominio.txt` | `apps/*/domain`: 99 % por módulo |
| `final-ruff.txt` | Perfil del proyecto: 0 hallazgos. Perfil ampliado: por regla. Fuera de `tests/` solo quedan los que ya estaban en main y que corrige el PR #4 |
| `final-complejidad.txt` | Máxima: 6 (umbral 10) |
| `final-arquitectura.txt` | import-linter 6/6 contratos; migraciones al día |
| `axe-pantallas-nucleo.json` | axe-core 4.14 en las 10 pantallas nuevas, en claro y oscuro: 0 violaciones; objetivos ≥ 24 px |
