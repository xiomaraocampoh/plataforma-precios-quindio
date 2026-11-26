# Despliegue alternativo en Vercel (serverless)

Cómo publicar AhorraPues en Vercel con su runtime de Python, **sin cambiar** el despliegue en Render
ni la imagen Docker ([`despliegue.md`](despliegue.md), ADR-017). La decisión, sus límites y la
comparación con Render están en el
[ADR-0031](../adr/0031-despliegue-alternativo-en-vercel-serverless.md).

> **Estado.** La configuración está lista y el CI reproduce el *build* de Vercel en cada PR (job
> `vercel`: instala solo `requirements.txt`, carga los ajustes de producción, corre `collectstatic`
> y arranca el WSGI). **Todavía no hay un despliegue real en Vercel**; la sección 8 lista lo que hay
> que comprobar la primera vez.

## 1. Qué se despliega

```
 navegador ──▶ CDN de Vercel ──▶ /static/…  (archivos de collectstatic, con hash)
                    │
                    └──▶ función Python (config/wsgi.py, Django) ──▶ PostgreSQL de Neon (pooler)
                                                                └─▶ Redis con TLS (Upstash)
 GitHub Actions ── cada 10 min ──▶ POST /interno/correos/procesar/  (cola de correo)
 Persona del equipo ── a mano ──▶ migrate contra DATABASE_URL_UNPOOLED
```

| Pieza | Dónde vive | Notas |
|---|---|---|
| Aplicación | Función de Vercel (`config/wsgi.py`) | Sin proceso permanente: arranca en frío tras un rato sin tráfico |
| Estáticos | CDN de Vercel | Vercel corre `collectstatic` en el *build* porque existe `STATIC_ROOT` |
| Base de datos | Neon (integración de Vercel) | La app usa `DATABASE_URL` (**con pooling**); las migraciones, `DATABASE_URL_UNPOOLED` |
| Caché | Upstash Redis (u otro con TLS) | `REDIS_URL=rediss://…` |
| Correo | API HTTPS de Brevo (`django-anymail`) | Igual que en Render (ADR-021) |
| Cola de correo | Workflow `procesar-correos` de GitHub Actions | **No** se usa el cron de Vercel |

## 2. Archivos del repositorio que usa Vercel

| Archivo | Para qué |
|---|---|
| `manage.py` | Vercel lo ejecuta para descubrir `DJANGO_SETTINGS_MODULE`. Su valor por defecto sigue siendo `config.settings.dev`; en Vercel la variable de entorno lo cambia a `prod` |
| `config/settings/base.py` → `WSGI_APPLICATION` | Punto de entrada: `config.wsgi.application` |
| `requirements.txt` y `[project].dependencies` de `pyproject.toml` | Dependencias de producción con versiones fijadas. Vercel no documenta cuál de los dos gana si están ambos, así que son **idénticos**. La fuente sigue siendo `requirements/prod.txt` |
| `.python-version` | Python 3.12, la misma versión del CI |
| `vercel.json` | Región `iad1` y `maxDuration` de 60 s para `config/wsgi.py` |
| `.vercelignore` | Evita subir `.env`, la base SQLite local, pruebas y documentación si se despliega con la CLI |
| `core/despliegue.py` | Ajustes que solo se activan con `VERCEL` (conexión, TLS, dominios) |

**Al cambiar una dependencia:** edita `requirements/base.txt` o `requirements/prod.txt` y luego la
misma línea, con la versión exacta (`==`), en `requirements.txt` y en `pyproject.toml`.
`tests/unit/test_requisitos_vercel.py` falla si los tres se desalinean.

## 3. Primera vez

### 3.1 Crear el proyecto

