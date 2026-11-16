# Núcleo completo: requisitos, rutas y cómo probarlos

Rama `feat/nucleo-completo`. Incluye todos los requisitos del núcleo **sin el módulo comercial**
(`apps/comercios` no se toca; contrato `comercios-no-adelantado` de import-linter) y sin despliegue.

## Preparar los datos

```bash
docker compose up -d db redis
python manage.py migrate
python manage.py cargar_demo --con-vencidos
python manage.py importar_sipsa ruta/al/archivo.csv      # opcional, RF-07
```

Contraseñas de `cargar_demo` (nunca están en el código ni en este documento):

| Variable | Usuarios |
|---|---|
| `DEMO_ADMIN_PASSWORD` | `admin` (superusuario) y `moderador_demo` (rol moderador, `is_staff`) |
| `DEMO_PASSWORD` | `demo`, `demo_ana`, `demo_luis`, `demo_sofia` |

Si la variable no existe al crear los usuarios, se genera una contraseña aleatoria y se muestra
**una sola vez** en la consola. Para fijarla después: `python manage.py changepassword admin`.

## Requisitos implementados

| Requisito | Qué hace | Ruta o comando | Pruebas |
|---|---|---|---|
| Punto 0 · acceso y vencidos | `admin` y `moderador_demo`; `--con-vencidos` carga precios de 8 días (reportado), 4 días (perecedero) y 31 días (oficial), más otros de 6, 2 y 29 días | `cargar_demo [--con-vencidos]` | `test_cargar_demo.py` |
| RF-02 Recuperar contraseña | Correo con enlace de un solo uso que vence en 1 hora; en desarrollo el correo se ve en la consola | `/cuentas/contrasena/recuperar/` | `test_recuperar_contrasena.py` |
| RF-03 Mis datos | Ver y actualizar usuario y correo; suprimir la cuenta con contraseña y confirmación; los aportes se conservan anonimizados | `/cuentas/mis-datos/`, `/cuentas/mis-datos/suprimir/` | `test_mis_datos.py` |
| RF-04 Búsqueda | Por nombre sin tildes ni mayúsculas (`nombre_normalizado`, conserva la ñ) y por código de barras exacto de 8 a 14 dígitos | buscador de inicio, `/productos/?q=` | `test_busqueda.py` |
| RF-04 Escanear código de barras | Botón en el buscador: lee el código con la cámara o una foto **en el navegador** (la imagen no se envía) y abre `/escanear/?codigo=`. Valida longitud y dígito de control GTIN; si el producto existe va a su comparación, si no ofrece solicitarlo con el código ya escrito | `/escanear/`, `/catalogo/solicitar/?codigo_barras=` | `test_codigo_barras.py`, `test_escanear.py` |
| RF-04 Buscar por foto (IA, opcional) | En el mismo diálogo, «Fotografiar el producto»: la IA extrae nombre y marca, el sistema busca en el catálogo y la persona confirma. Sin cuenta, con topes de uso; ADR-019 | `/buscar-por-foto/` (POST) | `test_reconocimiento.py`, `test_reconocedor_claude.py`, `test_buscar_por_foto.py` |
| RF-06 + PU-05 Duplicados | `normalizar_nombre` y `son_posibles_duplicados` (umbral 0,85, TDD); la solicitud muestra productos similares mientras se escribe y queda pendiente | `/catalogo/solicitar/` | `test_duplicados.py`, `test_solicitud_catalogo.py` |
| RF-07 SIPSA | Importa el CSV del DANE con fuente «sipsa»; la comparación lo muestra como referencia mayorista fuera del orden; `ClienteSipsa` en línea, pendiente | `importar_sipsa archivo.csv` | `test_sipsa.py`, `test_importar_sipsa.py` |
| RF-08 Directorio | Establecimientos aprobados con filtros por municipio, barrio y tipo | `/establecimientos/` | `test_establecimientos.py` |
| RF-09 Mapa | Enlace a OpenStreetMap con las coordenadas, sin API key | «Ver en el mapa» en el directorio | `test_mapas.py`, `test_establecimientos.py` |
| RF-10 Sugerir establecimiento | Queda pendiente e inactivo (restricción en la base de datos) y no se usa en la comparación ni en el registro hasta aprobarse | `/establecimientos/sugerir/` | `test_establecimientos.py` |
| RF-14 Sigue igual | Confirmación idempotente por usuario, reporte y día; renueva la vigencia y suma confianza; máximo 30 por hora | botón en cada resultado | `test_renovacion.py`, `test_sigue_igual.py` |
| RF-19 Filtros | Municipio, barrio y **rango de precio total** en la comparación (solo reducen; el orden no cambia); marca y categoría en el listado de productos; el criterio de orden siempre visible. El rango acepta el formato colombiano (`2.500`, `$2.500`, `2500,50`) y, si es inválido, avisa y no filtra | `/productos/<id>/?municipio=&barrio=&precio_min=&precio_max=`, `/productos/?marca=&categoria=` | `test_filtros.py`, `test_filtro_precio.py`, `test_interpretar_monto.py`, `test_filtros_comparacion.py`, `test_filtro_precio_comparacion.py`, `test_busqueda.py` |
| RF-20 Denunciar | Motivo y detalle; una sola denuncia por usuario y reporte | «Denunciar» en cada resultado | `test_moderacion.py` |
| RF-21 Bandeja | Solo rol moderador o staff: reportes en revisión, denuncias, solicitudes y establecimientos; aprobar o rechazar; cada decisión guarda moderador y fecha | `/moderacion/` y acciones en `/admin/` | `test_moderacion.py`, `test_admin.py` |
| RF-22 Suspender | Suspende la cuenta (no a staff ni a uno mismo); los reportes quedan auditables | bandeja y `/admin/` | `test_moderacion.py` |
| Mis aportes (C) | Reportes propios con su estado | `/precios/mis-aportes/` | `test_mis_aportes.py` |
| API v1 + OpenAPI | Ver la tabla siguiente | `/api/docs/` | `test_api_*.py`, `test_establecimientos.py`, `test_moderacion.py` |
| Admin (13) | `Presentacion` con filtros por unidad, categoría y marca, y búsqueda por código de barras; `Producto` con filtros por marca y categoría | `/admin/` | `test_admin.py` |

