"""Foto de un producto: se procesa, se guarda en la BD y se sirve con caché (RF-06, EC-01, M-14).

La imagen que se guarda NO es el archivo subido: el servidor la reencodea a una miniatura WebP
cuadrada. Así se descarta cualquier contenido oculto (metadatos con la ubicación, código embebido)
y todas las fotos salen del mismo tamaño y forma (EC-06).
"""

from io import BytesIO

import pytest
from django.urls import reverse
from PIL import Image

from apps.catalogo import selectors, services
from apps.catalogo.domain.fotos import LADO_MINIATURA, FotoInvalidaError
from apps.catalogo.models import FotoProducto

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def _abrir(datos: bytes) -> Image.Image:
    return Image.open(BytesIO(datos))


# ───────────── Procesar ─────────────


def test_la_miniatura_es_webp_cuadrada_y_liviana(imagen):
    salida = services.preparar_foto(imagen(tamano=(1200, 800)))
    foto = _abrir(salida)
    assert foto.format == "WEBP"
    assert foto.size == (LADO_MINIATURA, LADO_MINIATURA)
    assert len(salida) < 60_000  # pocos KB en 3G


def test_una_foto_pequena_no_se_agranda_mas_de_lo_que_tiene(imagen):
    # 300 px de lado: se lleva a la miniatura estándar para que todas se vean del mismo tamaño
    assert _abrir(services.preparar_foto(imagen(tamano=(300, 300)))).size == (
        LADO_MINIATURA,
        LADO_MINIATURA,
    )


@pytest.mark.parametrize("formato", ["JPEG", "PNG", "WEBP"])
def test_acepta_jpg_png_y_webp(imagen, formato):
    assert _abrir(services.preparar_foto(imagen(formato=formato))).format == "WEBP"


def test_no_conserva_los_metadatos_de_la_camara(imagen):
    # Privacidad (Ley 1581): una foto de celular puede traer la ubicación en el EXIF
    original = imagen(exif=True)
    assert _abrir(original).getexif()  # la foto de prueba sí los trae
    assert not _abrir(services.preparar_foto(original)).getexif()


@pytest.mark.parametrize(
    "contenido", [b"", b"%PDF-1.4 no es una imagen", b"GIF89a....", b"<svg onload='x'/>"]
)
def test_rechaza_lo_que_no_es_una_imagen_valida(contenido):
    with pytest.raises(FotoInvalidaError):
        services.preparar_foto(contenido)


def test_rechaza_otros_formatos_de_imagen(imagen):
    with pytest.raises(FotoInvalidaError, match="JPG, PNG o WebP"):
        services.preparar_foto(imagen(formato="GIF"))


def test_rechaza_fotos_muy_pequenas(imagen):
    with pytest.raises(FotoInvalidaError, match="pequeña"):
        services.preparar_foto(imagen(tamano=(100, 100)))


# ───────────── Guardar y quitar ─────────────


def test_guardar_la_foto_deja_la_version_en_el_producto(arroz, imagen):
    prod, _, _ = arroz
    services.guardar_foto(prod, services.preparar_foto(imagen()))
    prod.refresh_from_db()
    assert len(prod.foto_version) == 12
    foto = FotoProducto.objects.get(producto=prod)
    assert foto.tipo_contenido == "image/webp" and foto.contenido[:4] == b"RIFF"


def test_cambiar_la_foto_reemplaza_la_anterior_y_cambia_la_version(arroz, imagen):
    prod, _, _ = arroz
    services.guardar_foto(prod, services.preparar_foto(imagen(color=(200, 0, 0))))
    primera = prod.foto_version
    services.guardar_foto(prod, services.preparar_foto(imagen(color=(0, 0, 200))))
    prod.refresh_from_db()
    assert FotoProducto.objects.filter(producto=prod).count() == 1
    assert prod.foto_version != primera  # la URL cambia: el navegador no usa la foto vieja