1. En [vercel.com](https://vercel.com) entra con la cuenta de GitHub de la **propietaria del
   repositorio** y elige *Add New → Project → Import* sobre `plataforma-precios-quindio`. Vercel
   pide permiso para leer el repositorio. **No** se agrega a Vercel como colaborador del repositorio
   (CLAUDE.md, regla 6).
2. *Framework Preset*: **Django** (lo detecta por `manage.py`). *Root Directory*: la raíz. No
   cambies *Build Command* ni *Output Directory*.
3. *Settings → Environment Variables*: comprueba que esté activa **Automatically expose System
   Environment Variables**. Sin ella no existe `VERCEL=1` y la app conservaría las conexiones
   persistentes de Render (sección 4).
4. *Settings → Functions → Function Region*: `iad1` (Washington D. C.), el mismo valor de
   `vercel.json`. La base de datos y Redis van en **la misma zona** (`us-east-1` en AWS).

### 3.2 Base de datos (Neon)

1. *Storage → Create Database → Neon (Postgres)*, región `us-east-1`, y conéctala al proyecto
   para *Production* (y *Preview* si se usará).
2. La integración crea, entre otras, dos variables:
   - `DATABASE_URL`: pasa por el **pooler** de Neon (PgBouncer, modo transacción; el host
     termina en `-pooler`). **La aplicación usa esta.**
   - `DATABASE_URL_UNPOOLED`: conexión directa. **Las migraciones usan esta** (sección 5): el
     pooler en modo transacción no sirve para las operaciones largas de `migrate`.
3. Comprueba que las dos URLs traigan `sslmode=require`. Aunque falte, en Vercel la app lo exige
   (`core/despliegue.py`).

### 3.3 Redis con TLS (Upstash)

1. *Storage → Upstash → Redis* (o una base creada en [upstash.com](https://upstash.com)), región
   `us-east-1`.
2. Copia la URL que empieza por **`rediss://`** (con dos «s»: TLS) a la variable `REDIS_URL`.
   La caché de producción (`RedisCache`) usa `SSLConnection` y verifica el certificado;
   `tests/unit/test_cache_redis_tls.py` lo comprueba.

### 3.4 Variables de entorno

En *Settings → Environment Variables*, para *Production* (y *Preview* si aplica). Vercel las usa
**también en el build**: `collectstatic` carga los ajustes de producción, así que `SECRET_KEY`,
`DATABASE_URL` y `REDIS_URL` deben existir allí o el build falla.

| Variable | Valor | Obligatoria |
|---|---|---|
| `DJANGO_SETTINGS_MODULE` | `config.settings.prod` | Sí |
| `SECRET_KEY` | `python -c "import secrets; print(secrets.token_urlsafe(50))"` | Sí |
| `DATABASE_URL`, `DATABASE_URL_UNPOOLED` | Las crea la integración de Neon | Sí |
| `REDIS_URL` | `rediss://default:<clave>@<host>.upstash.io:6379` | Sí |
| `DOMINIOS_VERCEL` | `<proyecto>.vercel.app` (varios separados por coma). Ver 3.5 | Sí |
| `SITIO_URL` | `https://<proyecto>.vercel.app` | Sí (enlaces de los correos) |
| `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` | Solo si hay dominio propio (`ahorrapues.co`, `https://ahorrapues.co`) | No |
| `BREVO_API_KEY` | Clave de API `xkeysib-…` | Para enviar correo |
| `DEFAULT_FROM_EMAIL`, `EMAIL_REPLY_TO` | Como en Render ([`despliegue.md`](despliegue.md), 6.2) | Para enviar correo |
| `CORREO_CRON_TOKEN` | `python -c "import secrets; print(secrets.token_urlsafe(32))"` | Para la cola de correo |
| `SEMBRAR_DATOS_PRUEBA`, `SEMBRAR_CUENTAS_PRUEBA`, `CUENTAS_PRUEBA_PASSWORD` | Como en Render; solo en una demostración | No |

No definas `VERCEL` a mano: la pone Vercel. `FORZAR_HTTPS` se queda en `True` (por defecto).

### 3.5 Dominios: sin comodines

`DOMINIOS_VERCEL` admite solo dominios **exactos** `<proyecto>.vercel.app`. Cada uno se agrega a
`ALLOWED_HOSTS` y, con `https://`, a `CSRF_TRUSTED_ORIGINS`. Un comodín (`*.vercel.app` o
`.vercel.app`) haría que la app aceptara peticiones dirigidas a **cualquier** proyecto alojado en
Vercel, así que la app **no arranca** si lo encuentra. Tampoco acepta esquema ni barra final.

Cada *preview* tiene su propio dominio (`<proyecto>-git-<rama>-<equipo>.vercel.app`). Si se quiere
probar uno, se agrega exacto a `DOMINIOS_VERCEL` del entorno *Preview*.

### 3.6 Primer despliegue

1. Aplica las migraciones **antes** del primer despliegue (sección 5); si no, la primera petición
   falla porque las tablas no existen.
2. *Deployments → Redeploy* (o un push a `main`). En el registro del build deben aparecer la
   instalación de las dependencias y `collectstatic` («… static files copied …, … post-processed»).
3. Haz las comprobaciones de la sección 7.

## 4. Qué cambia en la aplicación cuando existe `VERCEL`

Solo en `config/settings/prod.py` y solo con la variable `VERCEL` (Render y Docker no la tienen):

| Ajuste | Render / Docker | Vercel | Por qué |
|---|---|---|---|
| `CONN_MAX_AGE` | `60` (o el del entorno) | `0` siempre | Una función congelada no debe retener conexiones; el pooler las reutiliza |
| `OPTIONS.sslmode` | El de la URL | `require` como mínimo (se respeta `verify-ca`/`verify-full`) | La base está en Internet, no en una red privada |
| `DISABLE_SERVER_SIDE_CURSORS` | `False` | `True` | Requisito de Django con PgBouncer en modo transacción |
| `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` | Del entorno | Del entorno **más** `DOMINIOS_VERCEL` | Dominios exactos, sin comodines |

Lo demás es igual que en Render: HTTPS obligatorio, HSTS, cookies seguras, 2FA siempre activa, caché
en Redis y estáticos con `CompressedManifestStaticFilesStorage`. Vercel sirve los estáticos desde su
CDN; WhiteNoise queda en el middleware pero no recibe esas peticiones.

**Disco:** la app no escribe archivos al arrancar ni al atender peticiones (registros a la consola,
sesiones en la base, caché en Redis). La única escritura en disco es `collectstatic`, que ocurre en el
*build*. En la función solo se puede escribir en `/tmp`, y la app no lo necesita.

## 5. Migraciones (manuales)

Vercel no tiene un paso de «release» que corra `migrate` como `scripts/start.sh` en Render. Se
corren desde un equipo del equipo con las variables de producción y la conexión **directa**:

```bash
npm i -g vercel                       # CLI de Vercel (una sola vez)
vercel link                           # asocia la carpeta al proyecto
vercel env pull .env.vercel --environment=production   # .env.vercel nunca se versiona (.gitignore)
pip install -r requirements.txt       # los ajustes de producción necesitan whitenoise

set -a; . ./.env.vercel; set +a       # carga las variables en esta terminal
DATABASE_URL="$DATABASE_URL_UNPOOLED" DJANGO_SETTINGS_MODULE=config.settings.prod \
  python manage.py migrate --noinput
rm .env.vercel                        # no dejes los secretos de producción en disco
```

- Usa siempre `config.settings.prod`: con `dev`, `DEBUG=True` y `migrate` sembraría los datos de
  prueba (ADR-0023).
- Orden en cada versión con migraciones: **primero `migrate`, luego desplegar**. Una migración que
  borra o renombra columnas necesita dos versiones (agregar → desplegar → quitar).
- En una demostración, los precios sembrados envejecen y nadie los refresca al arrancar (no hay
  `start.sh`). Se renuevan con el mismo bloque y `python manage.py refrescar_precios_prueba`.

## 6. Cola de correo

El correo se envía al confirmar la transacción, dentro de la misma petición; los reintentos los
procesa `POST /interno/correos/procesar/`. Se sigue usando el workflow
[`procesar-correos`](../../.github/workflows/procesar-correos.yml) cada 10 minutos, **no** el cron de
Vercel: en el plan Hobby solo corre una vez al día con precisión de una hora.

En GitHub, *Settings → Secrets and variables → Actions*:

- `PROD_URL` = `https://<proyecto>.vercel.app` (sin `/` al final);
- `CORREO_CRON_TOKEN` = el mismo valor que en Vercel.

`PROD_URL` apunta a **un solo** despliegue: el que esté en producción (Render o Vercel). Si los dos
comparten la base de datos, cualquiera de los dos procesa la misma cola. Para probar: *Actions →
procesar-correos → Run workflow*. Una pasada envía como máximo 50 correos (`CORREOS_POR_PASADA`),
dentro del límite de 60 s de la función.

## 7. Comprobaciones

Con `URL=https://<proyecto>.vercel.app`:

| Qué se comprueba | Comando | Esperado |
|---|---|---|
| Salud (base y caché) | `curl -s $URL/healthz/` | `{"estado": "ok", "bd": "ok", "cache": "ok"}` |
| Portada | `curl -s -o /dev/null -w "%{http_code}" $URL/` | `200` |
| Estáticos desde el CDN | `curl -sI $URL/static/css/app.<hash>.css` (el nombre sale del HTML de la portada) | `200` |
| HTTP redirige a HTTPS | `curl -s -o /dev/null -w "%{http_code}" http://<proyecto>.vercel.app/` | Redirección `3xx` a `https://` |
| Escritura exige cuenta | `curl -s -o /dev/null -w "%{http_code}" -X POST $URL/api/v1/precios/reportes/` | `403` |
| Cola de correo | *Actions → procesar-correos → Run workflow* | Paso verde con conteos |

La prueba de humo completa sirve contra la URL de Vercel: `scripts/prueba_de_humo.sh` (ver
[`despliegue.md`](despliegue.md), 9.5, sobre los encabezados `Origin` y `Referer`).

## 8. Primera verificación real (pendiente)

Nada de esto se ha medido todavía. Al hacer el primer despliegue, registra en el ADR-0031:

- [ ] Que el build use `requirements.txt` o `pyproject.toml` sin errores (registro del build).
- [ ] Que `{% static %}` resuelva nombres con hash en la función (si falta el manifiesto, las
      páginas responden 500 con «Missing staticfiles manifest entry»).
- [ ] Tiempo de la primera respuesta tras 15 min sin tráfico (arranque en frío de la función **y**
      de Neon) y de las siguientes.
- [ ] `/healthz/` en verde y prueba de humo sin fallas.
- [ ] Prueba de carga con k6 (EC-04) contra la URL, revisando también los límites del plan.

## 9. Volver a Render o quitar Vercel

Render no depende de nada de esto: sin `VERCEL`, los ajustes son los de siempre. Para dejar de usar
Vercel basta con borrar el proyecto en Vercel y volver a poner en `PROD_URL` la URL de Render. Los
archivos `vercel.json`, `.vercelignore`, `.python-version` y `requirements.txt` no afectan a Docker
ni a Render.
