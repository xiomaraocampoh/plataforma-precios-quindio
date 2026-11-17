# ADR-0023: Sembrar los datos y las cuentas de prueba desde las migraciones

- **Estado:** Propuesto
- **Fecha:** 2026-11-16
- **Autores:** Equipo; redactado con apoyo de IA
- **Escenarios de calidad afectados:** EC-02 (vigencia), EC-03 (anomalías), seguridad (M-13, M-15)
- **Métricas que lo verifican:** M-18 (contratos de import-linter), D-05

## Contexto
Para probar la aplicación, cada integrante tenía que correr, después de `migrate`, dos comandos
(`cargar_datos_prueba` y `crear_cuentas_prueba`), y el arranque del PaaS corría además
`cargar_demo`. Si alguien olvidaba un paso, terminaba con una base vacía o con cuentas que no
podían iniciar sesión. Además, los precios se fechan al cargarlos: con los días quedan todos
vencidos.

Una migración solo puede usar los modelos históricos (`apps.get_model`): no puede llamar a los
servicios, que importan los modelos actuales.

## Alternativas consideradas
| Alternativa | A favor | En contra |
|---|---|---|
| Seguir con comandos aparte | Sin código nuevo | El paso olvidado es el problema |
| Fixtures JSON (`loaddata`) | Estándar de Django | Fechas fijas (envejecen); sin reglas de negocio; claves primarias rígidas |
| Llamar a `cargar_datos_prueba` desde una migración | Una sola lógica | Usaría modelos actuales: se rompe en cuanto cambie un modelo |
| **Módulos `semilla.py` que reciben `apps`** | Misma lógica para la migración y los comandos; funciona con modelos históricos | Las reglas de los servicios se replican con el dominio puro |

## Decisión
- Cuatro migraciones de datos con `RunPython` y reversa: `catalogo.0008`, `establecimientos.0004`,
  `cuentas.0006` y `precios.0004`.
- Su lógica vive en `apps/<app>/semilla.py`. Cada módulo recibe el registro de modelos: el
  histórico en la migración, `django.apps.apps` en los comandos. Nunca importa modelos ni
  servicios (lo exige el contrato «semilla-sin-modelos» de `.importlinter`). Las reglas de los
  servicios se replican con las funciones puras del dominio: `normalizar_nombre` y
  `son_posibles_duplicados` (D-05), `es_anomalo` (EC-03) y las reglas de «Sigue igual» y denuncias.
- `core/semilla.py` reúne lo común: leer los CSV, el resumen y cuándo se puede sembrar.
- **Cuándo siembra `migrate`:**
  - Datos (catálogo, directorio y precios): con `DEBUG=True` o `SEMBRAR_DATOS_PRUEBA=True`.
  - Cuentas de prueba: con `DEBUG=True` o `SEMBRAR_CUENTAS_PRUEBA=True`. En producción no hay
    cuentas con rol conocido y contraseña compartida salvo que alguien lo pida.
  - Los precios necesitan a las cuentas como autores: sin ellas no se cargan y `migrate` lo avisa.
- La contraseña sale solo de `CUENTAS_PRUEBA_PASSWORD`. Sin ella, o si no cumple los validadores,
  las cuentas quedan con contraseña inutilizable y `migrate` explica cómo activarlas.
- Las fechas son relativas («hace N días»). `refrescar_precios_prueba` las vuelve a calcular desde
  hoy, y `scripts/start.sh` lo corre al iniciar cuando la siembra está activa.
- La siembra es idempotente: busca por clave natural y por `id_cliente`, que es el mismo UUID que ya
  usaba `cargar_datos_prueba`. La reversa borra por esas claves y conserva lo que otro dato usa.

## Consecuencias
- **Positivas:** `git pull` + `migrate` basta para tener datos y cuentas. Los dos caminos (migración
  y comandos) usan el mismo código, y hay pruebas para cada uno. La base de pruebas nace vacía:
  `config/settings/test.py` apaga la siembra.
- **Negativas:**
  - Las reglas de los servicios están en dos sitios: el servicio y la semilla. Ambos usan la misma
    función de dominio, así que solo se duplica cómo se llama.
  - Una migración ya aplicada no se vuelve a ejecutar: si los CSV cambian, hay que correr
    `cargar_datos_prueba`.
  - La reversa borra por clave natural. Si alguien creó a mano una marca con el mismo nombre, y
    ningún producto la usa, la reversa también la borra. Por eso la reversa solo actúa cuando la
    siembra está activa.
- **Riesgo:** como la migración usa el código *actual* de `semilla.py`, un cambio futuro de modelo
  puede romperla en una base nueva. Mitigación: la prueba
  `tests/integration/test_semilla_migraciones.py` migra una base vacía hacia adelante y en reversa
  en cada CI. Si se rompe, se corrige `semilla.py` o se crea una migración nueva; nunca se edita la
  migración fusionada.
- **Revisar si:** los datos de prueba dejan de caber en un CSV, o si producción necesita datos de
  referencia reales (eso no es una semilla de prueba).
