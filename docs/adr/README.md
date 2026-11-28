# Registro de decisiones arquitectónicas (ADR)

Cada ADR sigue la plantilla [`0000-plantilla.md`](0000-plantilla.md) (formato de Nygard, 2011).
Estados revisados y aprobados por el equipo el 2026-11-27.

| ADR | Decisión | Estado |
|---|---|---|
| [0001](0001-monolito-modular-multicapa.md) | Monolito modular multicapa | Aceptado |
| [0002](0002-django-drf-y-htmx.md) | Django y DRF con renderizado en el servidor e HTMX | Aceptado |
| [0003](0003-postgresql-como-base-de-datos-unica.md) | PostgreSQL como base de datos única | Aceptado · ampliado por 0035 |
| [0004](0004-cqrs-ligero-y-cache.md) | CQRS ligero con caché *cache-aside* | Aceptado |
| [0005](0005-vigencia-de-precios.md) | Ventanas de vigencia de precios | Aceptado (validado con usuarios) |
| [0006](0006-confiabilidad-del-dato-colaborativo.md) | Confiabilidad del dato colaborativo en capas | Aceptado |
| [0007](0007-orden-neutral-y-promociones-como-etiqueta.md) | Orden neutral único; promociones como etiqueta | Aceptado |
| [0008](0008-privacidad-del-reportante.md) | Privacidad del reportante por diseño | Aceptado |
| [0009](0009-registro-tolerante-a-conectividad-limitada.md) | Registro tolerante a la conectividad limitada | Aceptado |
| [0010](0010-integracion-con-sipsa.md) | Integración con SIPSA mediante puerto y adaptador (carga manual desde CSV) | Aceptado |
| [0011](0011-catalogo-canonico-con-presentaciones.md) | Catálogo canónico con presentaciones y precio por unidad | Aceptado |
| [0012](0012-modulo-comercial-como-modulo-nuevo.md) | Módulo comercial como módulo nuevo | Aceptado |
| [0013](0013-integracion-precio-oficial-con-reportado.md) | Precio oficial frente a reportado (el más reciente) | Reemplazado por 0018 |
| [0014](0014-promociones-como-estrategias.md) | Promociones como estrategias, fuera del orden | Aceptado |
| [0015](0015-verificacion-de-comercios-por-moderador.md) | Verificación de comercios por moderador | Aceptado · modificado por 0034 |
| [0016](0016-alertas-de-bajada-de-precio-diferidas.md) | Alertas de bajada de precio diferidas | Aceptado |
| [0017](0017-despliegue-en-paas-de-contenedores.md) | Despliegue en PaaS de contenedores (Render) | Aceptado |
| [0018](0018-precio-oficial-verificado-como-principal.md) | Precio oficial verificado como principal | Aceptado |
| [0019](0019-panel-de-administracion-y-roles.md) | Panel propio, roles con Groups y Marca como entidad | Aceptado |
| [0020](0020-codigo-de-barras-leido-en-el-navegador.md) | Código de barras leído en el navegador, sin enviar la imagen | Aceptado |
| [0021](0021-correo-transaccional-brevo-outbox-y-2fa.md) | Correo transaccional con Brevo, outbox y verificación en dos pasos | Aceptado |
| [0022](0022-reconocimiento-de-productos-por-foto-con-ia.md) | Reconocimiento de productos por foto con IA (opcional) | Aceptado |
| [0023](0023-semilla-de-prueba-en-migraciones.md) | Datos y cuentas de prueba sembrados desde las migraciones | Aceptado |
| [0024](0024-fotos-de-producto-guardadas-en-la-base-de-datos.md) | Fotos de producto en la base de datos, subidas desde el panel | Aceptado |
| [0025](0025-api-rest-con-openapi-frente-a-graphql.md) | API REST con OpenAPI frente a GraphQL | Aceptado |
| [0026](0026-escaneo-en-vivo-e-interpretacion-de-etiquetas.md) | Escaneo en vivo e interpretación de etiquetas de precio (amplía el 0022) | Aceptado (apagado por defecto) |
| [0027](0027-calculo-de-la-canasta-en-cada-consulta.md) | Canasta: calcular en cada consulta sobre la caché de la comparación | Aceptado |
| [0028](0028-productos-sin-precio-y-criterios-de-orden-de-la-canasta.md) | Canasta: productos sin precio vigente y criterios de orden declarados | Aceptado |
| [0029](0029-cantidades-y-promociones-en-la-canasta.md) | Canasta: cantidades, presentaciones y promociones «pague X lleve Y» | Aceptado (promociones en la canasta pendientes) |
| [0030](0030-asistente-de-compras-con-tool-use.md) | Asistente de compras con IA: la IA interpreta, el dominio calcula | Aceptado |
| [0031](0031-despliegue-alternativo-en-vercel-serverless.md) | Despliegue alternativo en Vercel (serverless), sin cambiar Render | Aceptado |
| [0032](0032-departamentos-del-catalogo.md) | Departamentos amplios sobre las categorías | Aceptado |
| 0033 | Pipeline de entrega continua (B2) | En la rama `docs/b2-analisis-adr-ec12`, pendiente de fusionar |
| [0034](0034-evidencia-de-comercios-en-pdf.md) | Evidencia de los comercios en PDF guardada en la base y borrada al decidir | Aceptado |
| [0035](0035-persistencia-relacional-frente-a-no-relacional.md) | Persistencia relacional en PostgreSQL frente a una base no relacional (amplía el 0003) | Aceptado |

Los ADR de la ampliación del Anexo 1 (desde el 0027) usan la **plantilla 8.1 del Anexo**, que agrega
a la de Nygard los campos *Escenarios relacionados* y *Verificación*.

## Numeración (decisión D-1, resuelta el 2026-11-27)

Se adopta la numeración del registro de decisiones entregado (C1-AS2-E2 y consolidados):

- **0001 a 0011:** núcleo del Corte 1. Los archivos que se habían creado como `0002` (CQRS) y
  `0003` (vigencia) se renombraron a `0004` y `0005`, y se crearon los que faltaban (0002, 0003 y
  0006 a 0011).
- **0012 a 0018:** módulo comercial (análisis de impacto del Corte 2).
- **0019 a 0035:** decisiones tomadas durante la construcción y la ampliación del Corte 3. El 0020
  (código de barras) se registró en el consolidado del Corte 2; el 0025 (REST frente a GraphQL)
  figuraba como ADR-024 en el informe C2-AS2-E3 y cambió de número porque el 0024 corresponde a las
  fotos de producto; el 0033 es el pipeline de B2.

Las referencias en el código y en los documentos se actualizaron a esta numeración. En los textos se
aceptan las formas `ADR-004` y `ADR-0004` para el mismo registro.
