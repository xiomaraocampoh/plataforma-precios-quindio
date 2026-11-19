"""Ícono de cada categoría del catálogo (prototipo visual para reconocer un producto de un vistazo).

Capa de dominio: Python puro, sin Django. Solo decide QUÉ ícono corresponde a un nombre de
categoría; los dibujos viven en el sprite de la plantilla (`templates/partials/_iconos.html`).

Neutralidad (EC-06): el ícono depende solo de la categoría, es igual de grande y del mismo estilo
para todos y nunca participa en el orden de la comparación.
"""

from .duplicados import normalizar_nombre

ICONO_GENERICO = "i-cat-generico"

# (ícono, palabras que lo activan). La primera regla que coincide gana.
_REGLAS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "i-cat-aseo",
        (
            "jabon",
            "detergente",
            "dental",
            "higienico",
            "champu",
            "shampoo",
            "aseo",
            "cloro",
            "suavizante",
            "desodorante",
            "limpia",
        ),
    ),
    (
        "i-cat-grano",
        ("arroz", "frijol", "lenteja", "garbanzo", "maiz", "avena", "harina", "cereal", "grano"),
    ),
    ("i-cat-lacteo", ("leche", "queso", "yogur", "yogurt", "mantequilla", "lacteo", "kumis")),
    ("i-cat-huevo", ("huevo",)),
    ("i-cat-cafe", ("cafe", "chocolate", "te", "aromatica", "infusion")),
    ("i-cat-aceite", ("aceite", "grasa")),
    ("i-cat-pasta", ("pasta", "spaghetti", "espagueti", "fideo", "macarron")),
    ("i-cat-dulce", ("azucar", "panela", "miel", "dulce", "sal", "endulzante")),
    ("i-cat-pescado", ("atun", "sardina", "pescado", "trucha")),
)

ICONOS: frozenset[str] = frozenset({icono for icono, _ in _REGLAS} | {ICONO_GENERICO})

# Con 4 letras o más, «lacteo» también activa «lacteos»; las cortas («te», «sal») solo coinciden
# exactas: así «tomate» no es «té» ni «salchicha» es «sal».
_MIN_PARA_PREFIJO = 4


def _coincide(palabra: str, clave: str) -> bool:
    if palabra == clave:
        return True
    return len(clave) >= _MIN_PARA_PREFIJO and palabra.startswith(clave)


def icono_de_categoria(nombre: str | None) -> str:
    """Id del ícono de la categoría (siempre uno de ICONOS; genérico si no se reconoce)."""
    palabras = normalizar_nombre(nombre or "").split()
    for icono, claves in _REGLAS:
        if any(_coincide(p, c) for p in palabras for c in claves):
            return icono
    return ICONO_GENERICO
