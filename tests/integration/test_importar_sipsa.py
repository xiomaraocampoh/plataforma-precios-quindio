"""RF-07: importación de precios de referencia SIPSA desde un CSV del DANE."""

from io import StringIO

import pytest
from django.core.management import CommandError, call_command
from django.urls import reverse
from django.utils import timezone

from apps.comparacion.selectors import comparar_producto
from apps.integraciones.clients.sipsa import leer_csv_sipsa
from apps.integraciones.models import PrecioReferencia

pytestmark = pytest.mark.integration


def _csv(tmp_path, contenido: str, nombre: str = "sipsa.csv"):
    ruta = tmp_path / nombre
    ruta.write_text(contenido, encoding="utf-8")
    return ruta


def _hoy() -> str:
    return timezone.localdate().strftime("%d/%m/%Y")


def test_lee_encabezados_con_tildes_separador_y_formato_colombiano():
    lectura = leer_csv_sipsa(
        StringIO(
            "Producto;Mercado;Precio promedio;Fecha\nArroz blanco;Armenia;$ 4.180,50;14/11/2026\n"
        )
    )
    assert lectura.errores == []
    assert str(lectura.precios[0].precio_por_kg) == "4180.50"


def test_informa_las_filas_con_error_y_sigue():
    lectura = leer_csv_sipsa(
        StringIO(
            "producto,mercado,precio,fecha\nArroz,Armenia,n.d.,2026-11-14\nPapa,Armenia,1950,2026-11-14\n"
        )
    )
    assert [linea for linea, _ in lectura.errores] == [2]
    assert [p.producto for p in lectura.precios] == ["Papa"]


def test_comando_importa_asocia_por_nombre_y_es_idempotente(tmp_path, arroz):
    producto, _, _ = arroz
    ruta = _csv(
        tmp_path,
        f"producto;mercado;precio;fecha\nARROZ BLANCO;Armenia, Mercar;4.180;{_hoy()}\n"
        f"Mango tommy;Armenia, Mercar;3.200;{_hoy()}\n",
    )
    salida = StringIO()
    call_command("importar_sipsa", str(ruta), stdout=salida)
    assert "1 nuevos, 0 actualizados" in salida.getvalue()
    assert "Sin producto en el catálogo (no se importaron): Mango tommy" in salida.getvalue()
    referencia = PrecioReferencia.objects.get()
    assert referencia.producto == producto and referencia.fuente == "sipsa"

    ruta.write_text(
        f"producto;mercado;precio;fecha\nArroz blanco;Armenia, Mercar;4.250;{_hoy()}\n",
        encoding="utf-8",
    )
    salida = StringIO()
    call_command("importar_sipsa", str(ruta), stdout=salida)
    assert "0 nuevos, 1 actualizados" in salida.getvalue()
    assert PrecioReferencia.objects.get().precio_por_kg == 4250


def test_archivo_sin_columnas_requeridas_falla_con_mensaje(tmp_path, db):
    ruta = _csv(tmp_path, "nombre;valor\nArroz;4500\n")
    with pytest.raises(CommandError, match="Faltan columnas"):
        call_command("importar_sipsa", str(ruta), stdout=StringIO())


def test_la_comparacion_la_muestra_como_referencia_sin_entrar_al_ranking(client, tmp_path, arroz):
    producto, _, _ = arroz
    ruta = _csv(
        tmp_path, f"producto;mercado;precio;fecha\nArroz blanco;Armenia, Mercar;4.180;{_hoy()}\n"
    )
    call_command("importar_sipsa", str(ruta), stdout=StringIO())
    html = client.get(reverse("comparacion:comparar", args=[producto.pk])).content.decode()
    assert "Referencia mayorista SIPSA (DANE)" in html
    assert "Armenia, Mercar" in html
    assert comparar_producto(producto.pk) == []  # no es un precio de tienda: no se ordena
