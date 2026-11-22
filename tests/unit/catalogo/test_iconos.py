"""Ícono de cada categoría (prototipo visual): una regla pura, sin Django (EC-06, M-03).

El ícono solo ayuda a reconocer el producto de un vistazo: es el mismo tamaño y estilo para todos,
no depende de la marca ni de la tienda y nunca entra en el orden de la comparación.
"""

import pytest

from apps.catalogo.domain.iconos import ICONO_GENERICO, ICONOS, icono_de_categoria

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("categoria", "icono"),
    [
        ("Arroz", "i-cat-grano"),
        ("Leche", "i-cat-lacteo"),
        ("Huevos", "i-cat-huevo"),
        ("Café", "i-cat-cafe"),
        ("Chocolate de mesa", "i-cat-cafe"),
        ("Aceite", "i-cat-aceite"),
        ("Pastas", "i-cat-pasta"),
        ("Azúcar", "i-cat-dulce"),
        ("Panela", "i-cat-dulce"),
        ("Atún", "i-cat-pescado"),
        ("Jabón", "i-cat-aseo"),
        ("Detergente", "i-cat-aseo"),
        ("Crema dental", "i-cat-aseo"),
        ("Papel higiénico", "i-cat-aseo"),
    ],
)
def test_cada_categoria_del_catalogo_tiene_su_icono(categoria, icono):
    assert icono_de_categoria(categoria) == icono


@pytest.mark.parametrize("escrito", ["ARROZ", "arroz", "  Arroz  ", "Árroz"])
def test_no_importan_mayusculas_tildes_ni_espacios(escrito):
    assert icono_de_categoria(escrito) == "i-cat-grano"


def test_reconoce_la_palabra_dentro_de_un_nombre_mas_largo():
    assert icono_de_categoria("Arroz y granos secos") == "i-cat-grano"
    assert icono_de_categoria("Lácteos y derivados") == "i-cat-lacteo"


def test_una_categoria_desconocida_usa_el_icono_generico():
    assert icono_de_categoria("Ferretería") == ICONO_GENERICO


@pytest.mark.parametrize("vacio", ["", "   ", None])
def test_sin_nombre_usa_el_icono_generico(vacio):
    assert icono_de_categoria(vacio) == ICONO_GENERICO


def test_no_confunde_palabras_cortas_con_fragmentos_de_otras():
    # «té» no debe activarse por «tomate»; «sal» no por «salchicha»
    assert icono_de_categoria("Tomate") == ICONO_GENERICO
    assert icono_de_categoria("Salchichas") == ICONO_GENERICO


def test_todo_icono_devuelto_esta_en_la_lista_de_iconos_del_sprite():
    for categoria in ("Arroz", "Leche", "Ferretería", "Jabón", "", "Atún"):
        assert icono_de_categoria(categoria) in ICONOS
    assert ICONO_GENERICO in ICONOS
