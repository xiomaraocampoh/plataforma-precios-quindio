# Protocolo de la prueba de usabilidad · Corte 2

Prueba **PUX-01** del plan de calidad. Escenario **EC-01** y métricas **M-01**, **M-02** y **M-04**,
con el cuestionario SUS como medida complementaria.

Responsable de usabilidad: María Luisa Londoño Moncada. Este kit no contiene resultados: se llena
durante las sesiones.

## 1. Objetivo

Comprobar con personas reales que:

- registrar un precio toma **15 s o menos** en conexión 3G (M-01);
- no se registra con la unidad, la presentación o el establecimiento equivocado (M-02);
- una persona nueva consulta y registra **sin ayuda** (M-04).

| Métrica | Fórmula | Mínimo | Objetivo |
|---|---|---|---|
| M-01 Operabilidad | registros de T2 completados en ≤ 15 s / intentos de T2 | ≥ 80 % | ≥ 90 % |
| M-02 Protección contra errores | registros de T2 con unidad, presentación o establecimiento equivocado / registros de T2 completados | ≤ 10 % | ≤ 5 % |
| M-04 Aprendibilidad | participantes que completan todas sus tareas sin pedir ayuda / participantes evaluados | ≥ 80 % | ≥ 90 % |
| SUS (complementaria) | promedio de los puntajes SUS (0 a 100) | ≥ 68 | ≥ 80 |

## 2. Participantes

- **Mínimo 5 consumidores** que compren el mercado en Armenia o en otro municipio del Quindío.
- Mayores de 18 años, con celular propio y sin relación con el desarrollo del proyecto: no pueden
  ser integrantes del equipo ni haber visto la plataforma antes.
- Busquen variedad: al menos una persona de 50 años o más, una que compre en tienda de barrio y otra
  que compre en supermercado.
- Cada participante se identifica solo con un código (P1, P2, …). No se anotan nombres, teléfonos ni
  direcciones en las plantillas.

## 3. Preparación

1. **Datos:** la aplicación corre con datos de demostración (`python manage.py cargar_demo`). Antes de
   cada sesión, revisa que «Arroz blanco» tenga precios vigentes en al menos tres establecimientos.
2. **Dispositivo:** idealmente el celular del participante, conectado a la red del equipo, o un
   computador con Chrome en modo dispositivo:
   - Chrome DevTools (F12) → *Toggle device toolbar* (Ctrl+Shift+M) → un celular de 390 px de ancho.
   - DevTools → **Network** → límite **Slow 3G**. En versiones recientes de Chrome el preajuste se
     llama «3G». Revisa que siga activo antes de cada tarea, porque se desactiva al cerrar DevTools.
3. **Cuentas:** el participante crea su propia cuenta en T3 y la usa en T2. Al terminar la jornada,
   el equipo puede borrar esas cuentas desde `/admin/`.
4. **Material:** cronómetro (o el del celular del moderador), `registro.csv` abierto, la hoja de
   [consentimiento](consentimiento.md) impresa o en pantalla, y `sus.md`.
5. **Roles:** una persona **modera**, es decir, lee el guion y no ayuda. Otra **observa y registra**:
   tiempos, errores y observaciones.

## 4. Consentimiento informado (Ley 1581 de 2012)

Se lee en voz alta y se pide aceptación verbal o firmada antes de empezar:

> Te invitamos a probar AhorraPues, una plataforma para comparar precios de la canasta familiar,
> creada como proyecto académico de la Corporación Universitaria Empresarial Alexander von
> Humboldt. Evaluamos la plataforma, no a ti: no hay respuestas buenas ni malas.
>
> La sesión dura unos 20 minutos. Anotaremos el tiempo de cada tarea, si la completas y tus
> comentarios. No grabaremos tu cara ni tu voz, y no guardaremos tu nombre: te identificaremos con
> un código. Los datos se usan solo para el informe del curso y se borran al terminar el semestre.
>
> Participar es voluntario y puedes retirarte en cualquier momento sin dar explicaciones. ¿Aceptas
> participar?

Anota en `observaciones` de la primera fila del participante: «consentimiento: sí».

## 5. Guion del moderador

**Introducción (2 min):**

