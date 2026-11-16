# Despliegue reproducible

Cómo construir, levantar y comprobar AhorraPues con la imagen de producción. Corresponde al
ADR-017 (despliegue en un PaaS de contenedores) y al entregable AS-II 3.

> **Estado.** La imagen y el compose de producción están **verificados en local** (sección 9).
> **No hay despliegue en la nube todavía**: falta elegir el proveedor (decisión D-11 del equipo).
> La sección 7 explica qué cambia al llevarlo a uno.

## 1. Qué se levanta

```
                 ┌──────────────────────────── red interna de Docker ────────────────────────────┐
 navegador ──▶  web (gunicorn + WhiteNoise)  ──▶  db (PostgreSQL 16)
 :${WEB_PORT}      │                          └─▶  redis (Redis 7, caché de la comparación)
                   └── migrar (paso único: aplica las migraciones y termina)
```

| Servicio | Qué hace | ¿Publica puerto? |
|---|---|---|
| `web` | La aplicación Django con gunicorn; sirve también los estáticos (WhiteNoise) | Sí: `${WEB_PORT}` (8000 por defecto) |
| `migrar` | Ejecuta `migrate` una vez; `web` espera a que termine bien | No |
| `db` | PostgreSQL 16 con volumen persistente (`pgdata`) | No |
| `redis` | Caché compartida (TTL de 60 s, invalidada al registrar un precio) | No |

El despliegue usa el nombre de proyecto `ahorrapues-prod`, así que **no se mezcla** con el
`docker-compose.yml` de desarrollo (otros contenedores, red y volúmenes).

## 2. Requisitos

Docker con Compose v2 (Docker Desktop en Windows con WSL 2 o en macOS) y unos 2 GB libres de disco.
No hace falta Python instalado.

## 3. Primera vez

Desde la raíz del repositorio. Los comandos usan esta variable para abreviar:

```bash
export DC="docker compose -f docker-compose.prod.yml --env-file .env.prod"
```

1. **Crear las variables.** `.env.prod` nunca se versiona; solo existe la plantilla:

   ```bash
   cp .env.prod.example .env.prod
   python3 -c "import secrets; print(secrets.token_urlsafe(50))"   # úsala como SECRET_KEY
   python3 -c "import secrets; print(secrets.token_urlsafe(24))"   # úsala como POSTGRES_PASSWORD
   ```

   Edita `.env.prod`: reemplaza cada valor «cambia-…» y pon tu dominio en `ALLOWED_HOSTS` y
   `CSRF_TRUSTED_ORIGINS`. `POSTGRES_PASSWORD` solo admite letras, números, `-` y `_`.

2. **Construir y levantar:**

   ```bash
   $DC up -d --build
   $DC ps          # web debe quedar «healthy»; migrar aparece «exited (0)»
   ```

3. **Cargar datos de ejemplo (opcional):**

   ```bash
   $DC exec web python manage.py cargar_demo --con-vencidos
   ```

   Los usuarios `demo`, `demo_ana`, `demo_luis` y `demo_sofia` usan `DEMO_PASSWORD`; `admin` y
   `moderador_demo` usan `DEMO_ADMIN_PASSWORD`. Si esas variables están vacías, el comando genera
   una clave aleatoria y la muestra **una sola vez**.

## 4. Comprobaciones

Con el puerto por defecto. Si pusiste `FORZAR_HTTPS=True` (lo correcto en un servidor real), el
sitio redirige a HTTPS; para comprobar por HTTP en local pon `FORZAR_HTTPS=False` o añade
`-H "X-Forwarded-Proto: https"` a cada `curl`.

| Qué se comprueba | Comando | Resultado esperado |
|---|---|---|
| Salud (PostgreSQL y caché) | `curl -s localhost:8000/healthz/` | `{"estado": "ok", "bd": "ok", "cache": "ok"}` |
| Portada | `curl -s -o /dev/null -w "%{http_code}" localhost:8000/` | `200` |
| Estáticos con hash (WhiteNoise) | abrir la portada y revisar que el CSS carga | 200 en `/static/css/app.<hash>.css` |
| Comparación | `curl -s -o /dev/null -w "%{http_code}" localhost:8000/productos/1/` | `200` |
| API documentada | `curl -s -o /dev/null -w "%{http_code}" localhost:8000/api/docs/` | `200` |
| Escribir exige cuenta | `curl -s -o /dev/null -w "%{http_code}" -X POST localhost:8000/api/v1/precios/reportes/` | `403` |
| HTTPS obligatorio (con `FORZAR_HTTPS=True`) | `curl -s -o /dev/null -w "%{http_code}" localhost:8000/` | `301` |

