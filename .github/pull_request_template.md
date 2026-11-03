## Qué cambia y por qué

<!-- Enlaza la historia/issue y, si aplica, el ADR -->

## Checklist ISO/IEC 25010 (marcar lo que aplica)

- [ ] **Adecuación funcional** — reglas de negocio nuevas con prueba escrita primero (TDD); orden de la comparación sin cambios o justificado (M-05, M-06)
- [ ] **Capacidad de interacción** — el flujo sigue completándose en ≤ 15 s; etiquetas, foco y contraste WCAG 2.2 AA (M-01, M-03)
- [ ] **Seguridad** — endpoints de escritura con autenticación; ninguna respuesta pública expone autor/ubicación; throttling en escrituras (M-13, M-15, M-16)
- [ ] **Eficiencia de desempeño** — sin N+1 (`select_related`/`prefetch_related`); caché invalidada si cambia el dato leído (M-08)
- [ ] **Mantenibilidad** — sin imports entre apps fuera de `services`/`selectors`; vistas sin lógica de negocio; cobertura del dominio ≥ 90 % (M-18, M-19)
- [ ] Migraciones incluidas y reversibles
- [ ] Documentación/ADR actualizados si cambia una decisión estructural

## Uso de IA generativa (declaración exigida por la guía)

- [ ] No se usó IA en este PR
- [ ] Se usó IA para: <!-- describir --> y el autor puede explicar y defender el código
