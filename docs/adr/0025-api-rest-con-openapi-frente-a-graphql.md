# ADR-0025: Exponer una API REST versionada con OpenAPI en lugar de GraphQL

- **Estado:** Aceptado (aprobado por el equipo el 2026-11-27)
- **Fecha:** 2026-11-16 (informe de despliegue C2-AS2-E3, donde figuraba como ADR-024); archivado en el repositorio el 2026-11-27
- **Autores:** Equipo; redactado con apoyo de IA
- **Escenarios de calidad afectados:** EC-04 (desempeño), EC-15 (confidencialidad), EC-05 (modificabilidad)
- **Métricas que lo verifican:** M-08, M-13, M-15

## Contexto
La guía exige una API documentada y el equipo debía decidir su estilo. Las consultas de la
plataforma tienen formas fijas (buscar, comparar un producto, consultar el directorio, armar una
canasta) y deben controlar con precisión qué campos se exponen, porque el autor de un reporte nunca
puede salir en una respuesta pública. La comparación ya tiene una caché por producto
([ADR-0004](0004-cqrs-ligero-y-cache.md)).

## Alternativas consideradas
| Alternativa | A favor | En contra |
|---|---|---|
| **A. REST versionada (`/api/v1/`) con DRF y OpenAPI (drf-spectacular)** | Cada ruta tiene un costo y un límite de uso conocidos; la caché por URL encaja con la caché por producto; serializers con lista blanca; documentación generada | Un cliente que quiera otra forma de datos necesita otra ruta o un parámetro |
| B. GraphQL | El cliente pide exactamente los campos que quiere; una sola ruta | Consultas de costo variable, difíciles de limitar; caché por URL inútil; más superficie para exponer campos por error; otra dependencia y otra forma de autorización |

## Decisión
Alternativa A. La API se expone como REST versionada en `/api/v1/`, con el esquema OpenAPI en
`/api/schema/` y la documentación en `/api/docs/`. Los cambios a `/v1` son solo aditivos (como el
arreglo `promociones` del [ADR-0014](0014-promociones-como-estrategias.md)); un cambio incompatible
abriría `/v2`.

## Consecuencias
- (+) Límites de uso por alcance y costo predecible por ruta (EC-04, M-16).
- (+) Lista blanca de campos verificable con pruebas de API (M-15).
- (+) El contrato se publica y se verifica en el CI (paso de esquema).
- (−) Clientes nuevos con necesidades distintas pueden requerir rutas nuevas.

## Evidencia en el código
- `config/urls.py` con `SpectacularAPIView` y `SpectacularSwaggerView`.
- Rutas `api/` en `catalogo`, `establecimientos`, `precios`, `comparacion`, `moderacion` y
  `comercios`, con serializers que declaran sus campos.
