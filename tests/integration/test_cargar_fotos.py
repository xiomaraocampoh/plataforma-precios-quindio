"""Comando `cargar_fotos`: importa una carpeta de imágenes a los productos (ADR-0024).

El nombre del archivo dice a qué producto va: su código de barras, su id o su nombre
(con la marca). Lo que no encaja o no es una imagen válida se informa y no detiene el resto.
"""

from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command

from apps.catalogo.models import FotoProducto, Marca, Presentacion, Producto

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def carpeta(tmp_path, imagen):
    def poner(nombre: str, contenido: bytes | None = None, formato="JPEG") -> Path:
        ruta = tmp_path / nombre
        ruta.write_bytes(contenido if contenido is not None else imagen(formato=formato))
        return ruta

    poner.dir = tmp_path
    return poner


def _correr(carpeta, *extra) -> str:
    salida = StringIO()
    call_command("cargar_fotos", str(carpeta.dir), *extra, stdout=salida)
    return salida.getvalue()


def _con_codigo(arroz, codigo="7702001001234"):
    _, p500, _ = arroz
    p500.codigo_barras = codigo
    p500.save()


def test_la_foto_se_asigna_por_codigo_de_barras(arroz, carpeta):
    _con_codigo(arroz)
    carpeta("7702001001234.jpg")
    salida = _correr(carpeta)
    assert FotoProducto.objects.get().producto == arroz[0]
    assert "1 foto" in salida


def test_la_foto_se_asigna_por_id_del_producto(arroz, carpeta):
    carpeta(f"{arroz[0].pk}.png", formato="PNG")
    _correr(carpeta)
    assert FotoProducto.objects.get().producto == arroz[0]


def test_la_foto_se_asigna_por_nombre_con_marca(db, arroz, carpeta):
    prod = arroz[0]
    prod.marca = Marca.objects.create(nombre="Diana")
    prod.save()
    carpeta("Arroz-blanco_Diana.webp", formato="WEBP")
    _correr(carpeta)
    assert FotoProducto.objects.get().producto == prod


def test_un_nombre_ambiguo_no_se_adivina(db, arroz, carpeta):
    # «Arroz blanco» existe con dos marcas: sin la marca no se sabe cuál es
    cat = arroz[0].categoria
    Producto.objects.create(
        nombre="Arroz blanco", marca=Marca.objects.create(nombre="Roa"), categoria=cat
    )
    Producto.objects.create(
        nombre="Arroz blanco", marca=Marca.objects.create(nombre="Diana"), categoria=cat
    )
    carpeta("arroz-blanco.jpg")
    salida = _correr(carpeta)
    assert not FotoProducto.objects.exists()
    assert "arroz-blanco.jpg" in salida and "ambig" in salida.lower()


def test_los_archivos_que_no_encajan_o_no_son_imagen_se_informan_y_no_detienen_el_resto(
    arroz, carpeta
):
    _con_codigo(arroz)
    carpeta("7702001001234.jpg")
    carpeta("999.jpg")  # no corresponde a ningún producto
    carpeta(f"{arroz[2].pk + 999}.jpg", b"%PDF-1.4 no es imagen")
    carpeta("notas.txt", b"hola")  # no es una imagen: se ignora en silencio
    salida = _correr(carpeta)
    assert FotoProducto.objects.count() == 1
    assert "999.jpg" in salida and "sin producto" in salida.lower()


def test_con_dry_run_no_guarda_nada_pero_dice_que_haria(arroz, carpeta):
    _con_codigo(arroz)
    carpeta("7702001001234.jpg")
    salida = _correr(carpeta, "--dry-run")
    assert not FotoProducto.objects.exists()
    assert "simulación" in salida.lower() and "1 foto" in salida


def test_no_pisa_una_foto_existente_salvo_con_reemplazar(arroz, carpeta, imagen):
    from apps.catalogo import services

    _con_codigo(arroz)
    services.guardar_foto(arroz[0], services.preparar_foto(imagen(color=(0, 0, 200))))
    antes = FotoProducto.objects.get().version
    carpeta("7702001001234.jpg")
    _correr(carpeta)
    assert FotoProducto.objects.get().version == antes  # se respetó la que ya tenía
    _correr(carpeta, "--reemplazar")
    assert FotoProducto.objects.get().version != antes


def test_una_carpeta_inexistente_da_un_error_claro(tmp_path):
    with pytest.raises(Exception, match="no existe"):
        call_command("cargar_fotos", str(tmp_path / "nada"), stdout=StringIO())


def test_solo_toca_productos_publicos(arroz, carpeta):
    arroz[0].activo = False
    arroz[0].save()
    carpeta(f"{arroz[0].pk}.jpg")
    _correr(carpeta)
    assert not FotoProducto.objects.exists()


def test_no_se_confunde_con_presentaciones_de_otros_productos(arroz, carpeta, db):
    _, p500, p1kg = arroz
    assert Presentacion.objects.count() == 2  # el código sirve para llegar al producto
    p500.codigo_barras = "7702001001234"
    p500.save()
    carpeta("7702001001234.jpg")
    _correr(carpeta)
    assert FotoProducto.objects.get().producto == p1kg.producto
