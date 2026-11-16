# Auditoría WCAG 2.2 AA · 2026-11-16

Rama `feat/cierre-corte-2`. Prueba PUX-02 del plan de calidad, métrica **M-03** (inclusividad).
Auditoría y correcciones asistidas por Claude Code; el equipo debe revisarlas y poder defenderlas.

**Pantallas:**
- inicio y búsqueda (con sugerencias abiertas)
- comparación de un producto
- registro de precio (formulario, errores y confirmación por HTMX)
- registro de cuenta (formulario y errores)
- ingreso (formulario y errores)

Cada estado se auditó en tema claro y en tema oscuro.

## Resultado

| Indicador | Antes | Después |
|---|---|---|
| Lighthouse, accesibilidad: inicio | 96 | **100** |
| Lighthouse: comparación | 100 | **100** |
| Lighthouse: registro de precio | 100 | **100** |
| Lighthouse: registro de cuenta | 96 | **100** |
| Lighthouse: ingreso | 96 | **100** |
| axe-core 4.14 (wcag2a/aa, 21a/aa, 22aa): nodos con violación en 20 estados | **12** (color-contrast 4, link-in-text-block 8) | **0** |
| Pares de color de `app.css` que no cumplen | 9 | **0** |
| Fallos A/AA confirmados (automáticos + manuales) | 7 (4 de nivel A) | **0** |
| **M-03** = criterios cumplidos / aplicables | 34 / 43 = **79,1 %** | 43 / 43 = **100 %** |

M-03 «antes» cuenta como no cumplidos los 7 fallos confirmados y los 2 criterios que no se habían
verificado (2.4.3 y 4.1.3). Hay 12 criterios de los 55 de WCAG 2.2 A + AA que no aplican: no hay
audio, video, atajos de una tecla, arrastre, contenido al pasar el puntero, ayuda consistente ni
transacciones legales o financieras.

## Fallos encontrados y corrección

| Criterio | Nivel | Dónde | Cómo se detectó | Commit |
|---|---|---|---|---|
| 1.4.3 Contraste mínimo | AA | Botón claro en el bloque oscuro de inicio: `#6cb6ff` sobre blanco, 2,14:1 | axe, Lighthouse | `933f592` |
| 1.4.1 Uso del color | A | «Crear cuenta» e «Ingresar» dentro de una frase, solo por color (1,14:1 frente al texto) | axe, Lighthouse, cálculo | `4d2a681` |
| 1.4.11 Contraste no textual | AA | Bordes de campos y buscador: 1,68:1 en claro y 1,85:1 en oscuro | cálculo de tokens | `bb98a7d` |
| 1.3.1 Información y relaciones | A | `aria-describedby` de Django apuntaba a ayudas y errores sin `id` (cuenta y precio) | HTML renderizado; axe solo lo marca como «revisar» | `e0e748a` |
| 3.3.1 Identificación de errores | A | El ingreso con campos vacíos se recargaba sin ningún mensaje | revisión manual | `e0e748a` |
| 2.2.2 Pausar, detener, ocultar | A | Palabra rotatoria infinita; comparación recargada cada 60 s sin control | prueba de teclado | `5ab53ac`, `dc0f940` |
| 1.4.12 Espaciado del texto | AA | La palabra rotatoria se recortaba («comp\|») | inyección del espaciado de 1.4.12 | `5ab53ac` |
| 4.1.3 Mensajes de estado / 2.4.3 Orden del foco | AA / A | `#avisos` sin uso; foco perdido en `<body>` tras HTMX | revisión manual | `dc0f940` |
| Esc en el buscador | — | Esc no cerraba la lista; mostraba un mensaje confuso | prueba de teclado | `0efe489` |

Las correcciones de plantillas tienen pruebas en `tests/integration/test_accesibilidad.py`. Las de
formularios primero fallaron (`pruebas-formularios-rojo.txt`) y luego pasaron
(`pruebas-formularios-verde.txt`).

