# Módulo comercial (Corte III)

Portal voluntario para comercios (RF-C01 a RF-C07). Se construyó como un **cambio de alcance**
sobre el núcleo, para medir la modificabilidad (EC-05):

- **M-17** desviación del esfuerzo: `(real − estimado) / estimado` (objetivo ≤ ±20 %).
- **M-18** cambios estructurales en el núcleo: objetivo 0.

Decisiones: ADR-0012 (módulo nuevo), ADR-0013 y ADR-0018 (precio oficial frente al reportado),
ADR-0014 (promociones como estrategias), ADR-0015 (verificación por moderador) y
**ADR-0034 (evidencia en PDF)**.

## Estructura

```
comercios/
├── domain/promociones.py   # DescuentoPorcentual, PrecioEspecial, PagueXLleveY, vigencia (TDD)
├── domain/documentos.py    # validar_pdf: .pdf, cabecera %PDF-, 1 byte a 2 MB (TDD, ADR-0034)
├── models.py               # PerfilComercio, DocumentoComercio, PrecioOficial, Promocion,
│                           # SolicitudCorreccion
├── services.py             # crear_perfil, verificar_perfil, publicar_precio_oficial, …
├── selectors.py            # portal, bandeja de moderación y puerto hacia la comparación
├── api/                    # /api/v1/comercios/ (solo rol comercio)
├── views.py + templates/comercios/
└── semilla.py              # comercios de prueba (ADR-0023)
```

## Solicitud y verificación (RF-C01, RF-C02)

1. La persona elige su establecimiento del directorio y adjunta **dos PDF obligatorios**: el
   certificado de existencia y representación legal de la **Cámara de Comercio** y el **RUT** de la
   DIAN. Cada uno pesa máximo 2 MB (Vercel corta en 4,5 MB por petición).
2. `crear_perfil(*, usuario, establecimiento_id, nombre_contacto, camara_comercio, rut, telefono)`
   valida los dos archivos con el dominio y guarda el perfil y los documentos en **una sola
   transacción**: si un archivo falla, no se crea nada.
3. Moderación los abre desde `/comercios/verificacion/` («Ver Cámara de Comercio», «Ver RUT»). La
   descarga (`…/perfil/<id>/documento/<tipo>/`) responde 404 a cualquier cuenta que no sea de
   moderación. Usa `Content-Disposition: inline` con un nombre genérico, `nosniff` y
   `Cache-Control: private, no-store`.
4. `verificar_perfil` (aprobar o rechazar) **borra los bytes** en la misma transacción
   (`contenido = NULL`, `borrado_en = now`). Como constancia quedan el tipo, el tamaño, el SHA-256
   y las fechas.

`PerfilComercio.evidencia` (texto) ya no se pide. Solo la semilla lo usa, como marcador de los
perfiles de prueba.

## Privacidad (Ley 1581, M-15)

El usuario dueño del perfil, el teléfono, el código y los documentos **nunca** salen en la API ni
en las plantillas públicas. Tampoco van a los registros (logs). Los listados de moderación no traen
los bytes (`defer("contenido")`).

## Integración con la comparación

Se hace **solo** a través del puerto de `comparacion` (ADR-0012), que añade `es_promocion` como
etiqueta. Nunca se toca `comparacion.domain.ranking`.
