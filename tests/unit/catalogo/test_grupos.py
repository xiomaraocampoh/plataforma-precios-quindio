"""Departamentos de la portada: grupos amplios de categorías (Mercado, Salud y belleza…)."""

import pytest

from apps.catalogo.domain.grupos import GRUPOS, VALOR_DEFECTO, grupo_por_valor, grupo_sugerido

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("categoria", "grupo"),
    [
        # lo que ya existe en el catálogo
        ("Arroz", "mercado"),
        ("Aceite", "mercado"),
        ("Azúcar", "mercado"),
        ("Panela", "mercado"),
        ("Pastas", "mercado"),
        ("Café", "mercado"),
        ("Atún", "mercado"),
        ("Chocolate de mesa", "mercado"),
        ("Leche", "lacteos_huevos"),
        ("Huevos", "lacteos_huevos"),
        ("Detergente", "aseo_hogar"),
        ("Papel higiénico", "aseo_hogar"),
        ("Crema dental", "salud_belleza"),
        ("Jabón", "salud_belleza"),
        # lo que traen los supermercados grandes
        ("Frutas y verduras", "frutas_verduras"),
        ("Verduras", "frutas_verduras"),
        ("Frutas", "frutas_verduras"),
        ("Tomate", "frutas_verduras"),
        ("Carnes", "carnes_pescado"),
        ("Pollo", "carnes_pescado"),
        ("Pescado", "carnes_pescado"),
        ("Embutidos", "carnes_pescado"),
        ("Queso", "lacteos_huevos"),
        ("Crema de leche", "lacteos_huevos"),
        ("Yogur", "lacteos_huevos"),
        ("Gaseosas", "bebidas"),
        ("Jugos", "bebidas"),
        ("Agua", "bebidas"),
        ("Cerveza", "bebidas"),
        ("Medicamentos", "salud_belleza"),
        ("Fármacos", "salud_belleza"),
        ("Farmacia", "salud_belleza"),
        ("Cremas corporales", "salud_belleza"),
        ("Shampoo", "salud_belleza"),
        ("Desodorantes", "salud_belleza"),
        ("Belleza y cuidado personal", "salud_belleza"),
        ("Jabón de ropa", "aseo_hogar"),
        ("Lavaplatos", "aseo_hogar"),
        ("Suavizante", "aseo_hogar"),
        ("Cloro y desinfectantes", "aseo_hogar"),
        ("Harinas", "mercado"),
        ("Lentejas y fríjoles", "mercado"),
        ("Galletas", "mercado"),
    ],
)
def test_cada_categoria_cae_en_su_departamento(categoria, grupo):
    assert grupo_sugerido(categoria) == grupo


def test_lo_desconocido_va_a_otros():
    assert grupo_sugerido("Artículos varios") == VALOR_DEFECTO == "otros"
    assert grupo_sugerido("") == "otros"


def test_no_distingue_tildes_ni_mayusculas():
    assert grupo_sugerido("CAFÉ") == grupo_sugerido("cafe") == "mercado"
    assert grupo_sugerido("fármacos") == "salud_belleza"


def test_la_crema_dental_no_es_un_lacteo_ni_la_pasta_dental_es_una_pasta():
    assert grupo_sugerido("Pasta dental") == "salud_belleza"
    assert grupo_sugerido("Crema dental") == "salud_belleza"


def test_los_departamentos_son_unicos_ordenados_y_otros_va_al_final():
    valores = [g.valor for g in GRUPOS]
    assert len(valores) == len(set(valores)) and valores[0] == "mercado" and valores[-1] == "otros"
    for g in GRUPOS:
        assert g.etiqueta.strip() and g.icono.startswith("i-"), g.valor


def test_busqueda_por_valor():
    assert grupo_por_valor("salud_belleza").etiqueta == "Salud y belleza"
    assert grupo_por_valor("no-existe") is None