## Revisión manual (después)

| Comprobación | Resultado |
|---|---|
| Navegación con Tab por las 5 pantallas | Orden lógico; todos los controles alcanzables; sin trampas |
| Foco visible | Contorno de 3 px en todos los elementos enfocados (0 sin foco visible) |
| «Saltar al contenido» | Es el primer Tab; con Enter el foco pasa a `<main>` y el siguiente Tab al contenido |
| Buscador | Tab baja a la sugerencia, Enter abre la comparación y Esc vacía y oculta la lista |
| Etiquetas de formularios | Todos los campos con `<label>`; errores y ayudas asociados por `aria-describedby` |
| Foco y anuncios tras HTMX | Con errores, el foco va al primer campo inválido; al confirmar, al título, que se anuncia en `#avisos`; «Registrar otro», al primer campo (`despues/foco-y-anuncios-htmx.json`) |
| Pausas (2.2.2) | La rotación del titular dura < 5 s y se detiene sola (ya no hay botón «Pausar animación»; antes duraba para siempre y lo exigía); «Pausar actualización» detiene la recarga y lo anuncia |
| Objetivos ≥ 24 px | Todos; «Crear cuenta» (85×20) está dentro de una frase (excepción *inline* de 2.5.8) |
| Reflujo a 320 px | Sin scroll horizontal en las 5 pantallas |
| Espaciado de texto (1.4.12) | Ningún texto recortado |
| Contraste | `antes/contraste.md` y `despues/contraste.md` (claro, oscuro y hero) |

## Problemas que quedan

1. **Sin prueba con lector de pantalla.** Los anuncios y el foco se verificaron en el DOM con Chrome,
   no con NVDA ni TalkBack. Conviene confirmarlos con una persona antes de la entrega.
2. **Semántica de la lista de resultados (observación de 1.3.1).** La tarjeta de resumen y la del
   criterio están dentro del `<ol>` de precios, así que el lector cuenta 5 elementos para 3 tiendas.
   No impide el uso.
3. **Usabilidad, fuera de WCAG:** las presentaciones se muestran como «5E+2 g» por
   `Decimal.normalize()` en `apps/catalogo/models.py`. Afecta a M-02.
4. axe deja como «revisar» el contraste del texto sobre la foto del hero y los degradados, porque no
   puede medir fondos de imagen. El cálculo con los colores sólidos de respaldo cumple.
5. Solo se auditaron las 5 pantallas pedidas; el admin de Django no está incluido.

## Cómo repetir la auditoría

Requisitos:
- Node 20 o superior y Chrome instalado.
- `npm install lighthouse@12 axe-core@4` en una carpeta de herramientas fuera del repositorio.
- La aplicación corriendo en `http://127.0.0.1:8000` con `cargar_demo`.
- Un archivo con la cookie de sesión `sessionid=<valor>` de un usuario de prueba.

```bash
node herramientas/auditar-a11y.mjs <ruta absoluta de salida> <archivo de cookie>
node herramientas/foco-htmx.mjs <ruta absoluta de salida> <archivo de cookie> <carpeta de perfil temporal>
python herramientas/contraste_css.py static/css/app.css > contraste.md
```

Copia los scripts de `herramientas/` a la carpeta donde instalaste los paquetes, porque buscan
`node_modules` junto a ellos.

Las rutas de salida y de perfil deben ser **absolutas**: con rutas relativas, Chrome en Windows no
arranca el modo de depuración.

## Archivos

- `antes/` y `despues/`:
  - `lighthouse/*.report.html`: informe completo por pantalla.
  - `lighthouse/resumen.json`: puntajes.
  - `axe/<estado>-<tema>.json`: violaciones y «revisar».
  - `axe/resumen.json`
  - `teclado.json`
  - `contraste.md`
- `despues/foco-y-anuncios-htmx.json`
- `pruebas-formularios-rojo.txt` y `pruebas-formularios-verde.txt`
