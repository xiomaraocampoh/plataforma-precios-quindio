"""Las dependencias que lee Vercel no se desalinean de requirements/prod.txt (ADR-0031).

Vercel no lee «-r» de forma documentada y no dice qué archivo gana si hay varios, así que la
lista efectiva de producción se declara completa en requirements.txt (versiones fijadas) y en
[project].dependencies de pyproject.toml. requirements/prod.txt sigue siendo la fuente: lo usan el
Dockerfile y Render. Si se agrega o sube una dependencia allí, esta prueba falla hasta que los dos
archivos de Vercel se actualicen.
"""

import tomllib
from pathlib import Path

import pytest
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

pytestmark = pytest.mark.unit

RAIZ = Path(__file__).resolve().parents[2]


def _lineas(ruta: Path) -> list[str]:
    """Requisitos de un archivo de pip, siguiendo «-r» y sin comentarios."""
    requisitos: list[str] = []
    for cruda in ruta.read_text(encoding="utf-8").splitlines():
        linea = cruda.split(" #", 1)[0].split("\t#", 1)[0].strip()
        if not linea or linea.startswith("#"):
            continue
        if linea.startswith("-r"):
            requisitos += _lineas(ruta.parent / linea.removeprefix("-r").strip())
            continue
        assert not linea.startswith("-"), f"{ruta.name}: opción de pip no admitida: {linea}"
        requisitos.append(linea)
    return requisitos


def _por_nombre(lineas: list[str]) -> dict[str, Requirement]:
    requisitos = [Requirement(linea) for linea in lineas]
    por_nombre = {canonicalize_name(r.name): r for r in requisitos}
    assert len(por_nombre) == len(requisitos), "hay paquetes repetidos"
    return por_nombre


PROD = _por_nombre(_lineas(RAIZ / "requirements" / "prod.txt"))
VERCEL_TXT = _por_nombre(_lineas(RAIZ / "requirements.txt"))
PYPROJECT = _por_nombre(
    tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))["project"]["dependencies"]
)


def test_requirements_txt_no_usa_includes():
    contenido = (RAIZ / "requirements.txt").read_text(encoding="utf-8")
    assert not any(linea.strip().startswith("-") for linea in contenido.splitlines())


def test_requirements_txt_tiene_exactamente_los_paquetes_de_produccion():
    assert set(VERCEL_TXT) == set(PROD)


@pytest.mark.parametrize("nombre", sorted(PROD))
def test_cada_version_fijada_cumple_el_rango_de_produccion(nombre):
    fijado, rango = VERCEL_TXT[nombre], PROD[nombre]
    (especificador,) = fijado.specifier  # una sola condición…
    assert especificador.operator == "==", f"{nombre}: fije la versión exacta con «==»"  # …exacta
    assert rango.specifier.contains(especificador.version, prereleases=True), (
        f"{nombre}=={especificador.version} no cumple «{rango.specifier}» de requirements/prod.txt"
    )
    assert fijado.extras == rango.extras, f"{nombre}: los extras deben coincidir"
    assert fijado.marker == rango.marker


def test_pyproject_declara_las_mismas_dependencias_que_requirements_txt():
    assert {n: str(r) for n, r in PYPROJECT.items()} == {n: str(r) for n, r in VERCEL_TXT.items()}


def test_vercel_usa_la_misma_version_de_python_que_el_ci():
    assert (RAIZ / ".python-version").read_text(encoding="utf-8").strip() == "3.12"
