"""El bloque final de la portada («Tu aporte ayuda a que todos ahorren») lleva una ilustración."""

from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


def test_el_bloque_final_usa_su_ilustracion_ancha_y_una_vertical_en_celular():
    css = (RAIZ / "static/css/app.css").read_text(encoding="utf-8")
    assert "fondo-cta.webp" in css and ".tile-oscuro.cta-final" in css
    assert (RAIZ / "static/img/fondo-cta.webp").stat().st_size < 120_000  # liviana para 3G
    assert (RAIZ / "static/img/fondo-panel.webp").exists()  # la vertical que se usa en celular