## API v1

Todas aparecen en `/api/docs/`. Ninguna respuesta incluye al autor de un reporte ni a quien sugirió
un establecimiento (EC-07). Los serializers usan lista blanca de campos.

| Método y ruta | Permiso | Throttle |
|---|---|---|
| `GET /api/v1/catalogo/productos/?q=` | público | anon/user |
| `GET /api/v1/catalogo/productos/{id}/` | público | anon/user |
| `GET /api/v1/establecimientos/?municipio=&barrio=` | público | anon/user |
| `POST /api/v1/establecimientos/sugerencias/` | autenticado | `sugerencias` 10/h |
| `POST /api/v1/moderacion/denuncias/` | autenticado | `denuncias` 20/h (409 si se repite) |
| `GET /api/v1/moderacion/reportes-en-revision/` | moderador o staff | anon/user |
| `GET, PATCH /api/v1/moderacion/reportes-en-revision/{id}/` | moderador o staff | `moderacion` 600/h |

## Cómo probar a mano

1. **RF-04:** en inicio, escribe `CAFE`; aparece «Café molido». En `/productos/` escribe un código de
   barras completo. Con `cargar_demo`, el botón de código de barras del buscador acepta
   `2000000000015` (Arroz blanco 500 g): escríbelo en el diálogo o sube una foto de ese código.
2. **RF-14:** ingresa como `demo_ana` y abre la comparación de «Frijol cargamanto». Pulsa
   «Sigue igual»; la segunda vez dice «Ya lo confirmaste hoy».
3. **Vigencia (EC-02):** en «Frijol cargamanto» solo aparecen Supermercado del Parque (oficial, 29
   días) y Tienda El Vecino (6 días). Los de 8 y 31 días no se muestran.
4. **RF-19:** en la comparación del arroz, filtra por barrio «Centro». El orden no cambia, solo
   desaparecen filas. Después escribe «Precio desde» `2.500` y «Precio hasta» `4.800`: el mensaje
   dice «Mostrando N resultados entre $2500 y $4800» y el orden por precio por unidad se conserva.
   Escribe `abc` en un campo de precio: aparece un aviso y no se filtra. El rango se aplica al
   **precio total** del empaque (el que se ve en grande), no al precio por unidad.
5. **RF-20 y RF-21:** denuncia un precio con `demo_ana`. Ingresa como `moderador_demo`, abre
   Mi cuenta → Moderación y acepta la denuncia: el precio sale de la comparación y la decisión
   aparece en «Últimas decisiones».
6. **RF-10:** sugiere un establecimiento; no aparece en el directorio ni en «¿Dónde estás?» hasta
   que moderación lo apruebe.
7. **RF-02:** registra un correo en Mis datos, cierra sesión y pide recuperar la contraseña. El
   enlace sale en la consola de `runserver`; úsalo dos veces y la segunda dirá «El enlace ya no es
   válido».
8. **RF-07:** importa el ejemplo de `docs/integraciones/sipsa.md` y abre la comparación del arroz:
   aparece la tarjeta «Referencia mayorista SIPSA (DANE)».

## Decisiones de diseño

- **`ranking.py` sin cambios.** El selector arma `FilaComparacion` (resultado, reporte, ubicación,
  última confirmación) y ordena solo los `ResultadoComparacion` con `ordenar_neutral`. Los filtros
  se aplican después y solo reducen. La API de comparación devuelve exactamente lo mismo que antes.
- **Moderación orquesta servicios.** `moderacion.services` llama a los servicios de cada módulo y
  nunca escribe en su ORM. La bandeja y las acciones de `/admin/` dejan el mismo registro en
  `DecisionModeracion`, que es de solo lectura.
- **Supresión (Ley 1581).** Se anonimiza el usuario en vez de borrarlo, porque el autor es una FK
  `PROTECT`. Los precios siguen en la comparación sin identidad.
- **SIPSA no es precio de tienda.** Por eso se muestra como referencia mayorista, en una tarjeta
  aparte.
- **Marca y categoría en el listado de productos, no en la comparación.** La comparación es de un
  solo producto, con una marca y una categoría, así que ahí ese filtro no tendría efecto.
