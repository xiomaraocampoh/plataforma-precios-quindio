# Análisis de impacto de la ampliación B2: entrega continua

**Anexo 1 de la guía · Corte 3 · Arquitectura de Software II y Modelos de Calidad**

- **Fecha:** 2026-11-27 · **Estado:** Propuesto (estimaciones pendientes de aprobación del equipo)
- **Base analizada:** `main` según el archivo comprimido del repositorio del 2026-11-27 (núcleo, canasta y despliegue en Render)
- **Opción del bloque B:** B2, entrega continua. **Escenario de referencia:** EC-12 (Anexo 1).
- **Plantilla:** 8.3 del Anexo 1 (registro de análisis de impacto). Las columnas *Tipo de cambio* y
  *Esfuerzo estimado* se llenan **antes de construir**; la de *Esfuerzo real*, al cierre.
- **Declaración de uso de IA:** este documento se redactó con apoyo de un asistente de IA generativa
  (Claude, Anthropic) a partir de la lectura del repositorio y de los requisitos de B2 que el equipo
  resumió. Las estimaciones son una propuesta: el equipo debe revisarlas, aprobarlas y poder
  defender cada cifra. Las horas reales las registra cada integrante.

**Marcas de estado.** *Verificado* = comprobado en el repositorio en esta fecha. *Propuesto* = decisión o
estimación pendiente de aprobación. *Planificado* = se medirá al cerrar la ampliación. *No verificado*
= depende de la configuración de GitHub o de Render, que no está en el código.

> **Pendiente de contraste.** El texto del Anexo 1 (§ de B2 y EC-12) no está en el repositorio. Antes
> de aprobar este documento, el equipo debe comparar los requisitos RF-B2-01 a RF-B2-08 y el escenario
> EC-12 con el Anexo y corregir lo que difiera.

---

## 1. Resumen

B2 no agrega funcionalidad para el consumidor: construye el **proceso** que lleva un cambio desde el
pull request hasta producción con controles automáticos. Por eso **no modifica `apps/`** y toca el
núcleo en **un solo punto aditivo**: `/healthz/` (en `core/views.py`) agrega la versión desplegada, para
que el pipeline compruebe que staging corre el cambio que se acaba de enviar y no una versión
anterior. Los contratos de `import-linter` no se ven afectados.

| Bloque | Qué incluye | Estimado (h) | Con 15 % de contingencia (h) |
|---|---|---|---|
| **A. Documentos previos** | Este análisis, ADR-0033 y EC-12 refinado (regla 2 del Anexo) | 7 | 8 |
| **B. Protección y CI** | Rama `main` protegida con checks requeridos; CI en jobs paralelos y con caché | 5 | 6 |
| **C. Puertas de calidad** | Quality gate de SonarQube y escaneo de la imagen con Trivy | 8 | 9 |
| **D. Staging** | Servicio de staging, versión en `/healthz/`, despliegue automático, prueba de humo con k6 | 15 | 17 |
| **E. Producción** | Promoción manual, reversión documentada y ensayada | 8 | 9 |
| **F. Evidencia y operación** | Evidencia de EC-12 y guía de operación | 9 | 10 |
| **Total** | | **52** | **60** |

La contingencia se calcula sobre el total (52 h × 1,15 ≈ 60 h); los subtotales por bloque se redondean y por eso
no suman exactamente 60.

Orden de recorte si falta tiempo: primero la reversión automatizada (queda el procedimiento manual
con el panel de Render), luego Trivy. La protección de `main`, el gate de SonarQube, el despliegue a
staging y la evidencia de EC-12 **no se tocan**: son lo que mide el escenario.

---

## 2. Requerimiento del cambio

| ID | Requisito | Prioridad |
|---|---|---|
| RF-B2-01 | Un PR que rompe una prueba, el lint o los límites de arquitectura **no se puede fusionar** en `main` | M |
| RF-B2-02 | El **quality gate de SonarQube** corre dentro del pipeline y bloquea si no pasa | M |
| RF-B2-03 | La imagen Docker se **escanea con Trivy** y el pipeline falla si hay vulnerabilidades altas o críticas con arreglo disponible | M |
| RF-B2-04 | Un cambio que pasa todas las puertas se **despliega solo a staging** | M |
| RF-B2-05 | Después de cada despliegue a staging corre una **prueba de humo con k6** | M |
| RF-B2-06 | La **promoción a producción es manual**, con aprobación de una persona | M |
| RF-B2-07 | Existe un **procedimiento de reversión documentado y probado** | M |
| RF-B2-08 | Hay **evidencia de EC-12**: un PR roto bloqueado y un cambio válido en staging en ≤ 15 min | M |

