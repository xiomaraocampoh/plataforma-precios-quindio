# ADR-019: Panel de administración propio, roles con Groups de Django y Marca como entidad

- **Estado:** Propuesto
- **Fecha:** 2026-11-16
- **Autores:** Equipo; redactado con apoyo de IA
- **Escenarios de calidad afectados:** EC-05 (modificabilidad), seguridad (M-13, M-14, M-15)
- **Métricas que lo verifican:** M-14 (trazabilidad), M-18 (contratos de import-linter), M-02

## Contexto
El catálogo, el directorio y las cuentas solo se administraban desde `/admin/` de Django, pensado
para el superusuario: sin el estilo ni la accesibilidad de la plataforma, sin roles diferenciados y
con escrituras que no dejaban rastro de quién cambió qué. La marca era texto libre en `Producto`, lo
que producía variantes («Águila Roja», «aguila roja») y filtros duplicados.

## Alternativas consideradas
| Alternativa | A favor | En contra |
|---|---|---|
| Ampliar `/admin/` con permisos y plantillas | Poco código | Estilo y accesibilidad difíciles de igualar (WCAG 2.2 AA); escribe con el ORM sin pasar por servicios |
| Roles propios (tabla nueva) | Total control | Duplica lo que Django ya resuelve con Groups y Permissions |
| **Panel propio + Groups/Permissions + auditoría en servicios** | Reutiliza `has_perm`; respeta las capas; mismo estilo y HTMX | Más vistas y plantillas que mantener |

## Decisión
- App nueva `apps/administracion` con el panel en `/panel/`. `/admin/` se conserva para el superusuario.
- Roles: Administrador, Moderador, Editor de catálogo y Reportante, como Groups de Django. Sus
  permisos se definen en `apps/cuentas/domain/roles.py` (Python puro) y los crea una migración de
  datos. `Usuario.rol` es la fuente de verdad: una señal `post_save` deja al usuario en el grupo de su
  rol. El rol «comercio» no tiene grupo hasta el Corte III.
- Cada vista del panel verifica el permiso de Django en el servidor (403). Ocultar botones es solo
  comodidad.
- El panel escribe a través de los servicios del módulo dueño del dato y registra
  `RegistroAuditoria` (quién, qué, cuándo, cambios) en la misma transacción. La bitácora es de solo
  inserción y no guarda datos personales (Ley 1581).
- Nada con reportes u otros registros asociados se borra físicamente: se desactiva (`activa`/`activo`
  en marca, categoría, producto, presentación; `activo` en establecimiento; `is_active` en usuario).
  Lo inactivo deja de ofrecerse al público.
- `Marca` pasa a ser entidad, única por nombre normalizado, con una migración reversible en tres pasos
  (crear y FK temporal → migrar datos → quitar el texto).

## Consecuencias
- (+) Trazabilidad de cada cambio administrativo (M-14) y permisos verificables por prueba.
- (+) Filtros de marca sin variantes; la API pública conserva `marca` como texto.
- (−) Desactivar una marca o categoría oculta productos sin borrar reportes: la bitácora es la que
  explica por qué un producto dejó de aparecer.
- (−) Si alguien cambia los grupos de un usuario directamente en `/admin/`, el rol no se actualiza:
  el rol manda y la siguiente vez que se guarde el usuario se vuelve a sincronizar.
- Numeración: se usa 0019 a continuación del último ADR del repositorio, a la espera de la decisión D-1.
