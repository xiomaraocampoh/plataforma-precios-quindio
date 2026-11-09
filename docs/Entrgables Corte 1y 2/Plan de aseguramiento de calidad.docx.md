**Plan de Aseguramiento de Calidad: Plataforma Colaborativa de Comparación de Precios (Armenia, Quindío)**

María Luisa Londoño Moncada  
Xiomara Ocampo Hurtado  
Juan Manuel Rodríguez  
Derly Elena Quejada Peres

Profesor: Ing. Rubén Darío Díaz Bautista

Corporación Universitaria Alexander von Humboldt  
Facultad de Ingenierías y Ciencias Básicas  
Ingeniería de Software  
2026

**Resumen**  
Este documento presenta el plan de aseguramiento de calidad de una plataforma web colaborativa para registrar, consultar y comparar precios de la canasta familiar en Armenia y el Quindío, desarrollada en el Seminario Nuclear 4 (Modelos de Calidad y Arquitectura de Software II). El plan adopta la norma ISO/IEC 25010:2023 como modelo de calidad del producto, complementada con ISO/IEC 25012 para la calidad de los datos y con ISO/IEC 25040 para la evaluación, y justifica esta elección frente a los modelos de McCall, Boehm y FURPS+. A partir del contexto del producto se priorizan la adecuación funcional, la capacidad de interacción, la seguridad, la eficiencia de desempeño y la mantenibilidad; se identifican sus subcaracterísticas críticas y se definen 22 métricas de producto y 6 de datos, cada una con fórmula, herramienta, valor objetivo y valor mínimo de aceptación. Por último, se establecen la estrategia de pruebas por niveles, los criterios de entrada y salida, la gestión de incidencias, las prácticas de aseguramiento del proceso, el cronograma de calidad por corte y los roles del equipo.  
***Palabras clave*****:** calidad, ISO/IEC 25010, métricas, pruebas, aseguramiento.

**Tabla de Contenido**

