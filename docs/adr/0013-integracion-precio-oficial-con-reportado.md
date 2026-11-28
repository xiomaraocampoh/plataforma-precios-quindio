# ADR-0013: Integrar el precio oficial con el reportado (mostrar el más reciente)

- **Estado:** Reemplazado por ADR-018
- **Fecha:** 2026-11-14 (borrador del Drive); archivado en el repositorio el 2026-11-16
- **Autores:** Equipo (borrador C2-AS2-E4 del Drive); adaptado al repositorio con apoyo de IA
- **Escenarios de calidad afectados:** EC-02, EC-03
- **Métricas que lo verifican:** D-03

> Se conserva porque una decisión que resulta inadecuada no se borra: se reemplaza con un ADR nuevo
> que explica el porqué (ver [ADR-018](0018-precio-oficial-verificado-como-principal.md)).

## Contexto
Un comercio puede publicar un precio distinto al que reportan los usuarios, por desactualización o
por interés propio (pregunta de diseño 1 de la guía).

## Alternativas consideradas
| Alternativa | A favor | En contra |
|---|---|---|
| Siempre prevalece el oficial | Simple; da control al comercio | Un comercio puede publicar un precio irreal sin contraste |
| Siempre prevalece el reportado | Refleja lo observado | Desincentiva a los comercios a participar |
| Prevalece el más reciente, con contraste visible | Equilibra fuentes; el consumidor ve la discrepancia | Más reglas que probar |

## Decisión (reemplazada)
Para cada establecimiento se muestra el precio vigente más reciente entre el oficial y el reportado,
con su fuente. Si hay al menos 2 reportes de usuarios en los últimos 7 días que difieren más de 10 %
del oficial, el resultado muestra «Usuarios reportan $X», la confianza baja a media y el comercio
recibe un aviso para corregir.

## Consecuencias
- (+) Transparencia y credibilidad (D-03).
- (−) Un comercio honesto puede ver advertencias por reportes atrasados; se mitigaba con la confirmación con un toque (RF-C07).
- **Por qué se reemplazó:** la encuesta a consumidores (n = 10, noviembre de 2026) mostró que el 60 % prefiere el precio de la tienda y nadie prefiere solo el de los usuarios; además, mostrar el más reciente puede ocultar el precio oficial ante un reporte erróneo o malintencionado.
