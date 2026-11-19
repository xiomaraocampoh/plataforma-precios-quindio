# Registro de decisiones arquitectónicas (ADR)

Cada ADR sigue la plantilla [`0000-plantilla.md`](0000-plantilla.md) (formato de Nygard, 2011).

| ADR | Decisión | Estado |
|---|---|---|
| [0001](0001-monolito-modular-multicapa.md) | Monolito modular multicapa | Propuesto |
| [0002](0002-cqrs-ligero-y-cache.md) | CQRS ligero con caché *cache-aside* | Propuesto |
| [0003](0003-vigencia-de-precios.md) | Ventanas de vigencia de precios | Propuesto (el Drive lo marca Aceptado) |
| [0012](0012-modulo-comercial-como-modulo-nuevo.md) | Módulo comercial como módulo nuevo | Propuesto (DP-1 pendiente) |
| [0013](0013-integracion-precio-oficial-con-reportado.md) | Precio oficial frente a reportado (el más reciente) | Reemplazado por 0018 |
| [0014](0014-promociones-como-estrategias.md) | Promociones como estrategias, fuera del orden | Propuesto (D-3 pendiente) |
| [0015](0015-verificacion-de-comercios-por-moderador.md) | Verificación de comercios por moderador | Propuesto |
| [0016](0016-alertas-de-bajada-de-precio-diferidas.md) | Alertas de bajada de precio diferidas | Propuesto |
| [0017](0017-despliegue-en-paas-de-contenedores.md) | Despliegue en PaaS de contenedores | Propuesto (proveedor pendiente) |
| [0018](0018-precio-oficial-verificado-como-principal.md) | Precio oficial verificado como principal | Propuesto |
| [0019](0019-panel-de-administracion-y-roles.md) | Panel propio, roles con Groups y Marca como entidad | Propuesto |
| [0021](0021-correo-transaccional-brevo-outbox-y-2fa.md) | Correo transaccional con Brevo (SMTP), outbox y verificación en dos pasos | Propuesto |
| [0022](0022-reconocimiento-de-productos-por-foto-con-ia.md) | Reconocimiento de productos por foto con IA (opcional) | Propuesto (requiere aprobación) |
| [0023](0023-semilla-de-prueba-en-migraciones.md) | Datos y cuentas de prueba sembrados desde las migraciones | Propuesto |
| [0024](0024-fotos-de-producto-guardadas-en-la-base-de-datos.md) | Fotos de producto en la base de datos, subidas desde el panel | Propuesto |

## Sobre la numeración (decisión D-1 pendiente)

Los ADR 0012 a 0019 usan la numeración de los documentos corregidos del 14 de noviembre de 2026
(la más reciente). Los archivos 0002 y 0003 conservan la numeración con la que se crearon en el
repositorio y **no coinciden** con la del documento de ADR del Drive (donde la decisión de CQRS es el
ADR-004 y la de vigencia es el ADR-005). Los ADR 0004 a 0011 del Drive (PostgreSQL, confianza, orden
neutral, privacidad, idempotencia, SIPSA, catálogo) **aún no tienen archivo en el repositorio**.
Renumerar y crear los faltantes es la decisión D-1 del equipo; hasta entonces no se renombra nada.