## 5. Operación

| Tarea | Comando |
|---|---|
| Ver el estado | `$DC ps` |
| Ver los registros | `$DC logs -f web` |
| Actualizar a una versión nueva | `git pull && $DC up -d --build` (las migraciones corren solas) |
| Reiniciar la aplicación | `$DC restart web` |
| **Respaldo** de la base de datos | `$DC exec -T db pg_dump -U precios precios > respaldo.sql` |
| Restaurar un respaldo (en una base vacía) | `$DC exec -T db psql -U precios precios < respaldo.sql` |
| Detener **conservando** los datos | `$DC down` |
| Detener y **borrar los datos** | `$DC down -v` ⚠ elimina el volumen de PostgreSQL |

## 6. Variables de entorno

| Variable | Obligatoria | Para qué |
|---|---|---|
| `SECRET_KEY` | Sí | Clave de Django; sin ella el arranque falla a propósito |
| `POSTGRES_PASSWORD` | Sí | Contraseña de la base; el compose arma `DATABASE_URL` con ella |
| `ALLOWED_HOSTS` | Sí | Dominios permitidos; incluir siempre `localhost` (lo usa la comprobación de salud) |
| `CSRF_TRUSTED_ORIGINS` | En un dominio real | Orígenes `https://…` desde los que se envían formularios |
| `FORZAR_HTTPS` | No (`True`) | Redirección a HTTPS, cookies seguras y HSTS. **Solo se apaga para probar en local** |
| `WEB_PORT` | No (`8000`) | Puerto publicado en tu máquina |
| `WEB_CONCURRENCY` | No (`3`) | Procesos de gunicorn |
| `PORT` | No (`8000`) | Puerto interno; los PaaS lo inyectan |
| `CACHE_COMPARACION_TTL`, `LIMITE_REPORTES_HORA` | No | Parámetros de negocio (60 s y 30 por hora) |
| `DEMO_PASSWORD`, `DEMO_ADMIN_PASSWORD` | No | Claves de `cargar_demo` |

## 7. Llevarlo a un PaaS de contenedores (pendiente de proveedor)

La misma imagen sirve en Cloud Run, App Runner o Azure Container Apps. Lo que cambia:

1. **Imagen:** construirla (`docker build -t ahorrapues:prod .`) y subirla al registro del proveedor.
2. **Puerto:** el proveedor inyecta `PORT`; la imagen ya lo respeta.
3. **Base de datos y caché gestionadas:** en vez de los servicios `db` y `redis`, definir
   `DATABASE_URL` (PostgreSQL 16) y `REDIS_URL` con los datos que entregue el proveedor.
4. **Migraciones:** ejecutar `python manage.py migrate --noinput` como paso previo o como tarea
   (equivale al servicio `migrar`).
5. **Salud:** apuntar la comprobación del proveedor a `/healthz/`.
6. **TLS:** lo termina el proveedor; se conserva `FORZAR_HTTPS=True` y se configura
   `CSRF_TRUSTED_ORIGINS=https://<dominio>`.
7. **Secretos:** cargar `SECRET_KEY` y las claves en el gestor de secretos del proveedor, nunca en el
   repositorio.

Al elegir proveedor se registran en el ADR-017 el plan, la región y la URL, y se repite la prueba de
carga con k6 contra esa URL.

## 8. Límites conocidos

- **Sin despliegue en la nube** (falta decidir el proveedor, D-11).
- **El correo no se puede configurar por el entorno.** Hoy solo existen `EMAIL_BACKEND` y
  `DEFAULT_FROM_EMAIL`; el servidor SMTP (host, puerto, usuario, clave) no se lee del entorno. Por
  defecto el correo de recuperar contraseña (RF-02) se imprime en el registro del contenedor. Un
  despliegue real necesita agregar esa configuración.