[Introducción	6](#introducción)

[Justificación	8](#justificación)

[Objetivos	9](#objetivos)

[Objetivo General	9](#objetivo-general)

[Objetivos Específicos	9](#objetivos-específicos)

[Modelo de Calidad Adoptado y Justificación	10](#modelo-de-calidad-adoptado-y-justificación)

[Comparación con Modelos Clásicos	10](#comparación-con-modelos-clásicos)

[Razones de la Elección	11](#razones-de-la-elección)

[Contexto del Producto	12](#contexto-del-producto)

[Priorización de Características	13](#priorización-de-características)

[Subcaracterísticas Críticas	15](#subcaracterísticas-críticas)

[Métricas y Umbrales de Aceptación	16](#métricas-y-umbrales-de-aceptación)

[Estrategia de Pruebas	19](#estrategia-de-pruebas)

[Niveles de Prueba	19](#niveles-de-prueba)

[Criterios de Entrada y Salida	20](#criterios-de-entrada-y-salida)

[Gestión de Incidencias	20](#gestión-de-incidencias)

[Aseguramiento del Proceso	21](#aseguramiento-del-proceso)

[Cronograma de Calidad por Corte	22](#cronograma-de-calidad-por-corte)

[Roles	23](#roles)

[Conclusiones	24](#conclusiones)

[Recomendaciones	25](#heading=h.xs4z2xmipb04)

[Referencias Bibliográficas	26](#referencias-bibliográficas)

**Lista de Tablas**  
[**Tabla 1** *Control de Versiones del Documento*	8](#heading=h.gvouzknf495l)  
[**Tabla 2** *Comparación del Modelo Adoptado con los Modelos Clásicos de Calidad*	11](#tabla-2-comparación-del-modelo-adoptado-con-los-modelos-clásicos-de-calidad)  
[**Tabla 3** *Contexto del Producto*	13](#tabla-3-contexto-del-producto)  
[**Tabla 4** *Priorización de Características de ISO/IEC 25010:2023*	14](#tabla-4-priorización-de-características-de-iso/iec-25010:2023)  
[**Tabla 5** *Subcaracterísticas Críticas por Característica*	16](#tabla-5-subcaracterísticas-críticas-por-característica)  
[**Tabla 6** *Métricas, Herramientas y Umbrales de Aceptación*	17](#tabla-6-métricas,-herramientas-y-umbrales-de-aceptación)  
[**Tabla 7** *Niveles de Prueba, Técnicas y Métricas Asociadas*	20](#tabla-7-niveles-de-prueba,-técnicas-y-métricas-asociadas)  
[**Tabla 8** *Prácticas de Aseguramiento del Proceso*	22](#tabla-8-prácticas-de-aseguramiento-del-proceso)  
[**Tabla 9** *Actividades de Calidad por Corte*	23](#tabla-9-actividades-de-calidad-por-corte)  
[**Tabla 10** *Roles y Responsabilidades del Equipo*	24](#tabla-10-roles-y-responsabilidades-del-equipo)

# **Introducción** {#introducción}

Este plan define qué calidad debe tener la plataforma colaborativa de comparación de precios de Armenia y el Quindío, cómo se medirá y qué valor se considera suficiente. Corresponde al Entregable 1 del Corte 1 del curso Modelos de Calidad y se presenta en su versión 1.1. Cubre el **núcleo** del producto (catálogo, registro colaborativo, directorio y comparación) y se amplíará al **módulo comercial** en los cortes 2 y 3\.  
Se distinguen dos objetos de calidad:

* **Calidad del producto:** el software y sus datos, evaluados con ISO/IEC 25010:2023 e ISO/IEC 25012 (International Organization for Standardization \[ISO\], 2008, 2023).  
* **Calidad del proceso:** la forma en que el equipo construye el software (revisiones, integración continua, TDD y gestión de incidencias), con referencia conceptual a ISO/IEC y CMMI.

El **aseguramiento** (prevenir defectos con prácticas del proceso) se diferencia del **control** (detectar defectos en el producto con pruebas y medición). Este plan define ambos.**Tabla 1**  
*Control de Versiones del Documento*

| Versión | Fecha | Cambios | Responsable |
| ----- | ----- | ----- | ----- |
| 1.0 | 2026-11-06 | Versión inicial. | Xiomara Ocampo Hurtado |
| 1.1 | 2026-11-07 | Roles asignados; prueba de usabilidad ajustada a mínimo 5 usuarios; TDD de detección de duplicados (D-05); verificación de formato en CI. | Xiomara Ocampo Hurtado |

*Nota.* Registro de los cambios realizados al plan en cada versión.  
**Declaración de uso de inteligencia artificial.** Este plan se redactó con apoyo de un asistente de IA generativa (Claude, Anthropic) a partir del modelo de calidad elaborado por el equipo.

# **Justificación** {#justificación}

La plataforma no maneja dinero, pero su valor depende de que los datos sean confiables, actuales y neutrales. Además, trata datos personales protegidos por la Ley 1581 de 2012 y está expuesta a manipulación mediante reportes falsos o coordinados. Por eso no basta con que el software funcione: es necesario declarar de antemano qué atributos de calidad son prioritarios, cómo se medirán y qué umbral se considera aceptable.  
El uso mayoritario desde el celular, con conectividad limitada y picos de consulta en quincena, hace que la rapidez del registro y el desempeño sean decisivos para que el modelo colaborativo funcione. A esto se suma que el módulo comercial se agregará sobre un núcleo ya construido, lo que exige código modificable y probado con TDD.  
Contar con métricas y umbrales definidos desde el primer corte permite al equipo prevenir defectos durante la construcción, detectarlos antes de cada entrega y verificar en los cortes siguientes si el producto y el proceso cumplen lo previsto, lo que a su vez orienta el plan de mejora.

# **Objetivos** {#objetivos}

## **Objetivo General** {#objetivo-general}

Definir el plan de aseguramiento y control de la calidad de la plataforma colaborativa de comparación de precios, con base en ISO/IEC 25010:2023 e ISO/IEC 25012, que permita medir y evaluar la calidad del producto, de sus datos y del proceso a lo largo de los tres cortes del proyecto.

## **Objetivos Específicos** {#objetivos-específicos}

* Seleccionar y justificar el modelo de calidad de referencia frente a los modelos clásicos de McCall, Boehm y FURPS+.  
* Priorizar las características de calidad y sus subcaracterísticas críticas a partir del contexto del producto.  
* Definir las métricas, fórmulas, herramientas y umbrales de aceptación para el producto y sus datos.  
* Establecer la estrategia de pruebas por niveles, los criterios de entrada y salida y la gestión de incidencias.  
* Definir las prácticas de aseguramiento del proceso, el cronograma de calidad y los roles del equipo.

   

# **Modelo de Calidad Adoptado y Justificación** {#modelo-de-calidad-adoptado-y-justificación}

Se adopta **ISO/IEC 25010:2023** para la calidad del producto (ISO, 2023), complementado con **ISO/IEC 25012** para la calidad de los datos (ISO, 2008), con medidas al estilo de ISO/IEC 2502n y evaluación según **ISO/IEC 25040** (ISO, 2024).

## **Comparación con Modelos Clásicos** {#comparación-con-modelos-clásicos}

La Tabla 2 compara el modelo adoptado con los modelos clásicos de McCall et al. (1977), Boehm et al. (1978) y FURPS+ (Grady y Caswell, 1987).  
**Tabla 2**  
*Comparación del Modelo Adoptado con los Modelos Clásicos de Calidad*

| Criterio | McCall (1977) | Boehm (1978) | FURPS+ (Grady, 1987\) | ISO/IEC 25010:2023 |
| ----- | ----- | ----- | ----- | ----- |
| Estructura | 11 factores en 3 perspectivas (operación, revisión, transición), criterios y métricas. | Jerarquía desde la utilidad general hasta características primitivas. | 5 categorías (funcionalidad, usabilidad, fiabilidad, rendimiento, soportabilidad) \+ restricciones. | 9 características y sus subcaracterísticas, más modelo de calidad en uso. |
| Seguridad de la información | Integridad como factor, sin desglose. | No explícita. | Dentro de funcionalidad. | Característica propia: confidencialidad, integridad, no repudio, responsabilidad, autenticidad, resistencia. |
| Interacción y accesibilidad | Usabilidad general. | Ingeniería humana. | Usabilidad. | Capacidad de interacción, con inclusividad (accesibilidad) y protección contra errores del usuario. |
| Calidad de datos | No la cubre. | No la cubre. | No la cubre. | Modelo complementario ISO/IEC 25012\. |
| Medición y evaluación | Métricas propuestas, no estandarizadas. | Sin proceso formal. | Orientado a requisitos, sin catálogo de medidas. | Medidas en 2502n y proceso de evaluación en 25040\. |
| Vigencia | Histórico. | Histórico. | Usado en industria (IBM RUP). | Vigente, revisión 2023\. |

*Nota.* Elaboración propia a partir de McCall et al. (1977), Boehm et al. (1978), Grady y Caswell (1987) e ISO (2023).

## **Razones de la Elección** {#razones-de-la-elección}

1. **Seguridad e integridad** son críticas por los reportes falsos y la Ley 1581 de 2012; solo 25010 las desglosa en subcaracterísticas medibles.  
2. El carácter colaborativo hace que la **calidad de los datos** sea tan importante como la del software; ninguno de los modelos clásicos la contempla.  
3. La guía exige evaluar con **ISO/IEC 25040**, que está integrada con 25010\.  
4. 25010:2023 incorpora **inclusividad** y **protección contra errores del usuario**, alineadas con WCAG 2.2 AA (World Wide Web Consortium \[W3C\], 2023\) y con el riesgo de registrar en una unidad equivocada.

Se reconoce la herencia de los clásicos: la descomposición jerárquica característica \-\> subcaracterística \-\> medida viene de McCall y Boehm, y la visión práctica de requisitos no funcionales, de FURPS+. Se descarta aplicar un modelo clásico porque obligaría a añadir por fuera seguridad, accesibilidad y calidad de datos.

# **Contexto del Producto** {#contexto-del-producto}

La Tabla 3 describe el tipo de producto, sus usuarios, el ambiente de uso y su criticidad.  
**Tabla 3**  
*Contexto del Producto*

| Aspecto | Descripción |
| ----- | ----- |
| Tipo de producto | Plataforma web/móvil informativa y colaborativa para registrar, consultar y comparar precios de consumo masivo. |
| Usuarios | Consumidor (con o sin cuenta), Reportante, Comercio (voluntario), Moderador. |
| Ambiente | Uso desde celular, a menudo con conectividad limitada; Armenia y Quindío; 500 concurrentes en quincena; despliegue en nube; consultas ≫ registros. |
| Criticidad | Media. No maneja dinero, pero su valor depende de datos confiables, actuales y neutrales; maneja datos personales y está expuesta a manipulación. |

*Nota.* Caracterización del producto que sirve de base para la priorización de características.

# **Priorización de Características** {#priorización-de-características}

La Tabla 4 asigna una prioridad a cada característica de ISO/IEC 25010:2023 y la relaciona con los escenarios de calidad (EC) del proyecto.  
**Tabla 4**  
*Priorización de Características de ISO/IEC 25010:2023*

| Característica ISO/IEC 25010:2023 | Prioridad | Razón | Escenarios |
| ----- | ----- | ----- | ----- |
| Adecuación funcional | Alta | Si la comparación por unidad, la vigencia o las promociones se calculan mal, el producto pierde su razón de ser. Incluye la neutralidad del orden. | EC-06 |
| Capacidad de interacción | Alta | El modelo colaborativo solo funciona si registrar es rapidísimo y con mala señal. | EC-01 |
| Seguridad | Alta | Riesgo de reportes falsos o coordinados y obligación legal de proteger identidad y ubicación de los reportantes. | EC-03, EC-07 |
| Eficiencia de desempeño | Alta | Las consultas dominan la carga y hay picos de quincena. | EC-04 |
| Mantenibilidad | Alta | El módulo comercial se agrega sobre un núcleo construido; TDD exige código fácil de probar. | EC-05 |
| Fiabilidad | Media | No perder registros hechos con conectividad intermitente; una caída corta no causa daños graves. | EC-08, EC-04 |
| Flexibilidad | Media | Escalar ante picos y funcionar en distintos navegadores móviles. | EC-04 |
| Compatibilidad | Baja | Solo interopera con fuentes externas opcionales (SIPSA). |  |
| Protección (safety) | No aplica | No controla equipos ni puede causar daño físico o económico directo. Se documenta como descartada. |  |

*Nota.* EC \= escenario de calidad definido en la arquitectura del proyecto.  
**Calidad de datos (ISO/IEC 25012):** se priorizan actualidad, credibilidad, exactitud, consistencia, completitud, trazabilidad y confidencialidad.

# **Subcaracterísticas Críticas** {#subcaracterísticas-críticas}

    La Tabla 5 identifica, para cada característica priorizada, las subcaracterísticas críticas y por qué importan en este producto.  
**Tabla 5**  
*Subcaracterísticas Críticas por Característica*

| Característica | Subcaracterísticas críticas | Por qué importan aquí |
| ----- | ----- | ----- |
| Adecuación funcional | Corrección funcional; completitud funcional | Precio por unidad (\$/kg, \$/L), promociones, vigencia y orden neutral correctos; todas las funciones del núcleo presentes. |
| Capacidad de interacción | Operabilidad; protección contra errores del usuario; inclusividad; aprendibilidad | Registrar en ≤ 15 s, evitar unidad o presentación equivocada, cumplir WCAG 2.2 AA y lograrlo sin capacitación. |
| Seguridad | Integridad; autenticidad; responsabilidad; confidencialidad; resistencia | Reportes falsos no vigentes; solo autenticados registran; cada precio con autor y fuente; no exponer al reportante; resistir reportes masivos. |
| Eficiencia de desempeño | Comportamiento temporal; capacidad; utilización de recursos | p95 ≤ 2 s con 500 concurrentes, sin errores ni costos desbordados. |
| Mantenibilidad | Modificabilidad; modularidad; capacidad de prueba; analizabilidad | Agregar el módulo comercial sin rediseñar el núcleo; reglas cubiertas con TDD; código limpio en análisis estático. |
| Fiabilidad | Disponibilidad; tolerancia a fallos; recuperabilidad | Disponible en horarios de compra; registros sin señal sincronizados sin pérdida. |
| Flexibilidad | Escalabilidad; adaptabilidad | Escalar horizontalmente en quincena; funcionar en navegadores móviles comunes. |

*Nota.* Subcaracterísticas tomadas de ISO/IEC 25010:2023 (ISO, 2023).

# **Métricas y Umbrales de Aceptación** {#métricas-y-umbrales-de-aceptación}

Las fórmulas aplicadas para las métricas y umbrales de aceptación siguen el estilo de ISO/IEC 25023 (X \= A/B) y las medidas de datos, el de ISO/IEC 25024\. **Objetivo** es la calidad deseada; **mínimo** es el valor por debajo del cual la característica no cumple y se abre una incidencia.  
 La Tabla 6 presenta las métricas de producto (M) y de datos (D).  
**Tabla 6**  
*Métricas, Herramientas y Umbrales de Aceptación*

| ID | Subcaracterística | Métrica y fórmula | Herramienta | Objetivo | Mínimo |
| ----- | ----- | ----- | ----- | ----- | ----- |
| M-01 | Operabilidad | Registros completados en ≤ 15 s / intentos | Prueba con usuarios, red 3G simulada | ≥ 90 % | ≥ 80 % |
| M-02 | Protección contra errores | Registros con unidad, presentación o establecimiento equivocado / registros | Prueba con usuarios \+ revisión | ≤ 5 % | ≤ 10 % |
| M-03 | Inclusividad | Criterios WCAG 2.2 AA cumplidos / aplicables | Lighthouse, axe, WAVE \+ revisión manual | 100 % | ≥ 90 % y 0 fallos nivel A |
| M-04 | Aprendibilidad | Usuarios nuevos que registran y consultan sin ayuda / evaluados | Prueba con usuarios (SUS complementario) | ≥ 90 % | ≥ 80 % |
| M-05 | Corrección funcional | Casos de reglas de negocio aprobados / ejecutados | pytest (TDD) | 100 % | 90 % |
| M-06 | Corrección (neutralidad) | Resultados con orden según criterio declarado y promoción marcada / evaluados | Pruebas automatizadas con dataset de promociones | 100 % | 90 % |
| M-07 | Completitud funcional | Funciones del núcleo implementadas / especificadas | Matriz de trazabilidad | 100 % | ≥ 90 %  |
| M-08 | Comportamiento temporal | Percentil 95 del tiempo de respuesta con 500 usuarios virtuales | k6 | ≤ 1,5 s | ≤ 2 s |
| M-09 | Capacidad | Peticiones fallidas / totales con 500 concurrentes | k6 | ≤ 0,5 % | ≤ 1 % |
| M-10 | Utilización de recursos | % máximo de CPU y RAM en el pico | Métricas del proveedor / Grafana | ≤ 60 % | ≤ 80 % |
| M-11 | Integridad | Anómalos detectados / anómalos del conjunto de prueba | Dataset sembrado con reportes falsos y coordinados | ≥ 90 % | ≥ 80 % |
| M-12 | Integridad | Legítimos marcados como anómalos / legítimos | Mismo dataset | ≤ 5 % | ≤ 10 % |
| M-13 | Autenticidad | Endpoints de escritura con autenticación / endpoints de escritura | Revisión de OpenAPI \+ pruebas de API | 100 % | 900 % |
| M-14 | Responsabilidad | Registros con autor, fecha, fuente y versión auditables / registros | Consulta a BD / log de auditoría | 100 % | 90 % |
| M-15 | Confidencialidad | N.º de respuestas públicas que exponen identidad o ubicación del reportante | Pruebas de API \+ OWASP ZAP | 0 | 0 |
| M-16 | Resistencia | N.º de vulnerabilidades críticas o altas abiertas | OWASP ZAP, SonarQube, pip-audit | 0 | 0 críticas, ≤ 2 altas con plan |
| M-17 | Modificabilidad | (Esfuerzo real − estimado) / estimado al integrar el módulo comercial | Registro de horas en el tablero | ≤ ±20 % | ≤ ±30 % |
| M-18 | Modularidad | N.º de componentes del núcleo modificados y de cambios estructurales | Análisis de impacto \+ diff del repositorio | 0 cambios estructurales | 0 (componentes modificados registrados) |
| M-19 | Capacidad de prueba | % de líneas y ramas cubiertas | coverage.py (pytest \--cov) \+ SonarQube | Dominio ≥ 90 %, total ≥ 80 % | Dominio ≥ 80 %, total ≥ 70 % |
| M-20 | Analizabilidad | Rating de mantenibilidad y ratio de deuda técnica | SonarQube | A, deuda ≤ 3 % | B, deuda ≤ 5 % |
| M-21 | Disponibilidad | Tiempo disponible / tiempo total del periodo | Monitor de uptime \+ /healthz/ | ≥ 99,5 % | ≥ 99 % |
| M-22 | Tolerancia a fallos | Registros sincronizados / registros hechos sin conexión | Prueba simulando pérdida de red | 100 % | ≥ 98 % |
| D-01 | Actualidad | Tiempo hasta que el precio anterior deja de mostrarse como vigente | Prueba automatizada con marca de tiempo | ≤ 1 min | ≤ 5 min |
| D-02 | Actualidad | Precios vigentes dentro de la ventana / precios mostrados como vigentes | Consulta a BD | 100 % | 100 % |
| D-03 | Credibilidad | Precios con nivel de confianza y advertencia / mostrados | Pruebas de interfaz y API | 100 % | 100 % |
| D-04 | Exactitud | Precios de la muestra que coinciden con el verificado en tienda / muestra | Verificación en campo | ≥ 95 % | ≥ 90 % |
| D-05 | Consistencia | Productos duplicados / productos del catálogo | Script de detección de duplicados (regla son\_posibles\_duplicados) | ≤ 1 % | ≤ 3 % |
| D-06 | Completitud | Registros con producto, presentación, unidad, establecimiento, fecha y fuente / total | Consulta a BD \+ validaciones | 100 % | 100 % |

*Nota.* M \= métrica de calidad del producto (ISO/IEC 25023); D \= métrica de calidad de datos (ISO/IEC 25024).

# **Estrategia de Pruebas** {#estrategia-de-pruebas}

## **Niveles de Prueba** {#niveles-de-prueba}

La Tabla 7 relaciona cada nivel de prueba con lo que verifica, la técnica y herramienta empleadas, las métricas que alimenta y el corte en que se ejecuta.  
**Tabla 7**  
*Niveles de Prueba, Técnicas y Métricas Asociadas*

| Nivel | Qué verifica | Técnica y herramienta | Métricas | Corte |
| ----- | ----- | ----- | ----- | ----- |
| Unitarias (TDD) | Reglas de dominio: normalización por unidad, vigencia, confianza, orden neutral, detección de duplicados del catálogo y (corte 3\) promociones. | Ciclo rojo → verde → refactorización con pytest; sin base de datos. | M-05, M-06, M-19, D-05 | 2 y 3 |
| Integración | Servicios, API y base de datos: autenticación, idempotencia, invalidación de caché, privacidad. | pytest-django con PostgreSQL en CI; Postman/Newman para contrato OpenAPI. | M-13, M-14, M-15, M-22, D-01 | 2 y 3 |
| Sistema | Flujos de extremo a extremo: registrar, comparar, denunciar, moderar. | Casos derivados de la matriz de trazabilidad. | M-07 | 2 y 3 |
| Usabilidad | Registro ≤ 15 s, errores de usuario, aprendibilidad. | Prueba con al menos 5 usuarios reales (meta para el corte 3\) con red 3G simulada; cronómetro; cuestionario SUS. | M-01, M-02, M-04 | 2 y 3 |
| Accesibilidad | WCAG 2.2 AA. | axe DevTools, Lighthouse, WAVE \+ navegación por teclado y lector de pantalla. | M-03 | 2 y 3 |
| Análisis estático | Formato PEP 8, errores probables, vulnerabilidades, code smells, complejidad, deuda técnica. | Ruff en cada commit y en el CI; SonarQube por corte. | M-16, M-20 | 2 y 3 |
| Carga | 500 concurrentes en quincena. | k6 con umbrales p95 \< 2 s y errores \< 1 %. | M-08, M-09, M-10 | 3 |
| Seguridad | Vulnerabilidades y exposición de datos. | OWASP ZAP (DAST), SonarQube (SAST), pip-audit de dependencias. | M-15, M-16 | 3 |
| Calidad de datos | Integridad, duplicados, exactitud. | Dataset sembrado de reportes falsos; script de duplicados; muestra de campo. | M-11, M-12, D-04, D-05 | 3 |

*Nota.* Las pruebas unitarias siguen el ciclo de TDD descrito por Beck (2003).

## **Criterios de Entrada y Salida** {#criterios-de-entrada-y-salida}

* **Entrada a integración:** pruebas unitarias en verde y análisis estático sin hallazgos bloqueantes.  
* **Salida** todas las métricas en su valor mínimo o superior; las que no lo alcancen tienen incidencia abierta con plan de corrección.  
* **Bloqueo de integración (CI):** el pipeline falla si Ruff reporta errores, si el formato no cumple PEP 8 (ruff format \--check), si faltan migraciones o si la cobertura total baja de 70 %.

## **Gestión de Incidencias** {#gestión-de-incidencias}

Cada incidencia se registra en el tablero del repositorio con ID, métrica afectada, severidad (crítica, alta, media, baja), evidencia, responsable y estado. Las críticas bloquean el cierre del corte. Los hallazgos del análisis estático y su tratamiento se presentan en el informe de TDD y análisis estático.

# **Aseguramiento del Proceso** {#aseguramiento-del-proceso}

La Tabla 8 describe las prácticas con las que el equipo asegura la calidad del proceso y la evidencia que deja cada una.  
**Tabla 8**  
*Prácticas de Aseguramiento del Proceso*

| Práctica | Descripción | Evidencia |
| ----- | ----- | ----- |
| Control de versiones | Repositorio Git privado; ramas por funcionalidad; integración a *develop* y *main* por pull request. | Historial de commits y PR por integrante. |
| Revisión de código | Todo PR revisado por otro integrante con la lista de chequeo ISO 25010 de la plantilla. | Comentarios y aprobaciones en los PR. |
| Integración continua | GitHub Actions ejecuta lint, formato, verificación de migraciones, pruebas y cobertura. | Ejecuciones del pipeline. |
| TDD | Las reglas de dominio se escriben con prueba primero; los commits se marcan \[rojo\], \[verde\] y refactor. | Commits secuenciales prueba → código → refactor. |
| Definición de terminado | Historia con pruebas en verde, revisión aprobada, documentación y ADR actualizados. | Tablero del proyecto. |
| Uso de IA | Declarado en cada PR y en los commits (línea Co-Authored-By); | Plantilla de PR e historial. |

*Nota.* PR \= pull request; ADR \= registro de decisión de arquitectura.

# **Cronograma de Calidad por Corte** {#cronograma-de-calidad-por-corte}

La Tabla 9 distribuye las actividades de calidad en los tres cortes del semestre.  
**Tabla 9**  
*Actividades de Calidad por Corte*

| Corte | Actividades de calidad |
| ----- | ----- |
| 1 | Modelo de calidad, priorización, métricas, umbrales, estrategia de pruebas, requisitos y matriz de trazabilidad. |
| 2 | TDD de reglas de negocio; análisis estático y cobertura; prototipo y prueba de usabilidad (EC-01); estimación del cambio (base de M-17). |
| 3 | Pruebas de integración, sistema, carga y seguridad; evaluación ISO/IEC 25040 del producto y 25012 de los datos; reflexión sobre el proceso (ISO/IEC 330xx o CMMI) y plan de mejora. |

*Nota.* Cronograma sujeto a las fechas de entrega del curso.

# **Roles** {#roles}

La Tabla 10 asigna los roles de calidad entre los integrantes del equipo.  
**Tabla 10**  
*Roles y Responsabilidades del Equipo*

| Rol | Responsabilidad | Integrante |
| ----- | ----- | ----- |
| Líder de calidad | Mantiene este plan, la matriz de trazabilidad y el registro de incidencias; informe de TDD y análisis estático (SonarQube). | Xiomara Ocampo Hurtado |
| Responsable de desarrollo, pruebas automatizadas y despliegue | Implementación del núcleo con TDD, CI, cobertura, pruebas de integración y carga, despliegue reproducible. | Juan Manuel Rodríguez |
| Responsable de usabilidad y accesibilidad | Prototipo, prueba con usuarios (EC-01) y auditoría WCAG 2.2 AA. | María Luisa Londoño Moncada |
| Responsable de arquitectura y requisitos | Documentación C4 y ADR, encuesta y entrevistas a consumidores y tenderos, benchmarking y validación de requisitos. | Derly Elena Quejada |

*Nota.* Todos los integrantes revisan PR de otro compañero y escriben con TDD las reglas de negocio que implementen.

# **Conclusiones** {#conclusiones}

La adopción de ISO/IEC 25010:2023, complementada con ISO/IEC 25012 e ISO/IEC 25040, permite cubrir en un solo marco la seguridad, la accesibilidad y la calidad de los datos, aspectos que los modelos clásicos no contemplan o no desglosan en subcaracterísticas medibles.  
La priorización muestra que el valor del producto depende sobre todo de la adecuación funcional, la capacidad de interacción, la seguridad, la eficiencia de desempeño y la mantenibilidad. Las 28 métricas definidas convierten esas prioridades en valores verificables, cada uno con un objetivo y un mínimo de aceptación.  
La combinación de aseguramiento (revisión de código, integración continua y TDD) y control (pruebas por niveles, análisis estático y medición) le da al equipo evidencia para decidir, si el producto cumple o si debe abrirse una incidencia.

# **Referencias Bibliográficas** {#referencias-bibliográficas}

Beck, K. (2003). *Test-driven development: By example*. Addison-Wesley.  
Boehm, B. W., Brown, J. R., Kaspar, H., Lipow, M., MacLeod, G. J., & Merritt, M. J. (1978). *Characteristics of software quality*. North-Holland.  
Grady, R. B., & Caswell, D. L. (1987). *Software metrics: Establishing a company-wide program*. Prentice Hall.  
International Organization for Standardization. (2008). *Software engineering — Software product Quality Requirements and Evaluation (SQuaRE) — Data quality model* (Norma ISO/IEC 25012:2008).  
International Organization for Standardization. (2023). *Systems and software engineering — Systems and software Quality Requirements and Evaluation (SQuaRE) — Product quality model* (Norma ISO/IEC 25010:2023).  
International Organization for Standardization. (2024). *Systems and software engineering — Systems and software Quality Requirements and Evaluation (SQuaRE) — Quality evaluation framework* (Norma ISO/IEC 25040:2024).  
McCall, J. A., Richards, P. K., & Walters, G. F. (1977). *Factors in software quality* (Informe técnico RADC-TR-77-369). Rome Air Development Center.  
Piattini, M., García, F. O., García Rodríguez de Guzmán, I., & Pino, F. J. (2020). *Calidad de sistemas de información* (5.ª ed.). RA-MA.  
World Wide Web Consortium. (2023). *Web Content Accessibility Guidelines (WCAG) 2.2*. https\://www\.w3.org/TR/WCAG22/