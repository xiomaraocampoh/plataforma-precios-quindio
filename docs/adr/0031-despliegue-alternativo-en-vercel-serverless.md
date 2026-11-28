# ADR-0031: Despliegue alternativo en Vercel (serverless)

- **Estado:** Aceptado (aprobado por el equipo el 2026-11-27); configuración verificada en el CI
- **Fecha:** 2026-11-25
- **Autores:** Equipo; borrador con apoyo de IA, pendiente de revisión humana
- **Escenarios relacionados:** EC-04 (desempeño), EC-02 (vigencia), M-21 (disponibilidad); ADR-017, ADR-021, ADR-0004
- **Métricas que lo verifican:** M-08, M-09, M-10, M-21
- **Plantilla:** 8.1 del Anexo 1 (adaptada de Nygard, 2011)

## Contexto
La aplicación se publica en Render con la imagen Docker del ADR-017. Render gratuito duerme el
servicio tras un rato sin tráfico, bloquea SMTP (ADR-021) y no tiene procesos en segundo plano. El
equipo quiere **una segunda opción** de despliegue, Vercel, que ofrece Django sin configuración
(runtime de Python), CDN para los estáticos y despliegues de vista previa por rama.

Fuerzas:

- **No romper lo que funciona.** Render, Docker y el CI deben seguir iguales.
- **Modelo serverless.** Vercel ejecuta funciones efímeras: no hay proceso permanente, ni
  `scripts/start.sh`, ni disco escribible fuera de `/tmp`.
- **Conexiones a PostgreSQL.** Cada instancia de la función abre las suyas; sin un pooler se agota
  el cupo de conexiones del servidor.
- **Seguridad.** Los dominios `*.vercel.app` son de todos los clientes de Vercel; un comodín en
  `ALLOWED_HOSTS` no protege nada.
- **Precedente del ADR-017.** Ese ADR descartó el serverless puro porque Django y HTMX encajan mal
  con funciones efímeras. Este ADR no lo contradice: Vercel queda como **alternativa**, no como
  reemplazo, hasta medir el arranque en frío.

Hechos de la plataforma consultados el 2026-11-25 en la documentación de Vercel (se deben confirmar
al desplegar): Vercel detecta Django por `manage.py`, toma `WSGI_APPLICATION`, corre `collectstatic`
si existe `STATIC_ROOT` y sirve el resultado desde su CDN; admite
`CompressedManifestStaticFilesStorage`; lee `requirements.txt`, `pyproject.toml` o `Pipfile`, sin
documentar cuál gana si hay varios; Python 3.12 por defecto; en el plan Hobby las funciones duran
hasta 300 s, se elige una sola región y el cron corre como máximo una vez al día.

## Alternativas consideradas
1. **Solo Render (estado actual).** Sin cambios ni riesgo, pero una sola opción y el servicio
   duerme.
2. **Vercel como reemplazo de Render.** Pierde el proceso permanente y la paridad con la imagen
   Docker que se verificó (despliegue.md, sección 9). Prematuro sin mediciones.
3. **Vercel como alternativa activada por la variable `VERCEL`** (elegida). El mismo código y los
   mismos ajustes de producción; solo cambian la conexión a la base, el TLS y los dominios.
4. **Imagen Docker en Vercel.** Vercel no ejecuta contenedores propios para este caso; habría que
   mantener otra ruta de construcción.

## Decisión
Se agrega Vercel como **despliegue alternativo**, con estas reglas:

- **Dependencias:** `requirements.txt` (versiones fijadas, sin `-r`) y `[project].dependencies`
  de `pyproject.toml` declaran lo mismo que `requirements/prod.txt`, que sigue siendo la fuente.
  `tests/unit/test_requisitos_vercel.py` falla si se desalinean. `.python-version` fija 3.12.
- **Configuración:** `DJANGO_SETTINGS_MODULE=config.settings.prod` como variable de Vercel;
  `manage.py` conserva `dev` por defecto. Con `VERCEL` definida, `core/despliegue.py` fija
  `CONN_MAX_AGE=0`, `sslmode` mínimo `require` y `DISABLE_SERVER_SIDE_CURSORS=True`.
- **Base de datos:** Neon. La app usa `DATABASE_URL` (pooler, modo transacción); las migraciones,
  `DATABASE_URL_UNPOOLED`, a mano y antes de cada despliegue que las necesite.
- **Caché:** Redis con TLS (`rediss://`, p. ej. Upstash). La caché del ADR-0004 no cambia.
- **Dominios:** `DOMINIOS_VERCEL` con dominios exactos `<proyecto>.vercel.app`; un comodín impide
  arrancar.
