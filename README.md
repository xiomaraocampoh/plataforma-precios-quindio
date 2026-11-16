# Plataforma colaborativa de comparación de precios — Armenia / Quindío

Proyecto Nuclear · 6.º semestre (II-2026) · Arquitectura de Software II · Modelos de Calidad
Corporación Universitaria Empresarial Alexander von Humboldt

**Equipo:**

- María Luisa Londoño Moncada
- Xiomara Ocampo Hurtado
- Juan Manuel Rodríguez Pinzón
- Derly Elena Quejada Perea

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
- Salud: http://localhost:8000/healthz/ (PostgreSQL y caché)
- Datos de ejemplo: `python manage.py cargar_demo` (catálogo, tiendas y precios; idempotente)

Sin Docker, el proyecto arranca con SQLite y caché en memoria. En `.env` usa
`DATABASE_URL=sqlite:///db.sqlite3` y deja `REDIS_URL` vacío.

## Pruebas y calidad

```bash
pytest -m unit -v                     # dominio puro, sin BD (ciclo TDD rápido)
pytest -m integration -v              # API y servicios con BD
pytest --cov --cov-report=term --cov-report=xml   # todo + cobertura (el CI exige ≥ 70 %)
coverage run -m pytest -m unit && coverage report --include="apps/*/domain/*"   # dominio (meta ≥ 90 %)

ruff check .                          # PEP 8, seguridad, complejidad ≤ 10
ruff format --check .                 # formato (sin --check lo aplica)
lint-imports                          # límites de arquitectura (contratos en .importlinter)
```

- Las pruebas de integración usan PostgreSQL si `DATABASE_URL` apunta a él (como en el CI).
  Sin esa variable, `config/settings/test.py` usa SQLite en memoria.
- Revisión ampliada de Ruff (informativa, no la exige el CI):
  `ruff check . --extend-select PL,RUF,ARG,ERA,SIM,PIE,RET --statistics`.
- Carga (EC-04): `k6 run tests/load/k6/comparacion.js` (requiere [k6](https://k6.io)).
- **SonarQube:** genera `coverage.xml` con pytest y ejecuta el escáner con Docker según
  [docs/calidad/sonarqube.md](docs/calidad/sonarqube.md). La configuración está en
  `sonar-project.properties`.
- Las evidencias de cada corte se guardan en `docs/calidad/evidencias/<fecha>/`.

## Documentación

- `CLAUDE.md` — reglas de código, arquitectura y checklists ISO/IEC 25010 (léelo primero)
- `docs/adr/` — decisiones arquitectónicas
- `docs/calidad/trazabilidad-metricas.md` — métrica → prueba/herramienta
- `docs/calidad/sonarqube.md` — análisis estático con SonarQube en Docker
- `docs/arquitectura/c4/` — diagramas C4 (contexto, contenedores, componentes)
- `docs/operacion/auditoria-accesos.md` — revisión periódica de colaboradores (sin bots)

## Declaración de uso de IA

El esqueleto inicial y parte de la documentación se elaboraron con apoyo de un asistente de IA
generativa, revisado por el equipo. Cada PR declara el uso de IA en su plantilla, según la guía.
