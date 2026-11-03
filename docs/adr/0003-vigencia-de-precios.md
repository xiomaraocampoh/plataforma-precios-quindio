# ADR-0003: Ventanas de vigencia de precios

- **Estado:** Propuesto
- **Preguntas de diseño:** 2, 8
- **Escenarios / métricas:** EC-02, D-02, D-03

## Decisión
- Precio reportado: vigente 7 días.
- Producto de categoría perecedera: 3 días.
- Precio oficial de comercio: hasta que el comercio lo cambie o 30 días sin confirmar.

Valores parametrizados en `settings.PRECIOS` y probados en `tests/unit/precios/test_vigencia.py`.

## Consecuencias
Un precio vencido no se muestra como vigente (D-02 = 100 %). Validar los valores con las
entrevistas a tenderos del Corte I y ajustar este ADR si la evidencia lo indica.
