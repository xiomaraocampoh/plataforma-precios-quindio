# ADR-0034: Evidencia de los comercios en PDF guardada en la base de datos

- **Estado:** Aceptado (aprobado por el equipo el 2026-11-27)
- **Fecha:** 2026-11-27
- **Autores:** Equipo; redactado con apoyo de IA
- **Modifica:** [ADR-0015](0015-verificacion-de-comercios-por-moderador.md) (la evidencia de la verificación)
- **Escenarios de calidad afectados:** Seguridad (autenticidad, confidencialidad), EC-05
- **Métricas que lo verifican:** M-13, M-14, M-15, M-16

## Contexto
El ADR-0015 pedía una «evidencia simple» en texto libre (NIT, RUT o una descripción de la foto de la
fachada). En la práctica, ese texto no le permitía al moderador comprobar nada: un NIT escrito se
puede copiar de cualquier factura. La entrevista a la tienda consultada no fue concluyente sobre
cómo verificar a un comercio, así que se adopta lo que un comercio formal en Colombia siempre tiene:

- el **certificado de existencia y representación legal** de la Cámara de Comercio, y
- el **RUT** expedido por la DIAN.

Los dos se descargan en PDF. Son documentos con datos personales del representante (Ley 1581 de 2012),
así que hay que decidir dónde se guardan y cuánto tiempo.

Restricciones del despliegue: Render (disco efímero, ADR-0017) y Vercel (funciones sin disco
persistente y un límite de **4,5 MB por petición**, ADR-0031).

## Alternativas consideradas
| Alternativa | A favor | En contra |
|---|---|---|
| a) Almacenamiento externo (S3, Vercel Blob) | Escala; no crece la base | Costo, secretos y configuración nuevos; otro proveedor más que tiene datos personales |
| b) Disco local (`MEDIA_ROOT`) | Simple | Vercel no conserva archivos y Render gratuito los pierde al reiniciar |
| **c) `BinaryField` en PostgreSQL, como el ADR-0024** | Sin servicios nuevos; respaldo con la base; misma transacción que el perfil | La base crece mientras la solicitud está pendiente |

## Decisión
Se elige **c)**.

- Tabla nueva `comercios.DocumentoComercio` (FK al perfil con `CASCADE`, porque es una composición):
  `tipo` (`camara_comercio` o `rut`), `contenido` (`BinaryField`, `null=True`), `tamano`, `sha256`,
  `subido_en` y `borrado_en`. Hay un documento por tipo y perfil (`UniqueConstraint`), y la base
  impide guardar más de 2 MB (`CheckConstraint`). También exige que «sin bytes» vaya siempre con
  `borrado_en`.
- **Validación** en `comercios/domain/documentos.py` (Python puro, TDD): solo extensión `.pdf`
  (sin importar mayúsculas), cabecera `%PDF-` y tamaño entre 1 byte y **2 MB**. El formulario usa la
  misma regla para mostrar el error en el campo, y el servicio la repite antes de guardar.
- **Límite de 2 MB por archivo:** dos archivos y el resto del formulario quedan por debajo de los
  4,5 MB por petición de Vercel.
- `crear_perfil` guarda el perfil y los dos documentos en **una sola transacción**: si un archivo no
  sirve, no se crea nada.
- `PerfilComercio.evidencia` pasa a ser opcional. Ya no se pide en el formulario; la semilla la sigue
  usando como marcador de los perfiles de prueba (ADR-0023).

### Privacidad (Ley 1581)
- **Solo un moderador** los ve, en `/comercios/verificacion/perfil/<id>/documento/<tipo>/`. Para
  cualquier otra cuenta la respuesta es 404, y una persona sin sesión va al ingreso. La respuesta usa
  `application/pdf`, `inline` con un nombre genérico (`camara-comercio-<id>.pdf`), `nosniff` y
  `Cache-Control: private, no-store`. El nombre original del archivo no se guarda.
- **Minimización:** al verificar o rechazar el perfil, en la misma transacción de la decisión, se
  **borran los bytes** (`contenido = NULL`, `borrado_en = now`). Como constancia de lo que se revisó
  quedan el tipo, el tamaño, el SHA-256 y las fechas.
- Los documentos nunca aparecen en la API, en las plantillas públicas ni en los registros (logs).
  Los listados no traen los bytes (`defer("contenido")`).

## Consecuencias
- (+) El moderador verifica con documentos oficiales, no con texto libre.
- (+) Sin proveedores ni secretos nuevos; los datos no salen de la base del proyecto.
- (−) La base crece hasta 4 MB por solicitud pendiente, pero **solo de forma temporal**: los bytes
  se borran al decidir.
- (−) Una tienda informal sin RUT ni Cámara de Comercio no puede crear el perfil. Se acepta porque
  un perfil verificado publica «precios oficiales».
- **Revisar si:** las solicitudes pendientes acumulan más de ≈ 200 MB, o si se necesita conservar los
  documentos por obligación legal. Entonces habría que pasar a almacenamiento de objetos cifrado,
  manteniendo la misma interfaz de servicio.
