# Escenario de calidad de la ampliación B2 (entrega continua)

- **Fecha:** 2026-11-27 · **Estado:** Propuesto
- **Formato:** plantilla 8.2 del Anexo 1, en las seis partes de Bass, Clements y Kazman (2021).
- **Relación:** [análisis de impacto](../arquitectura/analisis-impacto-b2-entrega-continua.md) y
  [ADR-0033](../adr/0033-pipeline-de-entrega-continua.md).

> **Pendiente de contraste.** El texto de EC-12 del Anexo 1 no está en el repositorio. Este refinamiento
> parte de lo que el equipo resumió (PR roto bloqueado; cambio válido en staging en ≤ 15 minutos) y
> debe compararse con el Anexo antes de aprobarse.

---

## EC-12. Un cambio llega a staging rápido y uno roto nunca llega (Anexo 1, refinado)

**Atributos:** mantenibilidad (capacidad de prueba y de modificación), fiabilidad (recuperabilidad) y
seguridad (integridad), ISO/IEC 25010:2023.

| Parte | Descripción | EC-12 refinado |
|---|---|---|
| **Fuente del estímulo** | Quién o qué genera el estímulo | Una persona del equipo que abre un pull request o fusiona un cambio en `main` |
| **Estímulo** | Evento o condición que llega al sistema | **(a)** un PR con una prueba rota, un error de lint, una violación de límites de arquitectura o una vulnerabilidad alta de la imagen; **(b)** un cambio válido fusionado en `main`; **(c)** una versión en producción que debe retirarse |
| **Artefacto** | Parte del sistema afectada | El pipeline (`ci.yml`, `entrega.yml`, `revertir.yml`), la protección de `main`, el servicio de staging y el de producción en Render |
| **Entorno** | Condiciones en que ocurre | Operación normal del equipo; staging con datos de prueba; plan gratuito de Render (el servicio puede estar dormido) |
| **Respuesta** | Lo que hace el sistema | **(a)** el check falla y la fusión queda bloqueada; **(b)** pasa las puertas, la imagen se escanea, se despliega a staging, `/healthz/` informa el SHA enviado y la prueba de humo con k6 queda en verde; la promoción a producción espera una aprobación manual; **(c)** se vuelve al SHA anterior con el procedimiento documentado |
| **Medida de la respuesta** | Valor verificable | **(a)** 100 % de los PR con una puerta fallida bloqueados y 0 llegan a staging; **(b)** ≤ 15 min desde la fusión hasta staging con la prueba de humo en verde, en las tres corridas de evidencia; **(c)** ≤ 10 min para volver a la versión anterior *(umbral propuesto)* |

**Cómo se mide.**

| Medida | Métrica | Instrumento | Umbral |
|---|---|---|---|
| Tiempo de entrega a staging | M-26 | Historial de GitHub Actions: de la fusión a que termine `entrega.yml` | ≤ 15 min |
| Cambios con una puerta fallida que llegan a staging | M-27 | PR con una prueba rota y revisión de los despliegues a staging | 0 |
| Tiempo de reversión | M-28 | Ensayo cronometrado de `revertir.yml` o de *Rollbacks* | ≤ 10 min |
| Puertas de calidad | M-19, M-20 | Quality gate de SonarQube en el pipeline | Gate aprobado |

**Evidencia por guardar** en `docs/calidad/evidencias/<fecha>/b2/`: captura del PR bloqueado con el check
que falla; ejecuciones de `entrega.yml` con sus tiempos (tres corridas); captura de `/healthz/` con la
versión; captura de la aprobación manual; ensayo de reversión con tiempos.

## Métricas nuevas (propuestas) para `trazabilidad-metricas.md`

| ID | Subcaracterística | Medida | Umbral | Instrumento |
|---|---|---|---|---|
| M-26 | Capacidad de modificación (entrega) | Minutos desde la fusión en `main` hasta staging con la prueba de humo en verde | ≤ 15 min | Historial de GitHub Actions (`entrega.yml`) |
| M-27 | Capacidad de prueba (puertas) | Cambios con una puerta fallida que llegan a staging | 0 | PR de evidencia y checks requeridos |
| M-28 | Recuperabilidad | Minutos para volver a la versión anterior en producción | ≤ 10 min (propuesto) | Ensayo cronometrado documentado |

**Por qué 15 y 10 minutos.** Los 15 minutos vienen del Anexo. Los 10 de la reversión son una propuesta del
equipo: debe ser menor que el tiempo de entrega porque no reconstruye nada, solo vuelve a desplegar un
SHA ya probado. Si el ensayo muestra que no se cumple, se documenta el valor real y se ajusta el umbral.

---

## Referencias (APA 7)

Bass, L., Clements, P., & Kazman, R. (2021). *Software architecture in practice* (4.ª ed.).
Addison-Wesley Professional.

International Organization for Standardization. (2023). *ISO/IEC 25010:2023, Systems and software
engineering — Systems and software Quality Requirements and Evaluation (SQuaRE) — Product quality
model*.
