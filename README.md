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

## Correo con Brevo (ADR-021)

Los correos (verificación, seguridad, códigos de dos pasos y moderación) salen de verdad por el relé
SMTP de Brevo, en desarrollo y en producción. Sin `EMAIL_HOST` se imprimen en la consola, y las
pruebas nunca salen a la red.

1. **Crear la cuenta:** regístrate gratis en [brevo.com](https://www.brevo.com). El plan gratuito
   envía 300 correos al día.
2. **Verificar el remitente:** en *Senders, Domains & Dedicated IPs → Senders*, agrega
   `ahorrapuescolombia@gmail.com` con el nombre «AhorraPues». Abre el correo de Brevo que llega a esa
   bandeja y confírmalo.
3. **Generar la clave SMTP:** en *Settings → SMTP & API → SMTP*, pulsa *Generate a new SMTP key*.
   Usa la clave **SMTP**, que empieza por `xsmtpsib-`, y no la de API (`xkeysib-`). El *Login* de
   esa misma pestaña, que termina en `@smtp-brevo.com`, va en `EMAIL_HOST_USER`.
4. **Llenar el `.env`:** copia el bloque de correo de `.env.example` y reemplaza el usuario, la
   clave y el remitente. **El `.env` nunca se versiona:** compruébalo con `git ls-files .env`, que
   debe salir vacío. Si tu red bloquea el puerto 587, usa `EMAIL_PORT=2525`.
5. **Probar:** `python manage.py sendtestemail tu-correo@ejemplo.com`. Debe llegar en menos de un
   minuto; revisa también la carpeta de spam (ver ADR-021, remitente `@gmail.com`).
6. **Reintentos:** deja corriendo `python manage.py enviar_correos --continuo`, o prográmalo cada
   minuto, para reenviar lo que falló.

- Vista previa de cada plantilla (como staff): http://localhost:8000/panel/correos/vista-previa/

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
