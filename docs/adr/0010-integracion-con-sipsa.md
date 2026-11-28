# ADR-0010: Integrar SIPSA mediante puerto y adaptador

- **Estado:** Aceptado (aprobado por el equipo el 2026-11-27), con el cambio de implementación descrito abajo
- **Fecha:** 2026-11-06 (registro del Corte 1, C1-AS2-E2); archivado en el repositorio el 2026-11-27
- **Autores:** Equipo; redactado con apoyo de IA
- **Escenarios de calidad afectados:** carga inicial de datos (pregunta de diseño 5); compatibilidad
- **Métricas que lo verifican:** D-01 (referencia separada de la comparación)

## Contexto
Antes de que exista una comunidad de reportantes, la plataforma necesita datos iniciales. SIPSA,
del DANE, publica precios mayoristas de alimentos.

## Alternativas consideradas
| Alternativa | A favor | En contra |
|---|---|---|
| **A. Puerto `FuentePreciosExterna` y adaptador SIPSA** | La plataforma opera aunque SIPSA falle; fuente reemplazable y probable con un doble sin red | Una pieza más que mantener |
| B. Consultar SIPSA en línea en cada comparación | Siempre actualizado | Acopla la disponibilidad a un tercero |
| C. Extraer automáticamente (*scraping*) catálogos de cadenas | Más datos | Riesgo con los términos de uso |

## Decisión
Alternativa A. Un adaptador SIPSA con tiempo de espera de 5 s. Los precios importados se marcan con
fuente «sipsa» y se presentan como referencia, nunca como precio de un establecimiento.

## Consecuencias
- (+) La plataforma opera aunque SIPSA falle.
- (+) La fuente es reemplazable y se prueba con un doble sin red.
- Solo el 20 % de los consumidores encuestados registraría precios, y las categorías de mayor
  interés (lácteos, huevos y aseo) no están cubiertas del todo por SIPSA; por eso la carga manual
  en establecimientos piloto prioriza esas categorías.

## Cambio en la implementación
La carga es manual: `python manage.py importar_sipsa archivo.csv` lee un CSV descargado del DANE,
porque SIPSA publica boletines y no una API estable. Se conservan el puerto, el cliente con tiempo
de espera y la marca de fuente «sipsa». La referencia se muestra como bloque aparte y no entra en el
orden.

## Evidencia en el código
- `apps/integraciones/clients/sipsa.py`, `apps/integraciones/domain/sipsa.py`.
- `apps/integraciones/management/commands/importar_sipsa.py`.
- `docs/integraciones/sipsa.md`.
