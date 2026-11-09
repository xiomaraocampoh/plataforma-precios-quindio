**Especificación de Requisitos y Calidad de Datos: Plataforma Colaborativa de Comparación de Precios (Armenia, Quindío)**

María Luisa Londoño Moncada  
Xiomara Ocampo Hurtado  
Juan Manuel Rodríguez  
Derly Elena Quejada

Profesor: Ing. Rubén Darío Díaz Bautista

Corporación Universitaria Alexander von Humboldt  
Facultad de Ingenierías y Ciencias Básicas  
Ingeniería de Software  
2026

**Resumen**  
Este documento especifica los requisitos del núcleo de una plataforma colaborativa para comparar precios de la canasta familiar en Armenia y el Quindío y define la calidad de sus datos. Se presentan 22 requisitos funcionales agrupados en cuentas, catálogo, establecimientos, registro colaborativo de precios, consulta y comparación, y moderación, cada uno con actor, prioridad MoSCoW y criterio de aceptación; y 18 requisitos no funcionales vinculados a las características de ISO/IEC 25010:2023 y a las métricas del plan de calidad. Los ocho escenarios de calidad se refinan en el formato de seis partes de Bass, Clements y Kazman. Para la calidad de los datos se identifican siete características críticas de ISO/IEC 25012, con su mecanismo y su medida, y se definen reglas de calidad sobre las entidades principales. Por último, una matriz de trazabilidad relaciona cada requisito con su escenario, su métrica y la prueba que lo verifica, y se declaran los supuestos y restricciones.  
***Palabras clave*****:** requisitos, trazabilidad, ISO/IEC 25012, escenarios, datos.  
**Tabla de Contenido**

