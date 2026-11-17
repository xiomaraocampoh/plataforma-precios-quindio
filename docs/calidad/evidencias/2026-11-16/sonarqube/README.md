# SonarQube · 2026-11-16 (M-19, M-20)

**Qué se hizo.** Se levantó `sonarqube:community` (versión 26.11) en un contenedor propio en `127.0.0.1:9001` (el
contenedor ajeno del puerto 9000 no se tocó) y se analizó el repositorio con `sonarsource/sonar-scanner-cli` y el
archivo [`sonar-project.properties`](../../../../../sonar-project.properties) ya existente, con la cobertura de las
pruebas (`pytest --cov --cov-report=xml`, 622 pruebas, incluida la de navegador). Las capturas son del panel real.

## Resultado

| Indicador (todo el código) | Primer análisis («antes») | Tras corregir los hallazgos reales («después») |
|---|---|---|
| Puerta de calidad (*Quality gate*) | Passed | Passed |
| Seguridad | **E**, 4 hallazgos | **D**, 1 hallazgo abierto |
| Fiabilidad | C, 8 hallazgos | **C**, 6 hallazgos abiertos (ver más abajo) |
| Mantenibilidad | A, 6 hallazgos | A, 6 hallazgos |
| Cobertura | 95,1 % | 95,1 % |
| Duplicación | 0,0 % | 0,0 % |
| *Security hotspots* | 0 | 0 |
| Líneas de código | 7,9 mil | 7,9 mil |

En el código nuevo del segundo análisis: 0 incidencias nuevas, cobertura 100 % sobre 3 líneas nuevas, duplicación 0,0 %.

Capturas (`antes-*` y `despues-*`): resumen, vulnerabilidades, listado de hallazgos, cobertura y el panel «Overall Code».

## Los hallazgos del primer análisis y qué se hizo (revisados uno por uno)

| Hallazgo | Veredicto | Qué se hizo |
|---|---|---|
| `secrets:S6698` (bloqueante) contraseña de PostgreSQL en `config/settings/base.py` | **Real**: era la contraseña de desarrollo escrita en el código; la regla del proyecto dice que los secretos van solo por entorno | Se quitó: `DATABASE_URL` es obligatoria y el arranque falla con un mensaje claro si falta. Prueba de regresión |
| `Web:InputWithoutLabelCheck` (error) campo de archivo oculto de la cámara en `buscar.html` | **Real**, y era código del escáner | Se le dio nombre accesible (`aria-label`) a los campos de archivo. Prueba de regresión |
| `python:S3752` `healthz` sin métodos permitidos | **Real, menor** | `healthz` acepta solo lectura (GET/HEAD); POST responde 405. Prueba de regresión |
| `python:S8786` expresión regular de correos con costo cuadrático | **Real**: con 60 000 caracteres sin «@» se reintentaba desde cada posición | Se acotó con los máximos de los RFC (parte local 64, etiqueta 63). Prueba de regresión |
| `Web:S5247` `\|safe` del QR en `configurar_app.html` | **Falso positivo, verificado**: el QR (qrcode, `SvgPathImage`) solo contiene `<svg>` y `<path>`, incluso con texto hostil | Se marcó como falso positivo en SonarQube con su justificación, y hay una prueba que lo demuestra |
| `python:S4502` (crítico) `@csrf_exempt` en la baja de correos (`seguridad.py:237`) | **Justificado, pero queda abierto**: es el POST sin sesión del estándar RFC 8058 (`List-Unsubscribe-Post`); la autenticidad la da el token firmado | **Sin cambios.** Pendiente de que la responsable del módulo de correo lo confirme y lo acepte en SonarQube |
| `Web:S6845` ×6 `tabindex="0"` en regiones con scroll (administración, moderación, mis aportes, vista previa de correos) | **Intencional**: las tablas con desplazamiento deben poder enfocarse con el teclado (WCAG 2.1.1) | **Sin cambios.** Sigue contando como fiabilidad media, por eso Fiabilidad permanece en C |

Con el hallazgo del CSRF abierto, la calificación de Seguridad queda en **D** y no en A. Si se confirma como aceptable y se marca
como tal en SonarQube, cambiaría; no se hizo porque la decisión no es de quien ejecutó el análisis.

## Advertencias del propio análisis

- *«Cannot resolve the file path '__init__.py' of the coverage report, ambiguity»*: SonarQube no pudo ubicar los
  `__init__.py` vacíos de varias carpetas dentro del informe de cobertura; el 95,1 % se calculó con el resto de archivos.
- *«Shallow clone detected / Missing blame information for 277 files»*: el repositorio montado en el contenedor del
  escáner no trae historial completo de git, así que no hay información de autoría por línea. No afecta los resultados.
- La edición Community **no analiza vulnerabilidades de inyección (SQL, XSS)**; el propio panel lo advierte. El análisis
  de seguridad es parcial.
- Se usó una instancia local con base de datos embebida (el panel avisa que es solo para evaluación): estas capturas son
  la evidencia; el contenedor no es un servicio permanente.

## Cómo repetirlo

```bash
docker run -d --name sonarqube-ahorrapues -p 127.0.0.1:9001:9000 sonarqube:community
pytest --cov --cov-report=xml
docker run --rm -e SONAR_HOST_URL=http://host.docker.internal:9001 -e SONAR_TOKEN=<token> \
  -v "$PWD:/usr/src" sonarsource/sonar-scanner-cli
```
