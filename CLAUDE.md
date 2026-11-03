# CLAUDE.md — Plataforma colaborativa de comparación de precios (Armenia / Quindío)

> Contexto permanente para asistentes de IA que trabajen en este repositorio o en el Claude
> Project "Arquitectura y modelos". Léelo completo antes de proponer o escribir código.

## 1. Proyecto en una página

- **Qué es:** plataforma web (uso mayoritario en celular) para registrar, consultar y comparar
  precios de la canasta familiar entre tiendas de barrio, minimercados y supermercados.
- **Qué NO es:** no vende, no cobra, no hace pedidos ni domicilios, no recomienda por perfilamiento,
  no es sistema oficial de precios. Si una propuesta toca eso, está fuera de alcance.
- **Curso:** Proyecto Nuclear, 6.º semestre (II-2026) — Arquitectura de Software II + Modelos de Calidad,
  Ing. Rubén Darío Díaz Bautista. Corporación Universitaria Empresarial Alexander von Humboldt.
- **Equipo:** María Luisa Londoño Moncada, Xiomara Ocampo Hurtado, Juan Manuel Rodríguez.
- **Actores:** Consumidor (con o sin cuenta) · Reportante · Comercio (voluntario) · Moderador.
- **Stack:** Python 3.12 · Django 5.2 LTS · Django REST Framework + drf-spectacular (OpenAPI) ·
  HTMX 2 (servido desde `static/vendor`) · PostgreSQL 16 · Redis (caché en prod) · pytest.
- **Estilo arquitectónico:** monolito modular multicapa (ADR-0001).

## 2. Reglas inviolables

1. **Neutralidad (EC-06):** el orden de la comparación depende SOLO de
   `comparacion.domain.ranking._clave_neutral` (precio por unidad → nombre → id). Nunca añadir a la
   clave atributos comerciales (promoción, perfil verificado, patrocinio). Las promociones se
   muestran como etiqueta `es_promocion`.
2. **Privacidad (Ley 1581 de 2012):** ninguna respuesta pública (API o plantilla) incluye autor,
   usuario, correo ni ubicación de un reportante. Los serializers públicos usan **lista blanca**
   de campos; jamás `fields = "__all__"`.
3. **Escritura autenticada (M-13):** todo endpoint que escribe exige `IsAuthenticated` y un
   `throttle_scope`.
4. **No adelantar el módulo comercial:** `apps/comercios` se construye en el Corte III. Hacerlo
   antes invalida la medición de EC-05 (M-17, M-18).
5. **TDD en reglas de negocio:** primero la prueba roja en `tests/unit/`, luego el código en
   `apps/<app>/domain/`, luego refactor. Cada commit de dominio debe poder mostrar ese ciclo.
6. **Repositorio:** privado. Colaboradores autorizados además de la propietaria
   (`xiomaraocampoh`): `LuisaL1`, `ddeelena` (Derlye) y Juan Manuel (invitado por correo; anotar
   aquí su usuario de GitHub cuando acepte). Cualquier otro acceso lo decide solo la propietaria.
   Nunca proponer agregar bots, cuentas de IA ni integraciones con permisos de escritura
   como colaboradores.
7. **Integridad académica:** el uso de IA se declara en la plantilla de PR; cada integrante debe
   poder explicar el código. No generar trabajo que el equipo no pueda defender.

## 3. Arquitectura y capas

```
interfaces   views.py (HTMX)  ·  api/ (DRF)  ·  admin.py         ← HTTP, formularios, serialización
aplicación   services.py (escritura, transacciones)  ·  selectors.py (lectura, caché)
dominio      domain/*.py — Python puro, sin imports de Django, 100 % probado
persistencia models.py (ORM) · migrations/
```

Reglas de dependencia:
- `domain` no importa nada de Django ni de otras capas.
- `views`/`api` llaman a `services`/`selectors`; **no** escriben con el ORM directamente.
- Entre apps solo se importa `services`, `selectors`, `domain` o `models` (para FK). Nunca
  `views` de otra app.
- Lógica en plantillas: solo presentación (`if`, `for`, filtros). Cálculos van al selector.

Módulos (apps):
| App | Actor | Responsabilidad |
|---|---|---|
| `cuentas` | todos | Usuario personalizado, rol, consentimiento de datos |
| `catalogo` | — | Productos, presentaciones, normalización por unidad, duplicados (D-05) |
| `establecimientos` | — | Directorio con ubicación |
| `precios` | Reportante | Registro, vigencia, confianza, anomalías, idempotencia offline |
| `comparacion` | Consumidor | Lado lectura: búsqueda, comparación neutral, caché |
| `moderacion` | Moderador | Denuncias, revisión de reportes `en_revision` |
| `integraciones` | — | Puertos/adaptadores a fuentes externas (SIPSA) con timeout |
| `comercios` | Comercio | **Corte III**: perfil, precio oficial, promociones |

Caché (ADR-0002): cache-aside por producto (`core.cache.clave_comparacion`), TTL 60 s,
invalidación en `transaction.on_commit` dentro del servicio que escribe. Toda clave nueva lleva
prefijo de versión (`v1`).

## 4. Convenciones de código

