# ADR-019: Reconocimiento de productos por foto con la API de Anthropic

- **Estado:** Propuesto (requiere la aprobación del equipo y de la propietaria antes de activarse)
- **Fecha:** 2026-11-16
- **Autores:** Equipo; borrador generado con apoyo de IA y pendiente de revisión humana
- **Escenarios de calidad afectados:** EC-01 (rapidez de uso), EC-06 (neutralidad); riesgos de privacidad (Ley 1581) y costo
- **Métricas que lo verifican:** M-01, M-06, M-15

## Contexto
La persona quiere buscar un producto fotografiándolo. El escáner de código de barras (RF-04) es
gratuito y no sale del celular, pero no sirve si el empaque no tiene el código a la vista o el producto
no tiene código. La foto de la portada puede identificarse con un modelo de visión.

## Decisión
Se ofrece, **de forma opcional y apagada por defecto**, la búsqueda por foto con la API de Anthropic:

1. **Solo extrae.** El modelo recibe la foto y devuelve nombre, marca, tamaño y código visible. No tiene
   herramientas ni acceso a datos. Esa respuesta es un dato no confiable: el dominio
   (`integraciones/domain/reconocimiento.py`) la limpia, acota y valida, y se usa **solo como texto de
   búsqueda** sobre el catálogo. No decide precios ni orden (EC-06 intacto).
2. **La persona confirma.** Se muestran candidatos del catálogo y debe elegir; la lectura puede fallar.
3. **Puerto y adaptador** (`ReconocedorDeProductos` / `ReconocedorClaude`), como SIPSA: timeout, un
   reintento y toda falla se traduce a «no disponible»; la plataforma sigue por nombre o código.
4. **Privacidad.** La foto se reduce a 1024 px y se recodifica en el navegador (se pierden los metadatos
   EXIF, incluida la ubicación), se envía a Anthropic solo para esta consulta y **no se guarda** en
   nuestros servidores. La pantalla lo avisa antes de usarla.
5. **Costo y abuso.** **No exige cuenta** (decisión del equipo, 2026-11-16: menos fricción, EC-01).
   Para acotar el gasto: tope por persona y hora (`RECONOCIMIENTOS_POR_HORA`=20 con cuenta,
   `RECONOCIMIENTOS_ANONIMO_POR_HORA`=10 sin cuenta, identificada por una huella de la dirección IP,
   nunca la IP en claro) y un tope diario total (`RECONOCIMIENTOS_POR_DIA_TOTAL`=300). Limitación
   conocida: detrás de un proxy sin configurar, los visitantes comparten la misma dirección y por tanto
   el mismo tope. Sin `ANTHROPIC_API_KEY` la función no aparece. La clave vive solo en variables de
   entorno.
6. **Modelo configurable** (`RECONOCIMIENTO_MODELO`, por defecto `claude-opus-5-5`; una opción más
   económica es `claude-haiku-5-5`, a decidir con una prueba de precisión y costo).

## Consecuencias
- (+) Cubre productos sin código a la vista y mejora la inclusión de quien no sabe escribir el nombre.
- (−) **Dato personal potencial a un tercero:** hay que actualizar la política de tratamiento de datos
  y obtener la aprobación del equipo antes de activarla en producción.
- (−) Costo por consulta, dependencia externa y posibles errores del modelo (mitigados con la
  confirmación manual).
- (−) No hay medición de precisión todavía: **no se debe afirmar un porcentaje de acierto** hasta
  probarla con fotos reales de productos de Armenia.

## Alternativas descartadas
- Reconocedor local (modelo propio): más privado, pero exige entrenar y operar un modelo.
- Guardar las fotos para mejorar el catálogo: aumenta el riesgo de datos personales; fuera de alcance.