def test_la_misma_foto_da_la_misma_version(arroz, imagen):
    prod, _, _ = arroz
    miniatura = services.preparar_foto(imagen())
    services.guardar_foto(prod, miniatura)
    primera = prod.foto_version
    services.guardar_foto(prod, miniatura)
    assert prod.foto_version == primera


def test_quitar_la_foto_la_borra_y_limpia_la_version(arroz, imagen):
    prod, _, _ = arroz
    services.guardar_foto(prod, services.preparar_foto(imagen()))
    services.quitar_foto(prod)
    prod.refresh_from_db()
    assert prod.foto_version == "" and not FotoProducto.objects.exists()


def test_quitar_sin_foto_no_falla(arroz):
    services.quitar_foto(arroz[0])


def test_borrar_el_producto_borra_su_foto(arroz, imagen):
    prod, _, _ = arroz
    services.guardar_foto(prod, services.preparar_foto(imagen()))
    prod.delete()
    assert not FotoProducto.objects.exists()


def test_los_listados_nunca_cargan_los_bytes_de_la_foto():
    # Los bytes viven en otra tabla: listar productos no los trae (N+1 ni peso extra, EC-01)
    consulta = str(selectors.productos_publicos().query)
    assert "contenido" not in consulta and "fotoproducto" not in consulta


# ───────────── Servir la foto ─────────────


def _url(producto, **params):
    base = reverse("catalogo:foto", args=[producto.pk])
    return base + ("?" + "&".join(f"{k}={v}" for k, v in params.items()) if params else "")


def _con_foto(arroz, imagen):
    prod, _, _ = arroz
    services.guardar_foto(prod, services.preparar_foto(imagen()))
    prod.refresh_from_db()
    return prod


def test_la_foto_se_sirve_como_webp_sin_pedir_cuenta(client, arroz, imagen):
    prod = _con_foto(arroz, imagen)
    r = client.get(_url(prod))
    assert r.status_code == 200 and r["Content-Type"] == "image/webp"
    assert r.content == FotoProducto.objects.get(producto=prod).contenido


def test_con_la_version_correcta_el_navegador_la_guarda_un_ano(client, arroz, imagen):
    prod = _con_foto(arroz, imagen)
    r = client.get(_url(prod, v=prod.foto_version))
    assert "immutable" in r["Cache-Control"] and "max-age=31536000" in r["Cache-Control"]


def test_sin_version_la_cache_es_corta_para_no_dejar_fotos_viejas(client, arroz, imagen):
    prod = _con_foto(arroz, imagen)
    assert "immutable" not in client.get(_url(prod))["Cache-Control"]
    assert "immutable" not in client.get(_url(prod, v="otra"))["Cache-Control"]


def test_si_la_foto_no_cambio_responde_304_sin_cuerpo(client, arroz, imagen):
    prod = _con_foto(arroz, imagen)
    etag = client.get(_url(prod))["ETag"]
    r = client.get(_url(prod), HTTP_IF_NONE_MATCH=etag)
    assert r.status_code == 304 and r.content == b""


def test_sin_foto_o_con_producto_retirado_responde_404(client, arroz, imagen):
    prod, _, _ = arroz
    assert client.get(_url(prod)).status_code == 404  # no tiene foto
    prod = _con_foto(arroz, imagen)
    prod.activo = False
    prod.save()
    assert client.get(_url(prod)).status_code == 404  # retirado del catálogo público
    assert client.get(reverse("catalogo:foto", args=[999999])).status_code == 404


def test_la_foto_solo_se_pide_por_get(client, arroz, imagen):
    prod = _con_foto(arroz, imagen)
    assert client.post(_url(prod)).status_code == 405


def test_la_respuesta_no_depende_de_la_persona_ni_lleva_cookies(client, arroz, imagen, reportante):
    prod = _con_foto(arroz, imagen)
    client.force_login(reportante)
    r = client.get(_url(prod))
    assert "sessionid" not in r.cookies and "csrftoken" not in r.cookies  # cacheable por todos
