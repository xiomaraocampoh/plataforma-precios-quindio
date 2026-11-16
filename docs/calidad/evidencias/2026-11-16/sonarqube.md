# SonarQube · 2026-11-16

**Estado: no ejecutado.**

En el equipo donde se preparó el cierre no está instalado Docker (`docker: command not found`).
Sin Docker no se puede levantar `sonarqube:community` ni ejecutar `sonarsource/sonar-scanner-cli`,
como describe [docs/calidad/sonarqube.md](../../sonarqube.md).

Ya quedó listo:

- `sonar-project.properties` en la raíz (clave `plataforma-precios-quindio`; fuentes
  `apps,config,core`; pruebas `tests`; migraciones excluidas; `coverage.xml` como informe).
- `pyproject.toml` con `relative_files = true`, para que SonarQube resuelva las rutas de cobertura
  dentro del contenedor del escáner.

Para completar esta evidencia hace falta:

1. Instalar Docker Desktop (con WSL 2) en un equipo del equipo de trabajo.
2. Seguir los pasos 1 a 3 de `docs/calidad/sonarqube.md`.
3. Reemplazar la tabla siguiente con los valores del panel *Overview*.

| Indicador | Valor |
|---|---|
| Quality Gate | pendiente |
| Bugs | pendiente |
| Vulnerabilidades | pendiente |
| Security Hotspots | pendiente |
| Code smells | pendiente |
| Rating de mantenibilidad | pendiente |
| Deuda técnica | pendiente |
| Cobertura | pendiente (pytest-cov reporta el valor en `07-final-pytest-cobertura.txt`) |
| Duplicación | pendiente |