- **PEP 8 vía Ruff** (`ruff check . && ruff format .`), línea máx. 100, complejidad ≤ 10.
- Nombres de dominio **en español** (modelos, campos, funciones); palabras clave y librerías en inglés.
- Funciones de servicio con argumentos solo por nombre (`def registrar_reporte(*, autor, ...)`).
- Dinero y cantidades: `Decimal`, nunca `float`. Precios `DecimalField(12, 2)`.
- Fechas: `timezone.now()`, `USE_TZ=True`, zona `America/Bogota`.
- Modelos: `TextChoices` para enumeraciones; restricciones en BD (`CheckConstraint`,
  `UniqueConstraint`) además de validación en formularios; índices declarados en `Meta`; FKs con
  `on_delete=PROTECT` salvo composición real; `__str__` siempre definido.
- Consultas: `select_related`/`prefetch_related` obligatorios en listados; prohibido N+1.
- Migraciones: una por cambio lógico, revisadas en el PR, nunca editar una ya fusionada en `main`.
- HTMX: la misma vista sirve página completa o fragmento (`request.htmx`); fragmentos en
  `templates/<app>/partials/_nombre.html`; token CSRF en `hx-headers` del `<body>`; usar
  `hx-disabled-elt` en formularios para evitar doble envío.
- Accesibilidad: `label` en cada control, `aria-live` para resultados dinámicos, contraste ≥ 4.5:1,
  objetivos táctiles ≥ 24 px, sin depender solo del color.
- Commits: Conventional Commits (`feat(precios): …`, `test(catalogo): …`, `refactor: …`).
  Ramas: `main` (protegida) ← `develop` ← `feat/<tema>`. PR con al menos una revisión.

## 5. Pruebas

- `tests/unit/` — dominio puro, marcador `unit`, sin BD, rápido.
- `tests/integration/` — API/servicios con BD, marcador `integration`.
- Cobertura: dominio ≥ 90 %, total ≥ 80 % (mínimos 80/70; el CI falla por debajo de 70).
- `tests/load/k6/comparacion.js` — prueba de carga; se ejecuta con **k6**, no con pytest
  (umbral p95 < 2000 ms, errores < 1 %).
- Cada prueba nueva que verifique una métrica lleva el ID en un comentario (`# M-15`).

## 6. Checklists ISO/IEC 25010:2023 (aplicar en cada cambio)

**Adecuación funcional** (corrección, completitud)
- [ ] ¿La regla está en `domain/` y tiene prueba con casos límite (0, negativos, unidades distintas)?
- [ ] ¿El precio por unidad se calcula con `precio_por_unidad` y nunca a mano?
- [ ] ¿El orden de resultados sigue siendo el declarado (M-06 = 100 %)?

**Capacidad de interacción** (operabilidad, protección contra errores, inclusividad, aprendibilidad)
- [ ] ¿El registro sigue siendo ≤ 3 campos visibles y completable en ≤ 15 s con 3G (M-01)?
- [ ] ¿Se valida presentación/unidad para evitar registrar en la unidad equivocada (M-02)?
- [ ] ¿Pasa axe/Lighthouse sin fallos A y con criterios AA (M-03)?

**Seguridad** (integridad, autenticidad, responsabilidad, confidencialidad, resistencia)
- [ ] ¿Escritura autenticada + throttling? ¿Se guarda autor y fecha (M-13, M-14)?
- [ ] ¿La respuesta pública omite datos del reportante (M-15 = 0 exposiciones)?
- [ ] ¿Entradas validadas en serializer **y** restricción en BD? ¿Sin SQL crudo con f-strings?
- [ ] ¿Secretos solo por variables de entorno?

**Eficiencia de desempeño** (comportamiento temporal, capacidad, recursos)
- [ ] ¿La consulta usa índices existentes y un número constante de queries?
- [ ] ¿La lectura pasa por un selector cacheado y la escritura invalida la clave?

**Mantenibilidad** (modularidad, modificabilidad, testabilidad, analizabilidad)
- [ ] ¿El cambio respeta las reglas de dependencia de la sección 3?
- [ ] ¿Ruff limpio, complejidad ≤ 10, sin código muerto?
- [ ] ¿Si cambió una decisión estructural, hay ADR nuevo o actualizado?

## 7. Escenarios y umbrales de referencia

| ID | Medida (mínimo aceptable) |
|---|---|
| EC-01 | Registro ≤ 15 s en ≥ 80 % de intentos (objetivo 90 %) |
| EC-02 | Precio anterior deja de mostrarse como vigente en ≤ 5 min (objetivo 1 min) |
| EC-03 | Detección de anómalos ≥ 80 %, falsos positivos ≤ 10 % |
| EC-04 | p95 ≤ 2 s con 500 concurrentes, error ≤ 1 % |
| EC-05 | Desviación de esfuerzo ≤ ±30 %, 0 cambios estructurales al núcleo |
| EC-06 | Orden neutral y promoción distinguida en 100 % de casos |

## 8. Cómo trabajar con este repositorio

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements/dev.txt
cp .env.example .env
docker compose up -d db redis
python manage.py migrate && python manage.py runserver
pytest -m unit            # ciclo TDD rápido
pytest --cov              # todo + cobertura
```

Al pedir ayuda a la IA: indica la app, la capa y la métrica afectada. La IA debe responder
con prueba primero cuando el cambio toque `domain/`, y nunca modificar `_clave_neutral` ni los
serializers públicos sin señalarlo explícitamente.