---

## 3. Estado actual (verificado en el repositorio)

| Aspecto | Hoy | Marca |
|---|---|---|
| CI | `.github/workflows/ci.yml` con tres jobs: `calidad` (ruff, formato, `lint-imports`, migraciones al día, `pytest` con cobertura ≥ 70 %, Playwright), `vercel` (comprobaciones de producción) e `imagen` (`docker build`) | Verificado |
| Otros workflows | `procesar-correos.yml` (reintentos de correo) | Verificado |
| SonarQube | Solo informe manual (`docs/calidad/sonarqube.md`, `sonar-project.properties`); no corre en el CI | Verificado |
| Trivy | No existe | Verificado |
| Staging | No existe; solo hay un servicio en Render (producción) | Verificado |
| Prueba de humo | `scripts/prueba_de_humo.sh` (bash, 23 comprobaciones) y `tests/load/k6/comparacion.js` (500 usuarios, no sirve como humo) | Verificado |
| Despliegue a producción | Render con Auto-Deploy; el equipo lo apaga a mano durante las pruebas | No verificado |
| Protección de `main` y checks requeridos | No se puede ver desde el código | No verificado |
| Reversión | No hay procedimiento escrito | Verificado |

---

## 4. Tabla de componentes

Tipo de cambio: **Nuevo**, **Extensión** (aditivo, sin cambiar contratos) o **Estructural** (cambia
límites de módulo o contratos). La meta es **0 estructurales** (M-18).

| Componente | Tipo de cambio | Esfuerzo estimado (h) | Esfuerzo real (h) | Observaciones |
|---|---|---|---|---|
| **A. Documentos previos** | | | | |
| Análisis de impacto de B2 (este documento) | Nuevo | 3 | | `docs/arquitectura/analisis-impacto-b2-entrega-continua.md` |
| ADR-0033, pipeline de entrega continua | Nuevo | 2 | | `docs/adr/0033-pipeline-de-entrega-continua.md` y fila en el índice |
| EC-12 refinado y métricas M-26 a M-28 | Nuevo | 2 | | `docs/calidad/escenarios-bloque-b2.md`; filas en `trazabilidad-metricas.md` |
| **B. Protección y CI** | | | | |
| Protección de `main` y checks requeridos | Nuevo | 2 | | Configuración de GitHub (requiere administrador del repositorio) |
| Reorganizar `ci.yml` (jobs en paralelo, caché, permisos mínimos, `concurrency`) | Extensión | 3 | | Sin cambiar los nombres de los checks existentes |
| **C. Puertas de calidad** | | | | |
| Quality gate de SonarQube en el pipeline | Nuevo | 5 | | Proyecto y token en el servicio, paso de análisis y de espera del gate, cobertura de `coverage.xml` |
| Escaneo de la imagen con Trivy | Nuevo | 3 | | Paso sobre la imagen construida; `.trivyignore` con motivo y fecha de cada excepción |
| **D. Staging** | | | | |
| Servicio de staging en Render (base, Redis, variables, datos de prueba) | Nuevo | 5 | | Auto-Deploy apagado; secretos solo en Render |
| `/healthz/` con la versión desplegada | Extensión | 2 | | `core/views.py` y `tests/integration/test_healthz.py`; campo adicional, sin romper M-21 |
| Workflow de despliegue a staging | Nuevo | 4 | | `.github/workflows/entrega.yml`: aviso a Render con el SHA, espera hasta que `/healthz/` informe ese SHA |
| Prueba de humo con k6 | Nuevo | 4 | | `tests/load/k6/humo.js` (pocos usuarios, bajo el límite de la API) y paso del pipeline |
| **E. Producción** | | | | |
| Promoción manual a producción | Nuevo | 3 | | Entorno de GitHub `production` con revisores requeridos; el **mismo SHA** que pasó staging |
| Reversión: procedimiento, workflow y ensayo | Nuevo | 5 | | `docs/operacion/entrega-continua.md` y `.github/workflows/revertir.yml`; ensayo con evidencia |
| **F. Evidencia y operación** | | | | |
| Evidencia de EC-12 | Nuevo | 5 | | PR con prueba rota bloqueado y cambio válido cronometrado; capturas en `docs/calidad/evidencias/` |
| Guía de operación | Nuevo | 4 | | `docs/operacion/entrega-continua.md` |
| **Total** | | **52** | | **60 h** con 15 % de contingencia |

