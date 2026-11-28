# ADR-0015: Verificar los comercios mediante un moderador

- **Estado:** Aceptado (aprobado por el equipo el 2026-11-27) · **Modificado por [ADR-0034](0034-evidencia-de-comercios-en-pdf.md)**
  (la evidencia pasa de texto libre a dos PDF: Cámara de Comercio y RUT)
- **Fecha:** 2026-11-16
- **Autores:** Equipo (borrador C2-AS2-E4 del Drive, 14-nov-2026); adaptado al repositorio con apoyo de IA
- **Escenarios de calidad afectados:** Seguridad (autenticidad), EC-03
- **Métricas que lo verifican:** M-14, M-16

## Contexto
Un perfil de comercio puede publicar precios oficiales y promociones, así que debe poder demostrarse
que quien lo gestiona representa al negocio. Si no se verifica, cualquiera podría suplantar a un
comercio. La mayoría de tiendas de barrio no tiene dominio propio de correo.

## Alternativas consideradas
| Alternativa | A favor | En contra |
|---|---|---|
| Verificación por un moderador con evidencia simple | Evita la suplantación; viable para tiendas sin dominio | Trabajo manual del moderador |
| Verificación automática por correo del dominio | Sin trabajo manual | La mayoría de tiendas de barrio no tiene dominio propio |

## Decisión
El perfil queda **pendiente** hasta que un moderador confirma, con una evidencia simple (foto de la
fachada con un código entregado por la plataforma, o RUT/NIT), que el usuario representa al
comercio. Solo un perfil verificado publica.

> **Cambio (2026-11-27): evidencia en PDF.** El texto libre no permitía verificar. Ahora la evidencia
> son dos PDF obligatorios: el certificado de Cámara de Comercio y el RUT. Se guardan en la base y se
> borran al decidir. Ver [ADR-0034](0034-evidencia-de-comercios-en-pdf.md).

**Detalle de diseño (hallazgo de la lectura del código).** La verificación se registra en el propio
módulo (`PerfilComercio.verificado_por` y `fecha`), no en `moderacion.DecisionModeracion`, porque el
campo `accion` de ese modelo tiene opciones cerradas y ampliarlas exigiría una migración en el
núcleo. La asignación del rol «comercio» debe hacerse mediante un servicio de `cuentas`, que hoy no
existe (solo hay `asegurar_moderador`).

## Consecuencias
- (+) Evita la suplantación de un comercio.
- (−) Trabajo manual del moderador, aceptable con la escala esperada.
- Evidencia pendiente: en la entrevista a la única tienda consultada, la pregunta sobre cómo verificar a un comercio no tuvo respuesta concluyente. Conviene validar el mecanismo con otra tienda antes de pasar este ADR a Aceptado.