- **Sin TLS en local:** la verificación local usa `FORZAR_HTTPS=False`; el modo seguro se comprueba
  con la cabecera `X-Forwarded-Proto` (sección 9).
- **Respaldos manuales** (sección 5); no hay copias automáticas ni retención.
- **Sin agregación de registros ni métricas** (la imagen escribe en la salida estándar).

## 9. Verificación realizada

- **Fecha:** 2026-11-16 · **Equipo:** macOS (Apple Silicon), Docker 29.6.2 y Compose v5.3.1
- **Código:** `main` (`ccc0c8c`) más los cambios de la rama `feat/despliegue-reproducible`
- **Quién la ejecutó:** la persona responsable de la rama, con apoyo de IA generativa; los comandos
  y sus resultados se pueden repetir con esta guía.

### 9.1 Construcción y arranque

| Comprobación | Resultado |
|---|---|
| `docker compose … up -d --build` (primera construcción) | Termina sin errores |
| Orden de arranque | `db` y `redis` saludables → `migrar` termina con éxito → `web` arranca y queda `healthy` |
| Migraciones | Todas aplicadas en una base vacía |
| Tamaño de la imagen | 351 MB |
| La imagen **no** contiene `.env` | 0 archivos (lo excluye `.dockerignore`) |
| La imagen **no** lleva dependencias de desarrollo | `pytest` no está instalado |
| Usuario del proceso | `app` (no administrador) |
| Estáticos con hash para WhiteNoise | `app.<hash>.css` generado en la construcción |
| Variante de desarrollo (`REQUIREMENTS=dev`) | Construye y conserva `pytest` |

### 9.2 Prueba de humo: `scripts/prueba_de_humo.sh` (modo local, `FORZAR_HTTPS=False`)

**23 comprobaciones, 0 fallas.** El detalle está en
[`evidencia-prueba-de-humo-2026-11-16.txt`](evidencia-prueba-de-humo-2026-11-16.txt). Cubre:

| Área | Qué se verificó |
|---|---|
| Lectura pública | Salud, portada, búsqueda sin tildes, comparación con el criterio de orden visible, filtro por municipio y barrio, directorio con enlace al mapa |
| API | `/api/docs/` y `/api/schema/` responden; la respuesta de comparación **no expone autor ni correo** (M-15) |
| Escritura (M-13) | Sin sesión: `403` en la API y redirección en la pantalla; un envío sin token CSRF se rechaza (`403`) |
| Flujo completo | Crear cuenta con autorización de datos, registrar un precio y verlo en «Mis aportes» |
| Moderación | Una cuenta común no entra; `moderador_demo` sí |

### 9.3 Modo seguro (`FORZAR_HTTPS=True`)

| Comprobación | Resultado |
|---|---|
| HTTP plano a `/` | `301` hacia `https://…` |
| Con la cabecera `X-Forwarded-Proto: https` (como un proxy TLS) | `200`; `/healthz/` en `ok` |
| Cabeceras de seguridad | `Strict-Transport-Security: max-age=31536000; includeSubDomains`, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff` |
| Cookie CSRF | Marcada `Secure` |

### 9.4 Resiliencia de `/healthz/` (M-21)

| Situación | Respuesta |
|---|---|
| Normal | `200` · `{"estado": "ok", "bd": "ok", "cache": "ok"}` |
| Redis detenido | `503` · `"cache": "error"`, `"bd": "ok"` |
| PostgreSQL detenido | `503` · `"bd": "error"`, `"cache": "ok"` |
| Servicio restablecido | Vuelve a `200` sin reiniciar la aplicación |

### 9.5 Lo que NO se verificó

- **Despliegue en la nube y su URL pública** (falta el proveedor, D-11).
- **Prueba de carga con k6** (EC-04) contra esta imagen: no se ejecutó.
- **Persistencia de los datos al reiniciar** el despliegue (`down` y `up`): no se probó.
- **Correo real** (SMTP) y **TLS real** de un navegador: solo se simuló con la cabecera del proxy.
- **El filtro por rango de precio** está en otra rama (`feat/filtro-rango-precio`); se agrega a la
  prueba de humo cuando se fusione.
