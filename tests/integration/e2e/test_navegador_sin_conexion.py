"""Registro sin conexión en un navegador real (RF-12, RNF-15, ADR-009, M-22).

Simula la pérdida de red con Playwright y verifica en la BD que cada precio quede una sola vez.
"""

import json
import os
import re

import pytest
from django.urls import reverse
from playwright.sync_api import Route, expect

from apps.precios.models import ReportePrecio

pytestmark = [pytest.mark.integration, pytest.mark.e2e]

RUTA_REGISTRO = reverse("precios:registrar")
PATRON_REGISTRO = re.compile(re.escape(RUTA_REGISTRO) + r"$")
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


def _abrir_registro(pagina, live_server):
    pagina.goto(live_server.url + RUTA_REGISTRO)
    expect(pagina.locator("input[name=id_cliente]")).to_have_value(UUID)  # crypto.randomUUID


def _llenar_y_guardar(pagina, precio="4500"):
    pagina.select_option("select[name=establecimiento]", index=1)
    pagina.select_option("select[name=presentacion]", index=1)
    pagina.fill("input[name=precio]", precio)
    pagina.get_by_role("button", name="Guardar precio").click()


def _perder_la_respuesta(route: Route):
    """El POST llega al servidor y se guarda, pero la respuesta nunca vuelve al celular."""
    route.fetch()
    route.abort("internetdisconnected")


def _cola(pagina) -> list:
    return pagina.evaluate(
        "() => Object.keys(localStorage).filter(k => k.startsWith('ahorrapues:registros'))"
        ".flatMap(k => JSON.parse(localStorage.getItem(k)))"
    )


def test_sin_senal_guarda_el_registro_y_lo_envia_al_volver_la_red(
    pagina_con_sesion, live_server, context
):  # M-22: reenvío por el evento "online"
    pagina = pagina_con_sesion
    _abrir_registro(pagina, live_server)
    aviso = pagina.locator("#registros-pendientes")

    context.set_offline(True)
    _llenar_y_guardar(pagina)
    expect(aviso).to_contain_text("1 registro pendiente de enviar")
    assert ReportePrecio.objects.count() == 0
    (pendiente,) = _cola(pagina)
    assert pendiente["fecha_observacion"]  # se guarda la hora en que se vio el precio (RN-08)
    expect(pagina.locator("input[name=id_cliente]")).not_to_have_value(pendiente["id_cliente"])

    context.set_offline(False)
    expect(aviso).to_contain_text("Se envió tu registro pendiente")
    assert ReportePrecio.objects.filter(id_cliente=pendiente["id_cliente"]).count() == 1
    assert _cola(pagina) == []


def test_respuesta_perdida_se_reenvia_al_cargar_la_pagina_sin_duplicar(
    pagina_con_sesion, live_server
):  # M-22: el primer envío sí llegó; el reenvío con el mismo id_cliente no crea otro
    pagina = pagina_con_sesion
    _abrir_registro(pagina, live_server)
    pagina.route(PATRON_REGISTRO, _perder_la_respuesta, times=1)

    _llenar_y_guardar(pagina)
    expect(pagina.locator("#registros-pendientes")).to_contain_text(
        "1 registro pendiente de enviar"
    )
    assert ReportePrecio.objects.count() == 1  # el servidor ya lo tenía

    pagina.reload()
    expect(pagina.locator("#registros-pendientes")).to_contain_text(
        "Se envió tu registro pendiente"
    )
    assert ReportePrecio.objects.count() == 1
    assert _cola(pagina) == []


def test_m22_diez_registros_sin_conexion_se_sincronizan_sin_perdida_ni_duplicados(
    pagina_con_sesion, live_server, context
):  # M-22 = registros sincronizados / registros hechos sin conexión (aceptable ≥ 98 %)
    pagina = pagina_con_sesion
    _abrir_registro(pagina, live_server)
    aviso = pagina.locator("#registros-pendientes")

    for i in range(5):  # la respuesta se pierde: el servidor ya los tiene
        pagina.route(PATRON_REGISTRO, _perder_la_respuesta, times=1)
        _llenar_y_guardar(pagina, precio=str(4000 + i * 10))
        expect(aviso).to_contain_text(f"{i + 1} registro")
    context.set_offline(True)
    for i in range(5, 10):  # sin señal: no salen del celular
        _llenar_y_guardar(pagina, precio=str(4000 + i * 10))
        expect(aviso).to_contain_text(f"{i + 1} registros pendientes de enviar")
    hechos = {r["id_cliente"] for r in _cola(pagina)}
    assert len(hechos) == 10

    context.set_offline(False)
    expect(aviso).to_contain_text("Se enviaron tus 10 registros pendientes")
    guardados = ReportePrecio.objects.filter(id_cliente__in=hechos)
    sincronizados = guardados.count()
    duplicados = ReportePrecio.objects.count() - sincronizados
    m22 = sincronizados / len(hechos)

    resultado = {
        "hechos_sin_conexion": len(hechos),
        "sincronizados": sincronizados,
        "duplicados": duplicados,
        "M-22": m22,
    }
    if salida := os.environ.get("M22_SALIDA"):  # evidencia para el informe de calidad
        with open(salida, "w", encoding="utf-8") as archivo:
            json.dump(resultado, archivo, ensure_ascii=False, indent=2)
    assert duplicados == 0
    assert m22 >= 0.98, resultado
