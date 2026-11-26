# ADR-0032: Departamentos amplios sobre las categorías del catálogo

- **Estado:** Propuesto
- **Fecha:** 2026-11-26
- **Autores:** Equipo; redactado con apoyo de IA
- **Escenarios de calidad afectados:** EC-01 (encontrar rápido), EC-06 (neutralidad)
- **Métricas que lo verifican:** M-01, M-03, M-06

## Contexto
Las categorías del catálogo son específicas («Arroz», «Café», «Crema dental»). Como accesos de la
portada eran demasiado estrechas y no reflejaban cómo se compra: un supermercado grande (Éxito,
Carulla) tiene frutas y verduras, carnes, farmacia y belleza; una tienda de barrio vende sobre todo
mercado, aseo y, a lo sumo, una crema. La portada necesita grupos amplios que se entiendan de un
vistazo.

## Alternativas consideradas
| Alternativa | A favor | En contra |
|---|---|---|
| Seguir con las categorías como accesos | Sin cambios | Demasiado específicas; la lista crece y ya no cabe |
| Mapear por nombre solo en el código, sin guardar nada | Sin migración | Una categoría nueva del panel cae en «otros» y no se puede corregir |
| **Campo `grupo` en la categoría, con sugerencia automática por nombre** | Editable en el panel; una categoría nueva se ubica sola; el filtro es una consulta simple | Una migración con datos; hay que mantener la regla de nombres |
| Una tabla `Departamento` aparte | Departamentos editables | Complejidad que hoy no hace falta (8 grupos estables) |

## Decisión
- `Categoria.grupo` (TextChoices, restricción `categoria_grupo_valido` en la base). Ocho
  departamentos: **Mercado, Frutas y verduras, Carnes y pescado, Lácteos y huevos, Bebidas, Aseo del
  hogar, Salud y belleza, Otros**.
- La regla `grupo_sugerido(nombre)` vive en `catalogo/domain/grupos.py` (Python puro, probada): la usan
  la migración 0011 (asigna las categorías existentes), la semilla y el panel (si el editor deja el
  departamento en «automático»). El departamento elegido a mano siempre gana.
- **Portada:** muestra los departamentos que tienen al menos un precio publicado, en un **orden fijo**
  (el de la lista de arriba), más «Más categorías». El orden no depende de la actividad ni de ningún
  atributo comercial.
- **Listado:** `/productos/?grupo=…` y un filtro «Departamento». Un valor desconocido se ignora.
- «Frutas y verduras» es un solo departamento (como en los supermercados); si hace falta separarlas,
  basta una categoría por cada una y cambiar el departamento en el panel.

## Consecuencias
- (+) La portada habla como la gente y no crece con el catálogo.
- (+) Una tienda de barrio no ve departamentos vacíos (no hay precios de farmacia): solo aparecen los
  que tienen datos.
- (−) La regla por nombre puede equivocarse con categorías ambiguas; por eso el panel permite
  corregirla.
- Migración 0011: agrega la columna, asigna los datos y luego exige la restricción; es reversible
  (la reversa solo quita la columna).

## Verificación
Pruebas unitarias de la regla (casos del catálogo actual y de supermercados grandes, tildes y
ambigüedades como «pasta dental»), de la migración con datos, del panel, de la portada y del filtro.
