# ADR-0033: Pipeline de entrega continua con staging, promoción manual y reversión

- **Estado:** Propuesto
- **Fecha:** 2026-11-27
- **Autores:** Equipo; borrador con apoyo de IA, pendiente de revisión humana
- **Escenarios relacionados:** EC-12 (Anexo 1, B2); EC-04 (desempeño, la prueba de humo no lo sustituye), M-21 (disponibilidad); ADR-017, ADR-0031
- **Métricas que lo verifican:** M-26, M-27, M-28 (nuevas, ver `docs/calidad/escenarios-bloque-b2.md`), M-19, M-20, M-21
- **Plantilla:** 8.1 del Anexo 1 (adaptada de Nygard, 2011)

## Contexto

El CI actual (`.github/workflows/ci.yml`) comprueba lint, límites de arquitectura, migraciones,
pruebas con cobertura, la configuración de producción para Vercel y la construcción de la imagen. No
tiene el análisis de SonarQube dentro del pipeline (solo un informe manual), ni escaneo de la imagen,
ni staging, ni promoción controlada, ni un procedimiento de reversión. Producción es un único
servicio de Render con la imagen del ADR-017 y, hasta hoy, el equipo apaga el despliegue automático a
mano cuando prueba.

El Anexo 1 (B2) y EC-12 piden que un cambio válido llegue a staging en 15 minutos o menos, que un cambio
que rompe una prueba quede bloqueado, que la promoción a producción sea manual y que exista una
reversión probada.

Fuerzas:

- **El gate no puede ser de un solo equipo.** El análisis de SonarQube que hoy se corre a mano en una
  máquina no sirve como control del pipeline.
- **Un solo artefacto.** Lo que se prueba en staging debe ser **exactamente** lo que se promueve a
  producción: el mismo commit.
- **Plan gratuito.** Render gratuito duerme el servicio tras un rato sin tráfico, y el CI debe caber
  en el presupuesto de 15 minutos de EC-12.
- **Los datos no se revierten con el código.** Una reversión de la aplicación no deshace las
  migraciones ya aplicadas.
- **No romper lo que funciona.** El despliegue en Render, la imagen Docker y la alternativa de
  Vercel (ADR-0031) siguen igual.

Hechos de Render consultados el 2026-11-27 en su documentación (se deben confirmar al implementar):
el despliegue automático puede ser *On Commit* (solo después de que pasen los checks de CI de GitHub)
u *Off*; cada servicio tiene una URL de *deploy hook* que acepta un parámetro `ref` con el SHA del
commit y, al usarlo, **desactiva el despliegue automático** del servicio; el panel ofrece *Rollbacks*
para volver a un despliegue anterior.

## Alternativas consideradas

| Alternativa | A favor | En contra |
|---|---|---|
| 1. Solo el Auto-Deploy de Render «después de los checks», sin staging | Cero configuración nueva | No hay staging ni promoción manual; no cumple EC-12 |
| 2. Dos servicios de Render con Auto-Deploy por rama (`develop` a staging, `main` a producción) | Sencillo de entender | Se despliegan commits distintos en cada entorno; la promoción no es del mismo artefacto; hay que mantener `develop` |
| 3. **GitHub Actions orquesta dos servicios de Render con *deploy hooks* y SHA** (elegida) | Mismo commit en staging y producción; aprobación manual nativa; todo queda en el historial de Actions | Más piezas que mantener (secretos, workflows) |
| 4. Mover a una plataforma con pipelines propios (Cloud Run con Cloud Deploy, por ejemplo) | Herramientas más completas | Fuera de alcance: cambia el ADR-017 y supera el tiempo disponible |

## Decisión

Se adopta la alternativa 3, con estas reglas:

- **Puertas en el PR.** `main` queda protegida: PR obligatorio, una aprobación y los checks
  `calidad`, `vercel`, `imagen`, `sonarqube` y `trivy` como requeridos. Sin force push.
