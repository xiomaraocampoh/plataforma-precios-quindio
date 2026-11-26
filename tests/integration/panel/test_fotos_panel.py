"""Foto del producto en el panel: la sube el Editor de catálogo y queda auditada (ADR-019, M-14)."""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.administracion.models import RegistroAuditoria
from apps.catalogo import services
from apps.catalogo.models import FotoProducto

pytestmark = pytest.mark.integration


def _datos(producto, **extra):
    """Formulario de edición del producto (sin tocar sus presentaciones)."""
    filas = list(producto.presentaciones.all())
    datos = {
        "nombre": producto.nombre,
        "marca": producto.marca_id or "",
        "categoria": producto.categoria_id,
        "presentaciones-TOTAL_FORMS": str(len(filas)),
        "presentaciones-INITIAL_FORMS": str(len(filas)),
        "presentaciones-MIN_NUM_FORMS": "1",
        "presentaciones-MAX_NUM_FORMS": "1000",
    }
    for i, p in enumerate(filas):
        datos.update(
            {
                f"presentaciones-{i}-id": p.pk,
                f"presentaciones-{i}-producto": producto.pk,
                f"presentaciones-{i}-cantidad": str(p.cantidad.normalize()),
                f"presentaciones-{i}-unidad": p.unidad,
                f"presentaciones-{i}-codigo_barras": p.codigo_barras or "",
                f"presentaciones-{i}-activa": "on",
            }
        )
    datos.update(extra)
    return datos


def _archivo(contenido: bytes, nombre="arroz.jpg", tipo="image/jpeg"):
    return SimpleUploadedFile(nombre, contenido, content_type=tipo)


def _editar(client, datos, producto):
    return client.post(reverse("panel:editar", args=["productos", producto.pk]), datos)


def test_el_editor_de_catalogo_sube_la_foto_de_un_producto(entrar, datos, imagen):
    client, _ = entrar("editor_catalogo")
    arroz = datos["arroz"]
    r = _editar(client, _datos(arroz, foto=_archivo(imagen())), arroz)
    assert r.status_code == 302, r.content.decode()[:600]
    arroz.refresh_from_db()
    assert len(arroz.foto_version) == 12 and FotoProducto.objects.filter(producto=arroz).exists()


def test_subir_la_foto_queda_en_la_auditoria(entrar, datos, imagen):
    client, editor = entrar("editor_catalogo")
    arroz = datos["arroz"]
    _editar(client, _datos(arroz, foto=_archivo(imagen())), arroz)
    arroz.refresh_from_db()
    registro = RegistroAuditoria.objects.get()
    assert (registro.actor, registro.accion, registro.entidad) == (editor, "editar", "producto")
    assert registro.cambios["foto"][0] == "sin foto"
    assert registro.cambios["foto"][1] == arroz.foto_version


def test_una_foto_invalida_se_rechaza_con_un_mensaje_claro_y_sin_auditar(entrar, datos):
    client, _ = entrar("editor_catalogo")
    arroz = datos["arroz"]
    r = _editar(client, _datos(arroz, foto=_archivo(b"%PDF-1.4", "x.jpg")), arroz)
    assert r.status_code == 200
    assert "JPG, PNG o WebP" in r.content.decode()
    assert not FotoProducto.objects.exists() and not RegistroAuditoria.objects.exists()


def test_se_puede_quitar_la_foto_actual(entrar, datos, imagen):
    client, _ = entrar("editor_catalogo")
    arroz = datos["arroz"]
    services.guardar_foto(arroz, services.preparar_foto(imagen()))
    r = _editar(client, _datos(arroz, quitar_foto="on"), arroz)
    assert r.status_code == 302
    arroz.refresh_from_db()
    assert arroz.foto_version == "" and not FotoProducto.objects.exists()
    assert RegistroAuditoria.objects.get().cambios["foto"][1] == "sin foto"


def test_guardar_sin_tocar_la_foto_la_conserva(entrar, datos, imagen):
    client, _ = entrar("editor_catalogo")
    arroz = datos["arroz"]
    services.guardar_foto(arroz, services.preparar_foto(imagen()))
    version = arroz.foto_version
    _editar(client, _datos(arroz, nombre="Arroz blanco extra"), arroz)
    arroz.refresh_from_db()
    assert arroz.foto_version == version and FotoProducto.objects.filter(producto=arroz).exists()


def test_el_formulario_permite_subir_archivos_y_muestra_la_foto_actual(entrar, datos, imagen):
    client, _ = entrar("editor_catalogo")
    arroz = datos["arroz"]
    url = reverse("panel:editar", args=["productos", arroz.pk])
    html = client.get(url).content.decode()
    assert 'enctype="multipart/form-data"' in html
    assert 'type="file"' in html and 'accept="image/jpeg,image/png,image/webp"' in html
    assert "Quitar la foto actual" not in html  # no hay foto que quitar todavía
    services.guardar_foto(arroz, services.preparar_foto(imagen()))
    arroz.refresh_from_db()
    html = client.get(url).content.decode()
    assert reverse("catalogo:foto", args=[arroz.pk]) in html and "Quitar la foto actual" in html


def test_sin_permiso_de_editar_productos_no_se_puede_subir_la_foto(entrar, datos, imagen):
    client, _ = entrar("reportante")
    arroz = datos["arroz"]
    r = _editar(client, _datos(arroz, foto=_archivo(imagen())), arroz)
    assert r.status_code == 403
    assert not FotoProducto.objects.exists()


def test_tambien_se_puede_subir_la_foto_al_crear_un_producto(entrar, datos, imagen):
    from apps.catalogo.models import Producto

    client, _ = entrar("editor_catalogo")
    nuevo = {
        "nombre": "Leche entera",
        "marca": "",
        "categoria": datos["granos"].pk,
        "presentaciones-TOTAL_FORMS": "1",
        "presentaciones-INITIAL_FORMS": "0",
        "presentaciones-MIN_NUM_FORMS": "1",
        "presentaciones-MAX_NUM_FORMS": "1000",
        "presentaciones-0-cantidad": "1",
        "presentaciones-0-unidad": "L",
        "presentaciones-0-codigo_barras": "",
        "presentaciones-0-activa": "on",
        "foto": _archivo(imagen()),
    }
    r = client.post(reverse("panel:nuevo", args=["productos"]), nuevo)
    assert r.status_code == 302, r.content.decode()[:600]
    assert Producto.objects.get(nombre="Leche entera").foto_version


def test_el_editor_escribe_la_descripcion_del_producto(entrar, datos):
    client, _ = entrar("editor_catalogo")
    arroz = datos["arroz"]
    r = _editar(client, _datos(arroz, descripcion="Grano largo."), arroz)
    assert r.status_code == 302
    arroz.refresh_from_db()
    assert arroz.descripcion == "Grano largo."


def test_el_campo_de_foto_admite_arrastrar_pegar_y_buscar(entrar, datos):
    """El campo sigue siendo un input de archivo (buscar) y se mejora con arrastrar y pegar."""
    client, _ = entrar("editor_catalogo")
    arroz = datos["arroz"]
    html = client.get(reverse("panel:editar", args=["productos", arroz.pk])).content.decode()
    assert 'type="file"' in html and "data-zona-foto" in html
    assert "js/zona-foto.js" in html
    # explica las tres formas sin depender del color ni del script
    assert "arrastra" in html.lower() and "Ctrl+V" in html
