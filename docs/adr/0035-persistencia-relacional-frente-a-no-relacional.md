# ADR-0035: Mantener la persistencia relacional en PostgreSQL frente a una base no relacional

- **Estado:** Aceptado (aprobado por el equipo el 2026-11-27) · Amplía el [ADR-0003](0003-postgresql-como-base-de-datos-unica.md)
- **Fecha:** 2026-11-27 (documento final C3-AS2-E6, apéndice A)
- **Autores:** Equipo; redactado con apoyo de IA
- **Escenarios de calidad afectados:** EC-02, EC-03, EC-04, EC-05, EC-15
- **Métricas que lo verifican:** D-05, D-06, M-14

## Contexto
Los datos de la plataforma son relaciones entre entidades: un producto tiene presentaciones; un
precio une una presentación con un establecimiento, un autor y una fecha; un perfil de comercio se
vincula a un establecimiento, y una promoción, a un precio oficial. La comparación y la canasta
cruzan esas relaciones en cada consulta. La calidad del dato (ISO/IEC 25012) exige exactitud y
consistencia, y varias reglas deben cumplirse aunque el código falle, como un solo perfil activo por
establecimiento o un precio mayor que cero. Con el módulo comercial y la canasta del Corte 3 se
revisó si la decisión del ADR-0003 seguía siendo adecuada.

## Alternativas consideradas
| Alternativa | A favor | En contra |
|---|---|---|
| **A. Base relacional (PostgreSQL)** | Integridad referencial, restricciones de unicidad y de verificación, transacciones ACID, consultas con uniones | Esquema fijo que exige migraciones; escalado de escritura más costoso |
| B. Base no relacional de documentos (por ejemplo, MongoDB) | Esquema flexible; escalamiento horizontal | Traslada al código la integridad entre colecciones y las reglas de unicidad compuestas; complica las consultas que cruzan entidades |

## Decisión
Alternativa A. Se mantiene PostgreSQL como almacén principal, con las reglas críticas declaradas
como restricciones en la base de datos. Redis, un almacén clave-valor, se usa solo como caché y para
los contadores de límites de uso.

## Consecuencias
- (+) Las restricciones de la base rechazan datos inválidos aunque el código tenga un error.
- (+) Las transacciones evitan estados parciales, como un perfil de comercio sin su evidencia.
- (−) Cada cambio de esquema requiere una migración.
- (−) El escalamiento horizontal de escritura es más costoso, lo que no afecta al volumen regional
  esperado.

## Verificación
Pruebas de integración que comprueban las restricciones (unicidad del perfil activo, decisión con
moderador y fecha, posición en la canasta) y la prueba de carga de EC-04.