- **Región:** `iad1` (Washington D. C.), con la base y Redis en `us-east-1`. Se descartó `gru1`
  (São Paulo): desde Colombia la ruta suele pasar por Miami, así que la latencia a la costa este de
  EE. UU. es en general menor que a São Paulo. Lo que más pesa es que la función quede junto a la
  base, porque una página hace varias consultas. **No se ha medido**: se valida con k6.
- **Correo:** API HTTPS de Brevo (ADR-021, sin cambios). La cola se procesa con el workflow
  `procesar-correos` de GitHub Actions apuntando a la URL de Vercel (`PROD_URL`), no con el cron de
  Vercel.
- **Duración:** `maxDuration` de 60 s para `config/wsgi.py`. Es el triple del tiempo máximo de la
  llamada más lenta de la app (reconocimiento por foto, 20 s) y corta peticiones colgadas antes de
  que consuman cupo del plan.

### Comparación con Render (ADR-017)

| Aspecto | Render (contenedor, ADR-017) | Vercel (serverless, este ADR) |
|---|---|---|
| **Arranque en frío** | El plan gratuito duerme el servicio tras ~15 min sin tráfico; despertar tarda cerca de **1 min** (se observó con el workflow de correo) | Cada instancia nueva importa Django: se espera del orden de **segundos**, más el despertar de Neon si estaba suspendido. **Sin medir** |
| **Proceso permanente** | Sí: gunicorn con varios workers; conexiones persistentes (`CONN_MAX_AGE=60`) | No: instancias efímeras, `CONN_MAX_AGE=0` y pooler obligatorio. Nada corre entre peticiones |
| **Migraciones** | Automáticas al arrancar (`scripts/start.sh`) | **Manuales** desde un equipo, con `DATABASE_URL_UNPOOLED`, antes de desplegar |
| **Datos de demostración** | `start.sh` refresca los precios de prueba al iniciar | Se refrescan a mano (`refrescar_precios_prueba`) |
| **Tareas programadas** | Sin cron gratuito; se usa GitHub Actions | Cron de Hobby limitado a **una vez al día**; se sigue usando GitHub Actions |
| **Estáticos** | WhiteNoise dentro de la app | CDN de Vercel; WhiteNoise no recibe esas peticiones |
| **Disco** | Escribible (efímero) | Solo `/tmp`; la app no escribe en disco |
| **Paridad con local** | Misma imagen Docker verificada | Otra ruta de construcción; el CI la reproduce (job `vercel`) |
| **Vistas previas** | No | Una URL por rama (hay que declarar cada dominio en `DOMINIOS_VERCEL`) |
| **Costos** | Plan gratuito: un servicio que duerme; base y Redis aparte | Hobby gratuito para uso **no comercial**, con cupos mensuales de ejecución; Neon y Upstash tienen planes gratuitos con cupos y Neon suspende la base sin tráfico. Los cupos se confirman en las páginas de precios antes de la prueba de carga: 500 usuarios concurrentes (EC-04) pueden agotarlos |

## Consecuencias
- (+) Una segunda forma de publicar sin tocar Render; cambiar de proveedor es mover `PROD_URL`.
- (+) Estáticos en CDN y vistas previas por rama.
- (+) El CI comprueba en cada PR que el build de Vercel funciona con solo `requirements.txt`.
- (−) Tres listas de dependencias que mantener (la prueba impide que se separen).
- (−) Migraciones manuales: si se despliega sin migrar, la app falla hasta que se migre.
- (−) Más piezas externas: Vercel, Neon y Upstash, cada una con su cupo gratuito.
- (−) El arranque en frío puede afectar el registro rápido (EC-01, ≤ 15 s) y el p95 (EC-04).

## Verificación
- **Hecho (CI y local, 2026-11-25):** en un entorno limpio con solo `requirements.txt`, los ajustes
  de producción con `VERCEL=1` cargan; `check --deploy` sin errores; `collectstatic` genera
  `staticfiles.json` y los archivos comprimidos; `config.wsgi` arranca y `{% static %}` devuelve el
  nombre con hash. Pruebas unitarias de la conexión serverless, el TLS de la base y de Redis, los
  dominios y el backend de correo.
- **Planificado:** primer despliegue real con `/healthz/` en verde y la prueba de humo
  ([`despliegue-vercel.md`](../operacion/despliegue-vercel.md), sección 8); tiempo de arranque en
  frío; prueba de carga con k6 contra la URL de Vercel (p95 < 2 s, error < 1 %). Con esos datos, el
  equipo decide si Vercel sigue como alternativa, reemplaza a Render o se retira.
