# Módulo comercial — se construye en el Corte III

**No implementar antes de tiempo.** La guía introduce este módulo como un *cambio de alcance*
sobre un núcleo ya construido para medir la modificabilidad (EC-05):

- **M-17** desviación del esfuerzo: `(real − estimado) / estimado` (objetivo ≤ ±20 %).
- **M-18** cambios estructurales en el núcleo: objetivo 0.

Antes de escribir código aquí:

1. Hacer el **análisis de impacto** (Corte II, entregable 4 de Arquitectura) y registrar la
   estimación en el tablero.
2. Crear el ADR que decida cómo se integran precio oficial vs. reportado (pregunta de diseño 1)
   y cómo las promociones no alteran la neutralidad (pregunta 7).
3. Activar la app en `config/settings/base.py → LOCAL_APPS`.

Estructura prevista (misma plantilla de capas que el resto de apps):

```
comercios/
├── domain/promociones.py   # DescuentoPorcentual, PrecioEspecial, PagueXLleveY, vigencia (TDD)
├── models.py               # PerfilComercio, PrecioOficial, Promocion
├── services.py             # publicar_precio_oficial, publicar_promocion, verificar_comercio
├── selectors.py
├── api/                    # endpoints del portal de comercios (BFF si el equipo lo decide)
├── views.py + templates/comercios/
```

La integración con la comparación se hace **solo** a través de `comparacion.selectors`
(que añade `es_promocion` como etiqueta) — nunca tocando `comparacion.domain.ranking`.
