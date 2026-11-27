"""La guía de uso de AhorraPues que K-nasta enseña a quien llega por primera vez. Python puro."""

import pytest

from apps.canasta.domain.guia import TEMAS, TIPOS_VISUAL, buscar_temas, tema_por_id

pytestmark = pytest.mark.unit


def _mejor(texto):
    temas = buscar_temas(texto)
    return temas[0].id if temas else None


@pytest.mark.parametrize(
    ("pregunta", "tema"),
    [
        ("¿Cómo registro un precio?", "registrar"),
        ("quiero reportar un precio que vi hoy", "registrar"),
        ("cómo subo el precio de la leche", "registrar"),
        ("¿Cómo creo una cuenta?", "cuenta"),
        ("necesito registrarme", "cuenta"),
        ("cómo me inscribo en la página", "cuenta"),
        ("¿Cómo comparo precios?", "comparar"),
        ("donde veo cuál tienda es más barata para el arroz", "comparar"),
        ("cómo confirmo un precio", "confirmar"),
        ("como denuncio un precio que está mal", "confirmar"),
        ("cómo escaneo el código de barras", "escanear"),
        ("puedo buscar con la cámara?", "escanear"),
        ("por qué ya no aparece el precio", "vigencia"),
        ("qué significa confianza media", "vigencia"),
        ("no encuentro un producto", "producto_faltante"),
        ("cómo pido que agreguen un producto", "producto_faltante"),
        ("mi tienda no está en el directorio", "tienda_faltante"),
        ("cómo sugiero un establecimiento", "tienda_faltante"),
        ("donde veo mis aportes", "mis_aportes"),
        ("cómo activo el modo oscuro", "apariencia"),
        ("tengo un comercio, cómo publico mis precios", "comercio"),
        ("mis datos son públicos?", "privacidad"),
        ("olvidé mi contraseña", "contrasena"),
        ("qué es AhorraPues", "que_es"),
        ("para qué sirve esta página", "que_es"),
    ],
)
def test_encuentra_el_tema_de_cada_pregunta(pregunta, tema):
    assert _mejor(pregunta) == tema


def test_sin_relacion_no_hay_tema():
    assert buscar_temas("hola buenas tardes") == []
    assert buscar_temas("2 kg arroz, 1 L leche") == []
    assert buscar_temas("") == []


def test_devuelve_como_mucho_los_temas_pedidos_ordenados_por_afinidad():
    temas = buscar_temas("cómo registro un precio y creo una cuenta", limite=2)
    assert len(temas) == 2 and {t.id for t in temas} == {"registrar", "cuenta"}


def test_no_distingue_tildes_ni_mayusculas():
    assert _mejor("COMO REGISTRO UN PRECIO") == "registrar"
    assert _mejor("como registro un precio") == "registrar"


def test_cada_tema_tiene_pasos_palabras_y_destinos_validos():
    ids = [t.id for t in TEMAS]
    assert len(ids) == len(set(ids)) and len(ids) >= 12
    for t in TEMAS:
        assert t.titulo and len(t.pasos) >= 1 and t.patrones
        assert all(paso.texto.strip() for paso in t.pasos)
        for texto, ruta in t.acciones:
            assert texto and ":" in ruta  # «app:nombre», para resolverla con reverse


def test_tema_por_id():
    assert tema_por_id("registrar").titulo.startswith("¿Cómo registro un precio")
    assert tema_por_id("no-existe") is None


def test_cada_tema_tiene_una_etiqueta_corta_y_un_icono_para_sus_botones():
    for t in TEMAS:
        assert 1 <= len(t.corto) <= 26, t.id  # cabe en un botón de dos columnas
        assert t.icono.startswith("i-"), t.id


# --- minitutoriales visuales ------------------------------------------------------------------
def test_cada_tema_se_explica_con_imagenes_en_la_mayoria_de_sus_pasos():
    for t in TEMAS:
        con_imagen = [p for p in t.pasos if p.visuales]
        assert con_imagen, t.id
        assert len(con_imagen) >= len(t.pasos) / 2, t.id  # un tutorial, no un texto con adornos


def test_las_imagenes_son_de_un_tipo_conocido_y_tienen_lo_que_necesitan():
    for t in TEMAS:
        for paso in t.pasos:
            for v in paso.visuales:
                assert v.tipo in TIPOS_VISUAL, (t.id, v.tipo)
                if v.tipo in {"boton", "boton_sec", "chip", "casilla", "simbolo"}:
                    assert v.texto.strip(), (t.id, v.tipo)
                if v.tipo == "campo":
                    assert v.texto.strip() and v.valor.strip(), t.id
                if v.tipo == "opciones":
                    assert len(v.opciones) >= 2 and -1 <= v.activa < len(v.opciones), t.id
                if v.tipo == "filas":
                    assert len(v.filas) >= 2, t.id
                if v.tipo == "icono":
                    assert v.icono.startswith("i-") and v.texto.strip(), t.id


def test_los_pasos_de_texto_siguen_disponibles_para_la_ia():
    t = tema_por_id("registrar")
    assert t.textos[0].startswith("Necesitas una cuenta") and len(t.textos) == len(t.pasos)


def test_la_guia_de_apariencia_solo_habla_del_boton_de_la_barra():
    texto = " ".join(tema_por_id("apariencia").textos).lower()
    assert "sol" in texto and "luna" in texto
    assert "menú" not in texto  # en todos los tamaños está en la barra
    assert "abajo" not in texto and "automática" not in texto  # el grupo del pie ya no existe


def test_la_guia_dice_donde_esta_el_menu_de_la_cuenta_en_celular_y_en_el_computador():
    for tema in ("mis_aportes", "comercio"):
        texto = " ".join(tema_por_id(tema).textos)
        assert "menú ☰" in texto and "arriba a la derecha" in texto, tema