> Gracias por venir. Te voy a pedir cuatro tareas cortas en la plataforma. Por favor, piensa en voz
> alta: cuéntame qué buscas y qué esperas que pase. Si te quedas sin saber qué hacer, intenta lo que
> harías normalmente. Si de verdad no puedes seguir, dime «necesito ayuda» y te orientaré, pero eso
> lo anotaremos. ¿Listo?

**Reglas para el moderador:**

- Lee cada tarea textualmente y no muestres dónde está nada.
- **Pidió ayuda = s** si la persona dice que necesita ayuda o si, tras **60 s sin avanzar**, el
  moderador tiene que dar una pista. Después de la pista, la tarea puede completarse, pero queda con
  ayuda.
- **Completó = n** si la persona abandona o si, a los **3 minutos**, la tarea no está terminada.
- No corrijas errores durante la tarea. Anótalos.

**Orden de las tareas:** T1 → T3 → T2 → T4. Registrar un precio exige cuenta, por eso T3 va antes
que T2.

### T1 · Buscar y comparar

> «Quieres comprar arroz. Busca “arroz” y mira en qué lugares está y a qué precio.»

- **Inicio:** la página de inicio está cargada.
- **Fin:** la persona está en la comparación de un producto de arroz y dice en voz alta dónde está
  más barato.

### T3 · Crear cuenta

> «Para poder aportar precios necesitas una cuenta. Crea una.»

- **Inicio:** página de inicio.
- **Fin:** aparece «Tu cuenta quedó creada».
- Anota en `observaciones` si dudó con la autorización de datos.

### T2 · Registrar un precio (EC-01, M-01, M-02)

Antes de empezar, el observador elige y anota una combinación concreta, por ejemplo: **«Estás en
Supermercado Central y ves Arroz blanco de 1 kg a $4.900»**.

> «Estás en [establecimiento] y ves [producto y presentación] a [precio]. Registra ese precio.»

- **Inicio del cronómetro:** el formulario «Registrar un precio» está en pantalla y cargado.
- **Fin del cronómetro:** aparece «Listo, tu precio ya está publicado» o «quedó en revisión».
- **Error:** al terminar, el observador compara lo registrado con lo indicado y anota en `error`:
  `unidad` (por ejemplo, 500 g en vez de 1 kg), `presentacion` (otra presentación del mismo
  producto o un producto equivocado), `establecimiento` o `ninguno`. Si hay varios errores, sepáralos
  con `;`.

### T4 · Identificar el más barato por unidad y su confianza

> «En la comparación del arroz, dime cuál es la opción más barata **por kilo** y qué tan confiable es
> ese precio.»

- **Fin:** la persona dice el establecimiento y el nivel de confiabilidad (alta, media o baja).
- **Completó = s** solo si ambos datos son correctos.

**Cierre (5 min):** entrega `sus.md` para responder solo. Luego pregunta:

1. ¿Qué fue lo más difícil?
2. ¿Usarías esto antes de ir a comprar? ¿Por qué?
3. ¿Qué cambiarías primero?

Anota las respuestas en `observaciones`.

## 6. Registro y cálculo

1. Una fila por participante y tarea en [`registro.csv`](registro.csv): tiempo en segundos (decimales
   con punto), `completo` y `pidio_ayuda` con `s`/`n`, `error` y `observaciones`. Las filas vacías se
   ignoran.
2. Las respuestas del SUS van en [`sus.csv`](sus.csv): una fila por participante, ítems `p1` a `p10`
   del 1 al 5.
3. Calcula las métricas desde la raíz del repositorio:

   ```bash
   python scripts/calcular_usabilidad.py docs/calidad/usabilidad/registro.csv docs/calidad/usabilidad/sus.csv
   ```

4. Guarda la salida en `docs/calidad/evidencias/<fecha>/usabilidad.txt` junto con los CSV llenos, y
   comenta en el informe los hallazgos cualitativos de `observaciones`.

## 7. Riesgos conocidos antes de la prueba

- **M-01:** un solo selector lista todas las presentaciones de todos los productos, y el
  establecimiento hay que elegirlo de nuevo en cada registro. Si cuesta tiempo, anótalo en
  `observaciones`: es un hallazgo, no un error de la prueba.
- **Servicio en la nube:** si el despliegue estaba dormido, la primera carga es lenta. Ábrelo antes de
  cada sesión para que no afecte el cronómetro de T2.
