"""Departamentos del catálogo: grupos amplios de categorías (como en un supermercado). Python puro.

Las categorías son específicas («Arroz», «Crema dental»); los departamentos las agrupan para que la
portada y los filtros hablen como la gente: Mercado, Frutas y verduras, Salud y belleza… Un
supermercado grande tiene farmacia y belleza; una tienda de barrio, a lo sumo una crema. El orden de
los departamentos es fijo y no depende de ningún criterio comercial.
"""

import re
import unicodedata
from dataclasses import dataclass

VALOR_DEFECTO = "otros"


@dataclass(frozen=True)
class Grupo:
    valor: str
    etiqueta: str
    icono: str  # id del sprite


GRUPOS: tuple[Grupo, ...] = (
    Grupo("mercado", "Mercado", "i-g-canasta"),
    Grupo("frutas_verduras", "Frutas y verduras", "i-g-hoja"),
    Grupo("carnes_pescado", "Carnes y pescado", "i-cat-pescado"),
    Grupo("lacteos_huevos", "Lácteos y huevos", "i-cat-lacteo"),
    Grupo("bebidas", "Bebidas", "i-g-bebida"),
    Grupo("aseo_hogar", "Aseo del hogar", "i-cat-aseo"),
    Grupo("salud_belleza", "Salud y belleza", "i-g-salud"),
    Grupo("otros", "Otros", "i-cat-generico"),
)
_POR_VALOR = {g.valor: g for g in GRUPOS}

# Se evalúan en orden: lo más específico primero (la «crema dental» no es un lácteo, la «pasta
# dental» no es una pasta, el «jabón de ropa» es aseo y el «jabón» a secas es cuidado personal).
_REGLAS: tuple[tuple[str, str], ...] = (
    ("lacteos_huevos", r"\b(leche|huevos?|quesos?|yogur\w*|mantequilla|kumis|lacteos?)\b"),
    (
        "aseo_hogar",
        r"\b(detergentes?|lavaplatos|lavavajillas|suavizantes?|cloro|desinfectantes?|limpi\w*|"
        r"papel higienico|servilletas?|esponjas?|ambientador\w*|insecticidas?|escobas?|traperos?|"
        r"jabon(es)? (de|para) (ropa|loza|platos|barra))\b",
    ),
    (
        "salud_belleza",
        r"\b(dental|cepillos?|shampoo|champu|acondicionador|desodorantes?|cremas?|lociones?|"
        r"protector\w*|maquillaje|belleza|personal|medicament\w*|farmac\w*|analgesic\w*|"
        r"vitaminas?|jarabes?|panales?|afeitar|jabon(es)?|salud)\b",
    ),
    (
        "bebidas",
        r"\b(gaseosas?|jugos?|aguas?|cervezas?|bebidas?|te|maltas?|refrescos?|energizantes?)\b",
    ),
    (
        "carnes_pescado",
        r"\b(carnes?|pollo|pescados?|cerdo|res|embutidos?|salchichas?|jamon|chorizo|tocino|mariscos?)\b",
    ),
    (
        "frutas_verduras",
        r"\b(frutas?|verduras?|hortalizas?|tomates?|cebollas?|papas?|platanos?|bananos?|mango|"
        r"aguacates?|limon(es)?|zanahorias?|lechugas?|yucas?|naranjas?|manzanas?|moras?|fresas?|"
        r"pinas?)\b",
    ),
    (
        "mercado",
        r"\b(arroz|aceites?|azucar|panela|pastas?|cafe|chocolate\w*|atun|harinas?|sal|lentejas?|"
        r"frijol\w*|garbanzos?|cereal\w*|galletas?|snacks?|salsas?|conservas?|enlatados?|avena|"
        r"granos?|sardinas?|miel|mermeladas?|pan|despensa|mercado)\b",
    ),
)


def _plano(texto: str) -> str:
    base = unicodedata.normalize("NFKD", (texto or "").lower())
    sin_tildes = "".join(c for c in base if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", sin_tildes)).strip()


def grupo_sugerido(nombre_categoria: str) -> str:
    """El departamento que le corresponde a una categoría, por su nombre («otros» si no se sabe)."""
    plano = _plano(nombre_categoria)
    for valor, patron in _REGLAS:
        if re.search(patron, plano):
            return valor
    return VALOR_DEFECTO


def grupo_por_valor(valor: str) -> Grupo | None:
    return _POR_VALOR.get(valor)
