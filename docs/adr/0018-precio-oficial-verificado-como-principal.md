# ADR-0018: Mostrar el precio oficial verificado como principal, con advertencia de discrepancia

- **Estado:** Aceptado (aprobado por el equipo el 2026-11-27); reemplaza al [ADR-0013](0013-integracion-precio-oficial-con-reportado.md)
- **Fecha:** 2026-11-16
- **Autores:** Equipo (borrador C2-AS2-E4 del Drive, 14-nov-2026); adaptado al repositorio con apoyo de IA
- **Escenarios de calidad afectados:** EC-02, EC-03, EC-06
- **Métricas que lo verifican:** D-01, D-03, M-06

## Contexto
Pregunta de diseño 1 de la guía: cuando un comercio publica un precio oficial y los usuarios reportan
uno distinto, ¿cuál se muestra y cómo se comunica? En la encuesta a consumidores (n = 10, noviembre de
2026) el 60 % prefiere ver el precio publicado por la tienda, el 30 % el más reciente con aviso de la
diferencia y nadie prefiere solo el de los usuarios. El tendero entrevistado señaló como principal
temor que se publiquen precios que no son reales. El ADR-013 mostraba el más reciente, lo que puede
ocultar el precio oficial ante un reporte reciente erróneo o malintencionado.

## Alternativas consideradas
| Alternativa | A favor | En contra |
|---|---|---|
| Mantener el ADR-013 (el más reciente) | Ya diseñado | Contradice la preferencia mayoritaria y expone al comercio a reportes recientes erróneos |
| Mostrar siempre el oficial, sin contraste | Simple; da control al comercio | Un comercio podría publicar precios irreales (EC-03) |
| Oficial verificado como principal, con advertencia de discrepancia | Responde a la preferencia de los consumidores y al temor del comercio; la discrepancia sigue visible | Más reglas que probar |

## Decisión
Si el comercio está verificado ([ADR-015](0015-verificacion-de-comercios-por-moderador.md)) y su
precio oficial está vigente (confirmado en los últimos 30 días), se muestra el precio oficial como
principal, con la etiqueta «Oficial». Si hay al menos 2 reportes de usuarios en los últimos 7 días que
difieren más de 10 % del oficial, el resultado agrega «Usuarios reportan $X», la confianza baja a
media y el comercio recibe un aviso para confirmar o corregir. Si el precio oficial venció o el
comercio no está verificado, se muestra el reporte vigente más reciente, como en el núcleo. **El
criterio de orden no cambia** (ADR-007).

**Dónde se implementa.** El cambio se limita al selector de comparación (dentro de `FilaComparacion`),
sin tocar `comparacion/domain/ranking.py`.

## Consecuencias
- (+) Responde a la preferencia de los consumidores y al temor del comercio.
- (+) La discrepancia sigue visible (D-03).
- (−) Un comercio verificado que no actualiza a tiempo puede mostrar un precio desfasado hasta por 30 días; se mitiga con la advertencia y la confirmación con un toque (RF-C07).
- **Punto abierto de neutralidad.** El precio oficial entra en la comparación como *el precio que se compara* para ese establecimiento, de modo que quien se verifica influye en qué precio se ordena. No es una promoción y no altera `_clave_neutral`, pero sí conviene vigilarlo con la equidad entre comercios (guía §12.3). Debe revisarse al ratificar este ADR.
- **Evidencia que haría revisar la decisión:** una muestra mayor (30 consumidores y dos tiendas de barrio sin sistema de ventas) que contradiga el 60 %; o desfases frecuentes del precio oficial.