- **SonarQube.** El análisis corre en el CI con la cobertura del job `calidad` y espera el resultado
  del quality gate; si no pasa, el check falla. Se usa SonarQube en la nube sobre el repositorio
  público, porque un servidor local no es accesible desde los ejecutores de GitHub.
- **Trivy.** Escanea la imagen de producción construida en el CI. Falla con vulnerabilidades
  **altas o críticas con arreglo disponible**. Las excepciones van en `.trivyignore`, cada una con motivo
  y fecha de revisión.
- **Staging.** Un segundo servicio de Render con la misma imagen, base y Redis propios y datos de
  prueba. Su despliegue automático queda **apagado**: lo dispara el workflow `entrega.yml` con el
  *deploy hook* y el SHA del commit, solo en `push` a `main` y después de pasar las puertas.
- **Versión visible.** `/healthz/` agrega el campo `version` (SHA). El workflow espera hasta que staging
  informe el SHA enviado y solo entonces corre la prueba de humo; así no se prueba una versión vieja.
- **Prueba de humo con k6.** `tests/load/k6/humo.js`: pocos usuarios virtuales y poco tiempo, con
  p95 < 2 s y errores < 1 %, y por debajo del límite de la API para anónimos (120 solicitudes por
  minuto por IP). Primero hace una petición de calentamiento por el servicio dormido.
- **Promoción manual.** Un job con el entorno de GitHub `production` (revisores requeridos) despliega a
  producción **el mismo SHA** que pasó staging, y vuelve a correr la prueba de humo.
- **Reversión.** Dos vías documentadas y ensayadas: (a) urgente, *Rollbacks* de Render desde el
  panel; (b) trazable, el workflow `revertir.yml` (`workflow_dispatch` con el SHA anterior) que usa el
  mismo *deploy hook*. Las migraciones deben ser compatibles hacia atrás (ya está en el checklist
  del PR) para que revertir el código no deje el esquema incompatible.
- **Secretos.** Los *deploy hooks*, el token de SonarQube y las URL viven en secretos y entornos de
  GitHub, nunca en el repositorio.
- **Orden de entrega.** El análisis de impacto, este ADR y EC-12 se fusionan **antes** que cualquier
  código de B2 (regla 2 del Anexo).

## Consecuencias

**Positivas.** Un cambio roto no llega a `main` ni a staging; lo probado en staging es lo que se
promueve; la reversión queda escrita y ensayada; el historial de Actions es evidencia de EC-12.

**Negativas (trade-offs aceptados).**

- Staging gratuito duerme: la primera petición tarda unos 50 s. El presupuesto de 15 minutos lo incluye,
  pero deja poco margen: el CI actual instala Playwright y corre toda la batería y su tiempo **no
  se ha medido todavía**.
- Usar el *deploy hook* con SHA desactiva el despliegue automático en Render. Es lo buscado, pero
  hay que recordarlo si alguien intenta «arreglar» un despliegue desde el panel.
- Dependencia de dos servicios externos (SonarQube en la nube y GitHub) para fusionar.
- Revertir el código no revierte los datos.

**Riesgos.** Las cuotas del plan gratuito de Render y de SonarQube pueden cambiar el diseño; falsos
positivos de Trivy en la imagen base; permisos de administrador necesarios para proteger la rama y
crear entornos.

**Qué haría revisar esta decisión.** Que el cambio válido supere los 15 minutos en más de una de tres
corridas; que la prueba de humo falle por el sueño de staging y no por la aplicación; que el
costo de mantener los dos servicios supere el beneficio.

## Verificación

- Un PR con una prueba rota, bloqueado por los checks requeridos (captura).
- Un cambio válido que llega a staging en ≤ 15 minutos con la prueba de humo en verde (M-26).
- Ensayo de reversión con evidencia (M-28).
- `tests/integration/test_healthz.py` cubre el campo `version` sin romper M-21.
