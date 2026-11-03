# ADR-0001: Adoptar un monolito modular multicapa en Django

- **Estado:** Propuesto (validar en revisión de diseño del Corte I)
- **Escenarios afectados:** EC-04, EC-05
- **Métricas:** M-08, M-17, M-18, M-19, M-20

## Contexto
Equipo de 3 personas, un semestre, alcance que crece entre cortes (módulo comercial), carga
dominada por lecturas (500 concurrentes en quincena) y criticidad media. La guía valora
"una arquitectura sencilla y bien justificada" sobre una que acumula patrones.

## Alternativas consideradas
| Alternativa | A favor | En contra |
|---|---|---|
| **A. Monolito modular** (apps Django por dominio, capas domain/services/selectors/interfaces) | Un despliegue, una BD transaccional, bajo costo operativo, pruebas simples, límites de módulo explícitos | Escala como unidad; la disciplina de límites depende del equipo |
| B. Microservicios (catálogo, precios, comparación, comercios) | Escalado y despliegue independientes | Costo operativo y de red desproporcionado para el equipo; consistencia distribuida; más superficie de fallo |
| C. Monolito en capas sin módulos | Lo más rápido de arrancar | El módulo comercial tocaría todo el código (riesgo alto para EC-05) |

## Decisión
Alternativa A. Cada app es un módulo de dominio; la comunicación entre módulos se hace solo a
través de `services` (escritura) y `selectors` (lectura). El módulo comercial se añade como app
nueva en el Corte III.

## Consecuencias
- (+) EC-05 medible: el cambio debería limitarse a `apps/comercios` + `comparacion.selectors`.
- (+) Escalado horizontal de réplicas stateless detrás de un balanceador con caché compartida (Redis).
- (−) Una falla grave afecta a todo el sistema (fiabilidad = media, aceptado).
- Revisar si la prueba de carga muestra que un solo módulo domina el consumo de recursos.
