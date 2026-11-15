# Plataforma colaborativa de comparación de precios — Armenia / Quindío

Proyecto Nuclear · 6.º semestre (II-2026) · Arquitectura de Software II · Modelos de Calidad
Corporación Universitaria Empresarial Alexander von Humboldt

**Equipo:** María Luisa Londoño Moncada · Xiomara Ocampo Hurtado · Juan Manuel Rodríguez

## Arranque local

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements/dev.txt
cp .env.example .env
# htmx 2.0.4 ya viene versionado en static/vendor/ (sin CDN; licencia 0BSD en htmx.LICENSE)
docker compose up -d db redis
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

- App: http://localhost:8000 · API docs (OpenAPI): http://localhost:8000/api/docs/
- Pruebas: `pytest -m unit` (TDD rápido) · `pytest --cov` (todo)
- Límites de arquitectura: `lint-imports` (contratos en `.importlinter`)
- Salud: http://localhost:8000/healthz/ (PostgreSQL y caché)
- Carga: `k6 run tests/load/k6/comparacion.js`

## Documentación

- `CLAUDE.md` — reglas de código, arquitectura y checklists ISO/IEC 25010 (léelo primero)
- `docs/adr/` — decisiones arquitectónicas
- `docs/calidad/trazabilidad-metricas.md` — métrica → prueba/herramienta
- `docs/arquitectura/c4/` — diagramas C4 (contexto, contenedores, componentes)
- `docs/operacion/auditoria-accesos.md` — revisión periódica de colaboradores (sin bots)

## Declaración de uso de IA

El esqueleto inicial y parte de la documentación se elaboraron con apoyo de un asistente de IA
generativa, revisado por el equipo. Cada PR declara el uso de IA en su plantilla, según la guía.
