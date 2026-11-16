# SonarQube en local (Windows + Docker)

Análisis estático del repositorio con SonarQube Community. Complementa a Ruff (estilo y reglas
de Python), import-linter (límites de arquitectura) y pytest-cov (cobertura). La configuración
del proyecto está en [`sonar-project.properties`](../../sonar-project.properties).

**Requisitos:** Docker Desktop con WSL 2, al menos 4 GB de RAM libres para el contenedor y el
entorno del proyecto (`.venv`) con las dependencias de `requirements/dev.txt`.

Todos los comandos son para **PowerShell**, desde la raíz del repositorio.

## 1. Levantar el servidor (una sola vez)

```powershell
docker run -d --name sonarqube -p 9000:9000 sonarqube:community
docker logs -f sonarqube    # esperar "SonarQube is operational" y salir con Ctrl+C
```

1. Abrir <http://localhost:9000>, entrar con `admin` / `admin` y cambiar la contraseña cuando
   la pida.
2. *Create Project → Local project*, con la clave `plataforma-precios-quindio`.
3. *My Account → Security → Generate Tokens*: tipo **Project Analysis Token** para ese proyecto.
   El token es personal: no se versiona ni se pega en issues, PR o chats.

En las siguientes sesiones basta con `docker start sonarqube`.

## 2. Generar la cobertura

SonarQube no ejecuta las pruebas; lee el `coverage.xml` que deja pytest. `pyproject.toml` usa
`relative_files = true` para que las rutas se resuelvan dentro del contenedor del escáner.

```powershell
.venv\Scripts\activate
pytest --cov --cov-report=xml
```

## 3. Ejecutar el análisis

```powershell
$env:SONAR_TOKEN = "<token del paso 1>"     # solo en esta terminal
docker run --rm `
  -e SONAR_HOST_URL="http://host.docker.internal:9000" `
  -e SONAR_TOKEN=$env:SONAR_TOKEN `
  -v "${PWD}:/usr/src" `
  sonarsource/sonar-scanner-cli
Remove-Item Env:SONAR_TOKEN
```

El escáner lee `sonar-project.properties`. Al terminar, imprime el enlace al panel del proyecto.

## 4. Qué registrar como evidencia

En `docs/calidad/evidencias/<fecha>/sonarqube.md` se anotan los valores del panel *Overview*
(código completo, no solo *New Code*):

| Indicador | Dónde se ve |
|---|---|
| Quality Gate (Passed / Failed) | Encabezado del proyecto |
| Bugs y rating de fiabilidad | Overview → Reliability |
| Vulnerabilidades y rating de seguridad | Overview → Security |
| Security Hotspots revisados | Overview → Security Review |
| Code smells, rating de mantenibilidad y deuda técnica | Overview → Maintainability |
| Cobertura | Overview → Coverage (debe coincidir con `pytest --cov`, ±1 punto) |
| Duplicación | Overview → Duplications |

Si la cobertura sale en 0 %, revisa que `coverage.xml` exista en la raíz y que se haya
generado después del último cambio.

## 5. Detener o borrar

```powershell
docker stop sonarqube          # conserva los datos
docker rm -f sonarqube         # borra el contenedor y su historial de análisis
```