[Introducción	5](#introducción)

[Justificación	6](#justificación)

[Objetivos	7](#objetivos)

[Objetivo General	7](#objetivo-general)

[Objetivos Específicos	7](#objetivos-específicos)

[Requisitos Funcionales del Núcleo	8](#requisitos-funcionales)

[Requisitos No Funcionales	10](#heading=h.pa9kk47ghmak)

[Escenarios de Calidad Refinados	12](#escenarios-de-calidad-refinados)

[Calidad de los Datos (ISO/IEC 25012\)	14](#calidad-de-los-datos-\(iso/iec-25012\))

[Características Críticas	14](#características-críticas)

[Reglas de Calidad sobre las Entidades Principales	15](#reglas-de-calidad-sobre-las-entidades-principales)

[Matriz de Trazabilidad	16](#heading=h.lylaczxjelxq)

[Supuestos y Restricciones	18](#supuestos-y-restricciones)

[Conclusiones	19](#conclusiones)

[Recomendaciones	20](#heading=h.yu80ydrlwdm0)

[Referencias Bibliográficas	21](#referencias-bibliográficas)

**Lista de Tablas**  
[**Tabla 1** *Requisitos Funcionales del Núcleo*	9](#tabla-1-requisitos-funcionales-del-núcleo)  
[**Tabla 2** *Requisitos No Funcionales*	11](#tabla-2-requisitos-no-funcionales)  
[**Tabla 3** *Escenarios de Calidad en Formato de Seis Partes*	13](#tabla-3-escenarios-de-calidad-en-formato-de-seis-partes)  
[**Tabla 4** *Características Críticas de Calidad de los Datos*	14](#tabla-4-características-críticas-de-calidad-de-los-datos)  
[**Tabla 5** *Reglas de Calidad sobre las Entidades Principales*	15](#tabla-5-reglas-de-calidad-sobre-las-entidades-principales)  
[**Tabla 6** *Matriz de Trazabilidad entre Requisitos, Escenarios, Métricas y Pruebas*	16](#tabla-6-matriz-de-trazabilidad-entre-requisitos,-escenarios,-métricas-y-pruebas)

# **Introducción** {#introducción}

Este documento en su versión 1.1, incorpora la regla de duplicados D-05 y la trazabilidad a las pruebas existentes. Donde se especifican los requisitos del **núcleo**: catálogo de productos, registro colaborativo de precios, directorio de establecimientos y comparación, además de cuentas y moderación, que el núcleo necesita para operar. El módulo comercial se especifica en el análisis de impacto del corte 2\. La prioridad sigue el esquema MoSCoW: **M** debe, **S** debería, **C** podría.

**Declaración de uso de inteligencia artificial.** Este documento se redactó con apoyo de un asistente de IA generativa (Claude, Anthropic) y fue revisado por el equipo.

# **Justificación** {#justificación}

El valor de la plataforma depende tanto del software como de los datos que aportan los usuarios. Un requisito ambiguo o un dato desactualizado, duplicado o falso llevan al consumidor a una mala decisión de compra, por eso es necesario especificar con criterios de aceptación verificables qué debe hacer el sistema y qué calidad deben tener sus datos (International Organization for Standardization \[ISO\], 2008).  
La matriz de trazabilidad conecta cada requisito con un escenario, una métrica y una prueba, lo que permite comprobar en cada corte que lo especificado se construyó y se verificó, y detectar requisitos sin prueba o pruebas sin requisito.

# **Objetivos** {#objetivos}

## **Objetivo General** {#objetivo-general}

Especificar los requisitos funcionales y no funcionales del núcleo de la plataforma y la calidad de sus datos, con trazabilidad hacia los escenarios, las métricas y las pruebas que los verifican.

## **Objetivos Específicos** {#objetivos-específicos}

* Especificar los requisitos funcionales del núcleo con actor, prioridad y criterio de aceptación.  
* Definir los requisitos no funcionales vinculados a las características de ISO/IEC 25010:2023 y a las métricas del plan de calidad.  
* Refinar los escenarios de calidad en el formato de seis partes.  
* Identificar las características críticas de calidad de datos según ISO/IEC 25012 y definir reglas sobre las entidades principales.  
* Construir la matriz de trazabilidad entre requisitos, escenarios, métricas y pruebas.

# **Requisitos Funcionales**  {#requisitos-funcionales}

La Tabla 1 presenta los requisitos funcionales agrupados por módulo.  
**Tabla 1**  
*Requisitos Funcionales del Núcleo*

| ID | Requisito | Actor | Prioridad | Criterio de aceptación |
| ----- | ----- | ----- | ----- | ----- |
| **Cuentas** |  |  |  |  |
| RF-01 | El sistema debe permitir crear una cuenta con autorización expresa de tratamiento de datos. | Reportante | M | Sin aceptar la política no se crea la cuenta; se guarda la fecha de aceptación. |
| RF-02 | El sistema debe permitir iniciar y cerrar sesión, y recuperar la contraseña por correo. | Reportante, Moderador | M | Acceso solo con credenciales válidas; enlace de recuperación de un solo uso. |
| RF-03 | El sistema debe permitir consultar, actualizar y solicitar la supresión de los datos personales. | Reportante | S | Atiende consultas y reclamos conforme a la Ley 1581 de 2012\. |
| RF-04 | El sistema debe permitir buscar productos, ver sus presentaciones y consultar y comparar precios, incluidos los de referencia, sin crear ni iniciar sesión en una cuenta.  | Consumidor | M | Búsqueda, detalle y comparación funcionan sin iniciar sesión; registrar, denunciar o sugerir pide iniciar sesión.   |
| **Catálogo** |  |  |  |  |
| RF-05 | El sistema debe permitir buscar productos por nombre o código de barras. | Todos | M | Sugerencias desde 2 caracteres, sin distinguir mayúsculas ni tildes. |
| RF-06 | El sistema debe permitir ver un producto con sus presentaciones (cantidad y unidad). | Todos | M | Cada presentación muestra cantidad y unidad normalizadas. |
| RF-07 | El sistema debe permitir solicitar el alta de un producto o presentación inexistente, con aviso de posibles duplicados. | Reportante | S | La solicitud queda pendiente de moderación; se muestran productos similares (similitud de nombre normalizado ≥ 0,85) antes de enviar. |
| RF-08 | El sistema debe permitir cargar precios de referencia desde SIPSA (DANE). | Sistema | C | Carga diaria; los precios se marcan con fuente “sipsa” y se muestran como referencia. |
| **Establecimientos** |  |  |  |  |
| RF-09 | El sistema debe permitir consultar el directorio de establecimientos filtrando por municipio, barrio y tipo. | Todos | M | Muestra nombre, tipo, dirección y barrio. |
| RF-19 | El sistema debe permitir ver la ubicación de un establecimiento en un mapa. | Todos | S | Enlace a mapa con las coordenadas registradas. |
| RF-11 | El sistema debe permitir sugerir un establecimiento nuevo. | Reportante | M |  |
| **Registro colaborativo de precios** |  |  |  |  |
| RF-12 | El sistema debe permitir registrar el precio de una presentación en un establecimiento. | Reportante | M | Tres datos: establecimiento, presentación y precio; precio \> 0\. |
| RF-13 | El sistema debe permitir guardar un registro hecho sin conexión y reenviarlo al recuperarla, sin duplicarlo. | Reportante | S | Un reenvío con el mismo identificador de cliente no crea un segundo registro. |
| RF-14 | El sistema debe permitir confirmar con un toque que un precio existente sigue igual. | Reportante | C | La confirmación renueva la vigencia y suma al nivel de confianza. |
| **Consulta y comparación** |  |  |  |  |
| RF-15 | El sistema debe permitir comparar el precio vigente de un producto entre establecimientos. | Consumidor | M | Solo se muestran precios dentro de su ventana de vigencia. |
| RF-16 | El sistema debe permitir calcular y mostrar el precio por unidad de medida (\$/kg, \$/L, \$/und). | Consumidor | M | Solo se comparan presentaciones de la misma magnitud. |
| RF-17 | El sistema debe permitir mostrar el criterio de orden y ordenar los resultados solo por él. | Consumidor | M | Menor precio por unidad; empate por nombre del establecimiento. |
| RF-18 | El sistema debe permitir mostrar para cada precio su fuente, antigüedad y nivel de confianza. | Consumidor | M | Los precios de confianza baja llevan advertencia visible. |
| RF-19 | El sistema debe permitir filtrar la comparación por municipio y barrio. | Consumidor | S | El filtro no altera el criterio de orden. |
| **Moderación** |  |  |  |  |
| RF-20 | El sistema debe permitir denunciar un precio dudoso indicando el motivo. | Reportante | M | Una denuncia por usuario y reporte. |
| RF-21 | El sistema debe permitir revisar reportes en revisión y denuncias; aprobar o rechazar. | Moderador | M | Cada decisión queda registrada con moderador y fecha. |
| RF-22 | El sistema debe permitir suspender cuentas con comportamiento abusivo. | Moderador | S | Una cuenta suspendida no puede registrar; sus reportes quedan auditables. |

*Nota.* M \= debe; S \= debería; C \= podría (MoSCoW).  
**Requisitos No Funcionales**  
La Tabla 2 presenta los requisitos no funcionales con la característica de ISO/IEC 25010:2023 (ISO, 2023\) a la que pertenecen y la métrica del plan de calidad que los verifica.  
**Tabla 2**  
*Requisitos No Funcionales*

| ID | Característica (subcaracterística) | Requisito | Métrica |
| ----- | ----- | ----- | ----- |
| RNF-01 | Capacidad de interacción (operabilidad) | El registro de un precio se completa en ≤ 15 s con red 3G. | M-01 |
| RNF-02 | Capacidad de interacción (protección contra errores) | El reportante elige presentación y unidad de listas; el sistema rechaza precios no positivos y fechas futuras. | M-02 |
| RNF-03 | Capacidad de interacción (inclusividad) | Las interfaces cumplen WCAG 2.2 nivel AA. | M-03 |
| RNF-04 | Capacidad de interacción (aprendibilidad) | Un usuario nuevo registra y consulta sin ayuda. | M-04 |
| RNF-05 | Adecuación funcional (corrección) | Las reglas de normalización, vigencia y orden se verifican con pruebas automatizadas. | M-05, M-06 |
| RNF-06 | Eficiencia de desempeño | Con 500 usuarios concurrentes, p95 de la comparación ≤ 2 s y errores ≤ 1 %. | M-08, M-09, M-10 |
| RNF-07 | Seguridad (autenticidad) | Toda operación de escritura exige autenticación. | M-13 |
| RNF-08 | Seguridad (responsabilidad) | Cada precio guarda autor, fecha, fuente y estado. | M-14 |
| RNF-09 | Seguridad (confidencialidad) | Ninguna respuesta pública expone identidad ni ubicación del reportante. | M-15 |
| RNF-10 | Seguridad (resistencia) | Límite de 30 registros por hora por usuario; 0 vulnerabilidades críticas. | M-16 |
| RNF-11 | Seguridad (integridad) | Los reportes anómalos no se muestran como vigentes sin advertencia. | M-11, M-12 |
| RNF-12 | Mantenibilidad (modificabilidad, modularidad) | El módulo comercial se integra sin cambios estructurales al núcleo. | M-17, M-18 |
| RNF-13 | Mantenibilidad (capacidad de prueba, analizabilidad) | Cobertura del dominio ≥ 90 %; rating de mantenibilidad A. | M-19, M-20 |
| RNF-14 | Fiabilidad (disponibilidad) | Disponibilidad ≥ 99,5 % en el periodo de evaluación. | M-21 |
| RNF-15 | Fiabilidad (tolerancia a fallos) | Los registros hechos sin conexión se sincronizan sin pérdida. | M-22 |
| RNF-16 | Flexibilidad (adaptabilidad) | Funciona en las dos últimas versiones de Chrome, Safari y Firefox móviles. | Pruebas de sistema |
| RNF-17 | Legal | Política de tratamiento de datos, autorización del titular y canal de consulta y reclamo (Ley 1581 de 2012, Decreto 1074 de 2015); términos de uso con aceptación electrónica (Ley 527 de 1999). | Revisión documental |
| RNF-18 | Legal y ética | La información de promociones cumple la Ley 1480 de 2011; la plataforma no facilita coordinación de precios entre competidores (Leyes 155 de 1959 y 1340 de 2009). | Revisión documental |

*Nota.* Las métricas M corresponden al plan de aseguramiento de calidad . Leyes citadas: Congreso de la República de Colombia (1999, 2011, 2012).

# **Escenarios de Calidad Refinados** {#escenarios-de-calidad-refinados}

Los escenarios se expresan en el formato de seis partes de Bass et al. (2021). Las medidas son las del plan de calidad como valor mínimo  
. La Tabla 3 los presenta.  
**Tabla 3**  
*Escenarios de Calidad en Formato de Seis Partes*

| ID | Fuente | Estímulo | Artefacto | Entorno | Respuesta | Medida |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| EC-01 | Reportante | Registra el precio de un producto | Interfaz de registro | Dentro del establecimiento, red 3G | Registro completado con selección de catálogo y un campo numérico | ≥ 80 % en ≤ 15 s (objetivo 90 %) |
| EC-02 | Reportante o comercio | Cambia el precio de un producto | Comparación | Operación normal | El precio anterior deja de mostrarse como vigente | ≤ 5 min (objetivo ≤ 1 min) |
| EC-03 | Usuario o grupo malintencionado | Registra precios falsos de un establecimiento | Servicio de registro y comparación | Operación normal | Los anómalos quedan en revisión; los no confiables se muestran con advertencia | Detección ≥ 80 %; falsos positivos ≤ 10 % |
| EC-04 | 500 consumidores | Consultan comparaciones en simultáneo | Aplicación completa | Fin de semana de quincena | Responde sin errores ni degradación | p95 ≤ 2 s; error ≤ 1 % |
| EC-05 | Docente (nuevo requisito) | Se incorpora el módulo comercial | Código y arquitectura | Tiempo de desarrollo, corte 2 y 3 | Cambio concentrado en un módulo nuevo y puntos de extensión | 0 cambios estructurales; desviación ≤ ±30 % |
| EC-06 | Comercio | Publica una promoción | Comparación | Operación normal | Orden según criterio declarado; promoción distinguida | 100 % de los casos |
| EC-07 | Tercero | Consulta la API pública buscando al reportante | API REST | Operación normal | Ninguna respuesta incluye identidad ni ubicación | 0 exposiciones |
| EC-08 | Reportante | Pierde la señal al enviar un registro | Interfaz y servicio de registro | Conectividad intermitente | El registro se reenvía al recuperar la conexión, sin duplicarse | ≥ 98 % (objetivo 100 %) |

*Nota.* Formato de escenario de Bass et al. (2021).

# **Calidad de los Datos (ISO/IEC 25012\)** {#calidad-de-los-datos-(iso/iec-25012)}

## **Características Críticas** {#características-críticas}

La Tabla 4 identifica las características de calidad de datos críticas para la plataforma según ISO/IEC 25012 (ISO, 2008), con el mecanismo que las asegura y la medida que las verifica según ISO/IEC 25024 (ISO, 2015).  
**Tabla 4**  
*Características Críticas de Calidad de los Datos*

| Característica | Punto de vista | Por qué es crítica | Mecanismo | Medida |
| ----- | ----- | ----- | ----- | ----- |
| Actualidad | Inherente | Un precio viejo mostrado como vigente lleva a una mala decisión de compra. | Ventanas de vigencia; invalidación de caché al registrar. | D-01, D-02 |
| Credibilidad | Inherente | Fuentes con distinta confiabilidad, incluidos competidores. | Nivel de confianza, detección por mediana, moderación. | D-03, M-11, M-12 |
| Exactitud | Inherente | El precio registrado debe coincidir con el de la góndola. | Validaciones; confirmaciones de otros reportantes; muestra de campo. | D-04 |
| Consistencia | Inherente | Un producto duplicado divide la comparación. | Catálogo canónico; detección de duplicados. | D-05 |
| Completitud | Inherente | Un registro sin unidad o sin fecha no se puede comparar ni vencer. | Campos obligatorios en formulario y restricciones en BD. | D-06 |
| Trazabilidad | Inherente y dependiente del sistema | Moderar y atender reclamos de comercios exige saber quién y cuándo. | Autor, fuente, fecha y estado en cada reporte; registro de decisiones de moderación. | M-14 |
| Confidencialidad | Inherente y dependiente del sistema | Ubicación y actividad del reportante son datos personales. | Lista blanca en respuestas públicas; no se guarda geolocalización del reportante. | M-15 |

*Nota.* D \= métrica de calidad de datos; M \= métrica de calidad del producto.  
Las características de prioridad baja en este corte son precisión (los precios se expresan en pesos con dos decimales), comprensibilidad, conformidad, accesibilidad del dato, eficiencia, disponibilidad, portabilidad y recuperabilidad; se cubren indirectamente con requisitos del producto (RNF-14, RNF-15).

## **Reglas de Calidad sobre las Entidades Principales** {#reglas-de-calidad-sobre-las-entidades-principales}

La Tabla 5 define las reglas de calidad sobre los atributos de las entidades principales.  
**Tabla 5**  
*Reglas de Calidad sobre las Entidades Principales*

| Entidad | Atributo | Regla | Característica 25012 |
| ----- | ----- | ----- | ----- |
| Producto | nombre normalizado y su marca | Únicos en el catálogo (minúsculas, sin tildes salvo la ñ, sin puntuación ni espacios dobles); nombres con similitud ≥ 0,85 se marcan como posibles duplicados para el moderador. | Consistencia |
| Presentación | cantidad, unidad | Cantidad \> 0; unidad en {g, kg, ml, L, und}; combinación única por producto. | Exactitud, consistencia |
| Establecimiento | latitud, longitud, municipio | Coordenadas dentro del departamento del Quindío; municipio de una lista cerrada. | Exactitud, completitud |
| Reporte de precio | precio | \> 0, dos decimales; si se aleja más de 50 % de la mediana reciente, queda en revisión. | Exactitud, credibilidad |
| Reporte de precio | fecha de observación | No futura (tolerancia de 5 min); define la vigencia. | Actualidad |
| Reporte de precio | autor, fuente, estado | Obligatorios; el autor nunca se publica. | Trazabilidad, confidencialidad |
| Reporte de precio | id\_cliente | Único cuando existe. | Consistencia |
| Denuncia | reporte y denunciante | Una denuncia por usuario y reporte; resolución con moderador y fecha. | Trazabilidad |

*Nota.* Las reglas se aplican en formularios, serializers y restricciones de la base de datos.

# **Matriz de Trazabilidad**

La Tabla 6 presenta la matriz de trazabilidad.  
**Tabla 6**  
*Matriz de Trazabilidad entre Requisitos, Escenarios, Métricas y Pruebas*

| Requisito | Escenario | Métrica | Prueba |
| ----- | ----- | ----- | ----- |
| RF-01, RNF-17 | EC-07 | — | PS-01 Registro de cuenta sin autorización es rechazado |
| RF-04, RF-05 | — | M-07 | PS-02 Búsqueda y detalle de producto |
| RF-06 | — | D-05 | PU-05 Normalización de nombres y detección de duplicados; PS-03 Alta con aviso de duplicados |
| RF-11, RNF-02 | EC-01 | M-02, D-06 | PI-04 Precio cero es rechazado; PI-05 presentación inexistente devuelve 400 |
| RF-11, RNF-07 | — | M-13 | PI-01 Registrar exige autenticación |
| RF-11, RNF-08 | — | M-14 | PI-02 Reportante registra precio con autor y fecha |
| RF-12, RNF-15 | EC-08 | M-22 | PI-03 Reenvío con el mismo id\_cliente no duplica; PS-04 pérdida de red simulada |
| RF-11, RNF-01, RNF-04 | EC-01 | M-01, M-04 | PUX-01 Prueba con usuarios, red 3G |
| RF-15, RNF-05 | EC-02 | D-02 | PU-02 Vigencia (7 días, perecedero 3, oficial 30\) |
| RF-15 | EC-02 | D-01 | PI-06 Nuevo reporte invalida la caché |
| RF-16 | EC-06 | M-05 | PU-01 Normalización por unidad |
| RF-17 | EC-06 | M-06 | PU-04 Orden neutral; la promoción no altera el orden |
| RF-18, RNF-11 | EC-03 | D-03, M-11, M-12 | PU-03 Detección de anomalías y nivel de confianza; dataset sembrado |
| RF-15, RNF-09 | EC-07 | M-15 | PI-07 La respuesta pública no expone al reportante; PSeg-01 OWASP ZAP |
| RNF-10 | EC-03 | M-16 | PSeg-02 Límite de tasa; SonarQube y pip-audit |
| RNF-06 | EC-04 | M-08, M-09, M-10 | PC-01 k6 con 500 usuarios virtuales |
| RNF-03 | — | M-03 | PUX-02 Auditoría WCAG 2.2 AA |
| RF-20, RF-21, RF-22 | EC-03 | M-14 | PS-05 Flujo de denuncia y moderación |
| RNF-12 | EC-05 | M-17, M-18 | Análisis de impacto (corte 2\) y diff del repositorio (corte 3\) |
| RNF-13 | — | M-19, M-20 | Cobertura y SonarQube en CI |
| RNF-14 | — | M-21 | Monitor de uptime sobre /healthz/ |

*Nota.* Tipos de prueba: 

* **PU** unitaria (TDD, dominio),   
* **PI** integración (API \+ BD),   
* **PS** sistema,   
* **PUX** usabilidad,  
*  **PC** carga,   
* **PSeg** seguridad. 

# **Supuestos y Restricciones** {#supuestos-y-restricciones}

* Los primeros datos provienen de carga manual en establecimientos piloto y de SIPSA.  
* Las ventanas de vigencia se validan con las entrevistas a tenderos y la encuesta de google forms aplicada a stakeholders: [https\://forms.gle/2Dtk6NRiKve451EY8](https://forms.gle/2Dtk6NRiKve451EY8) .  
* La plataforma no es un sistema oficial de precios ni sustituye a las autoridades de protección al consumidor.

# **Conclusiones** {#conclusiones}

Los 22 requisitos funcionales y 18 no funcionales cubren el núcleo de la plataforma con criterios de aceptación verificables, y cada requisito no funcional queda ligado a una característica de ISO/IEC 25010:2023 y a una métrica del plan de calidad.  
La calidad de los datos se trata como un objeto propio: siete características críticas de ISO/IEC 25012 cuentan con un mecanismo que las asegura, una medida que las verifica y reglas concretas sobre las entidades principales.  
La matriz de trazabilidad muestra que las reglas de dominio ya tienen pruebas unitarias aprobadas y que las pruebas de integración, sistema, usabilidad, carga y seguridad restantes tienen un lugar definido en las siguientes enregas.

# **Referencias Bibliográficas** {#referencias-bibliográficas}

Bass, L., Clements, P., & Kazman, R. (2021). *Software architecture in practice* (4.ª ed.). Addison-Wesley.  
Congreso de la República de Colombia. (1999). *Ley 527 de 1999, por medio de la cual se define y reglamenta el acceso y uso de los mensajes de datos, del comercio electrónico y de las firmas digitales, y se establecen las entidades de certificación y se dictan otras disposiciones*.  
Congreso de la República de Colombia. (2011). *Ley 1480 de 2011, por medio de la cual se expide el Estatuto del Consumidor y se dictan otras disposiciones*.  
Congreso de la República de Colombia. (2012). *Ley 1581 de 2012, por la cual se dictan disposiciones generales para la protección de datos personales*.  
International Organization for Standardization. (2008). *Software engineering — Software product Quality Requirements and Evaluation (SQuaRE) — Data quality model* (Norma ISO/IEC 25012:2008).  
International Organization for Standardization. (2015). *Systems and software engineering — Systems and software Quality Requirements and Evaluation (SQuaRE) — Measurement of data quality* (Norma ISO/IEC 25024:2015).  
International Organization for Standardization. (2023). *Systems and software engineering — Systems and software Quality Requirements and Evaluation (SQuaRE) — Product quality model* (Norma ISO/IEC 25010:2023).