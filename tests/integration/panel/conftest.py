"""Datos y sesiones por rol para las pruebas del panel (/panel/)."""

import re
from decimal import Decimal

import pytest

from apps.catalogo.domain.duplicados import normalizar_nombre
from apps.catalogo.models import Categoria, Marca, Presentacion, Producto
from apps.establecimientos.models import Establecimiento


@pytest.fixture
def crear_usuario(django_user_model):
    def crear(rol="reportante", username=None, **extra):
        return django_user_model.objects.create_user(
            username=username or f"u_{rol}",
            password="x-clave-1234",
            rol=rol,
            acepto_tratamiento_datos=True,
            **extra,
        )

    return crear


@pytest.fixture
def entrar(client, crear_usuario):
    """entrar("editor_catalogo") → (client, usuario) con la sesión iniciada."""

    def _entrar(rol, **extra):
        usuario = crear_usuario(rol, **extra)
        client.force_login(usuario)
        return client, usuario

    return _entrar


@pytest.fixture
def datos(db):
    granos = Categoria.objects.create(nombre="Granos")
    diana = Marca.objects.create(nombre="Diana")
    arroz = Producto.objects.create(
        nombre="Arroz blanco",
        nombre_normalizado=normalizar_nombre("Arroz blanco"),
        marca=diana,
        categoria=granos,
    )
    p500 = Presentacion.objects.create(producto=arroz, cantidad=Decimal(500), unidad="g")
    tienda = Establecimiento.objects.create(
        nombre="Tienda Doña Rosa", tipo="tienda", direccion="Cra 14 # 10-20", barrio="Centro"
    )
    return {"granos": granos, "diana": diana, "arroz": arroz, "p500": p500, "tienda": tienda}


def referencias_rotas(html: str) -> list[str]:
    """IDs citados por aria-describedby/labelledby/controls que no existen en la página."""
    ids = set(re.findall(r'\bid="([^"]+)"', html))
    citados = re.findall(r'aria-(?:describedby|labelledby|controls)="([^"]+)"', html)
    return sorted({ref for grupo in citados for ref in grupo.split()} - ids)


def controles_sin_etiqueta(html: str) -> list[str]:
    """IDs de input/select/textarea visibles sin <label for> ni aria-label (WCAG 1.3.1, 4.1.2)."""
    etiquetados = set(re.findall(r'<label[^>]*\bfor="([^"]+)"', html))
    faltan = []
    for control in re.findall(r"<(?:input|select|textarea)\b[^>]*>", html):
        if re.search(r'type="(hidden|submit)"', control) or "aria-label=" in control:
            continue
        ident = re.search(r'\bid="([^"]+)"', control)
        if not ident or ident.group(1) not in etiquetados:
            faltan.append(ident.group(1) if ident else control[:60])
    return faltan