**Estructurales: 0.** Ningún archivo de `apps/` cambia. La única edición del núcleo es el campo
aditivo de `/healthz/`.

**Método.** Descomposición por componentes y juicio del equipo, igual que en el análisis de la canasta
(114 h) y del módulo comercial (79 h). B2 pesa menos porque no agrega dominio, pero tiene más
incertidumbre: depende de servicios externos (GitHub, Render, SonarQube).

---

## 5. Riesgos

| Riesgo | Efecto | Tratamiento |
|---|---|---|
| El CI actual es lento (instala Playwright y corre toda la batería) | Cuesta cumplir los 15 min de EC-12 | Medir el tiempo base antes de cambiar nada; paralelizar jobs y usar caché |
| Staging dormido por el plan gratuito de Render | La primera petición tarda unos 50 s | El paso de espera calienta el servicio antes del k6; el presupuesto de 15 min lo incluye |
| Permisos: proteger `main`, crear entornos y secretos requiere ser administrador del repositorio | Bloqueo del bloque B y E | Pedirle esos pasos a la propietaria del repositorio desde el inicio |
| Plan gratuito de SonarQube en la nube o de Render no cubre el uso | Cambia el diseño de C o D | Confirmar antes de construir; la alternativa es dejar el gate en una instancia propia |
| Trivy marca vulnerabilidades de la imagen base | Bloquea cambios que no dependen del equipo | `.trivyignore` con motivo y fecha; actualizar la imagen base cuando haya arreglo |
| Revertir el código no revierte la base de datos | Una reversión puede dejar el esquema adelantado | Migraciones compatibles hacia atrás (ya está en el checklist del PR); documentar el caso |
| Cuotas del plan gratuito de Render (horas y vigencia de la base) | Staging o producción caen en la demostración | Revisar las condiciones vigentes antes del 100 % del trabajo |
| Merges de otras personas mientras se prueba | Falsas fallas o versiones mezcladas | Grupo de `concurrency` en el despliegue y aviso al equipo antes de las corridas de evidencia |

---

## 6. Orden de trabajo y regla 2

La regla 2 del Anexo exige que el historial muestre el análisis **antes** del código. Orden de commits:

1. `docs(b2): análisis de impacto, ADR-0033 y EC-12 refinado` (los tres documentos, **sin código**).
2. Protección de `main` y reorganización de `ci.yml`.
3. Quality gate de SonarQube y Trivy.
4. Staging: servicio, `/healthz/` con versión, `entrega.yml`, `humo.js`.
5. Promoción manual y reversión.
6. Evidencia de EC-12 y guía de operación; horas reales en la tabla de la sección 4.

---

## 7. Decisiones y pendientes del equipo

1. **Aprobar las estimaciones** (52 h; 60 h con contingencia) y el orden de recorte. Con esa aprobación
   queda habilitado el segundo commit.
2. **Servicio del quality gate (D-B2-1).** Propuesta: SonarQube en la nube sobre el repositorio
   público, porque un servidor local no es accesible desde GitHub Actions. Confirmar el plan.
3. **Staging (D-B2-2).** Propuesta: segundo servicio en Render con base y Redis propios.
4. **Administración del repositorio (D-B2-3).** Definir quién configura la protección de `main`, los
   entornos y los secretos.
5. **Contraste con el Anexo 1.** Ver la nota de la cabecera.

---

## Referencias (APA 7)

Bass, L., Clements, P., & Kazman, R. (2021). *Software architecture in practice* (4.ª ed.).
Addison-Wesley Professional.

Corporación Universitaria Empresarial Alexander von Humboldt. (2026). *Anexo 1. Cambio de alcance del
corte 3: funcionalidades de ampliación* [Documento del curso].

Nygard, M. (2011). *Documenting architecture decisions*. Cognitect.
