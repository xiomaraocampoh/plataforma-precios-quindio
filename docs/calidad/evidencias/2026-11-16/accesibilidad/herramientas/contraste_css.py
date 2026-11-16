"""Razones de contraste WCAG 2.2 (1.4.3 y 1.4.11) de los tokens de static/css/app.css.

Uso: python contraste_css.py static/css/app.css > contraste.md
Lee los tokens de :root, del bloque oscuro (prefers-color-scheme: dark) y de .hero-fondo.
"""

import re
import sys
from pathlib import Path


def luminancia(hexa: str) -> float:
    hexa = hexa.lstrip("#")
    canales = [int(hexa[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in canales]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def razon(a: str, b: str) -> float:
    la, lb = sorted((luminancia(a), luminancia(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def mezcla(frente: str, fondo: str, alfa: float) -> str:
    f, b = frente.lstrip("#"), fondo.lstrip("#")
    return "#" + "".join(
        f"{round(int(f[i : i + 2], 16) * alfa + int(b[i : i + 2], 16) * (1 - alfa)):02x}"
        for i in (0, 2, 4)
    )


def tokens(bloque: str) -> dict[str, str]:
    return dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{6})", bloque))


css = Path(sys.argv[1]).read_text(encoding="utf-8")
claro = tokens(re.search(r":root\s*{(.*?)}", css, re.S).group(1))
oscuro = {
    **claro,
    **tokens(
        re.search(r"prefers-color-scheme:\s*dark\)\s*{\s*:root\s*{(.*?)}", css, re.S).group(1)
    ),
}
SUBRAYADO = bool(re.search(r"p a:not\(\.btn\)[^{]*{[^}]*text-decoration:\s*underline", css))
hero = {**claro, **tokens(re.search(r"\.hero-fondo\s*{(.*?)}", css, re.S).group(1))}

# (descripción, primer plano, fondo, mínimo, criterio)
PARES = [
    ("Texto principal sobre fondo", "texto", "fondo", 4.5, "1.4.3"),
    ("Texto principal sobre tarjeta", "texto", "superficie", 4.5, "1.4.3"),
    ("Texto suave sobre tarjeta", "texto-suave", "superficie", 4.5, "1.4.3"),
    ("Texto suave sobre fondo", "texto-suave", "fondo", 4.5, "1.4.3"),
    ("Texto suave sobre tarjeta de marca", "texto-suave", "marca-suave", 4.5, "1.4.3"),
    ("Enlace sobre tarjeta", "marca-enlace", "superficie", 4.5, "1.4.3"),
    ("Enlace sobre fondo", "marca-enlace", "fondo", 4.5, "1.4.3"),
    ("Botón secundario en hover", "marca-enlace", "marca-suave", 4.5, "1.4.3"),
    ("Botón primario", "sobre-marca", "marca", 4.5, "1.4.3"),
    ("Botón primario en hover", "sobre-marca", "marca-hover", 4.5, "1.4.3"),
    ("Mensaje de error", "error", "error-fondo", 4.5, "1.4.3"),
    ("Chip de promoción", "ambar-texto", "ambar-fondo", 4.5, "1.4.3"),
    ("Chip positivo", "positivo", "positivo-fondo", 4.5, "1.4.3"),
    ("Texto suave en tile oscuro", "sobre-oscura-suave", "marca-oscura", 4.5, "1.4.3"),
    ("Enlace frente al texto suave vecino", "marca-enlace", "texto-suave", 3.0, "1.4.1"),
    ("Borde de campo sobre tarjeta", "borde-fuerte", "superficie", 3.0, "1.4.11"),
    ("Borde de campo sobre fondo", "borde-fuerte", "fondo", 3.0, "1.4.11"),
    ("Contorno de foco sobre fondo", "marca", "fondo", 3.0, "1.4.11 / 2.4.7"),
    ("Contorno de foco sobre tarjeta", "marca", "superficie", 3.0, "1.4.11 / 2.4.7"),
    ("Contorno de foco sobre tile oscuro", "marca", "marca-oscura", 3.0, "1.4.11 / 2.4.7"),
    ("Ícono de marca sobre caja de ícono", "marca", "marca-suave", 3.0, "1.4.11"),
]
FIJOS = [
    ("Texto en tile oscuro", "#f5f5f7", "#1d1d1f", 4.5, "1.4.3"),
    ("Enlace dentro de tile oscuro (#6cb6ff)", "#6cb6ff", "#1d1d1f", 4.5, "1.4.3"),
    ("Chip en tile oscuro", "#f5f5f7", mezcla("#ffffff", "#1d1d1f", 0.12), 4.5, "1.4.3"),
]


def tabla(nombre: str, paleta: dict[str, str]) -> list[str]:
    filas = [
        f"\n### {nombre}\n",
        "| Par | Colores | Razón | Mínimo | Criterio | Resultado |",
        "|---|---|---|---|---|---|",
    ]
    for desc, fg, bg, minimo, crit in PARES:
        r = razon(paleta[fg], paleta[bg])
        ok = "cumple" if r >= minimo else "**NO CUMPLE**"
        if crit == "1.4.1" and SUBRAYADO:
            ok = "no aplica: los enlaces en texto van subrayados"
        filas.append(
            f"| {desc} | `{paleta[fg]}` / `{paleta[bg]}` | {r:.2f}:1 | {minimo}:1 | {crit} | {ok} |"
        )
    return filas


salida = [
    f"# Contraste de `{sys.argv[1]}` (WCAG 2.2)",
    "",
    "Fórmula de luminancia relativa de WCAG; razón = (L1 + 0,05) / (L2 + 0,05).",
]
salida += (
    tabla("Tema claro", claro)
    + tabla("Tema oscuro", oscuro)
    + tabla("Hero (paleta clara fija sobre la foto)", hero)
)
salida += [
    "\n### Colores fijos\n",
    "| Par | Colores | Razón | Mínimo | Criterio | Resultado |",
    "|---|---|---|---|---|---|",
]
for desc, fg, bg, minimo, crit in FIJOS:
    r = razon(fg, bg)
    estado = "cumple" if r >= minimo else "**NO CUMPLE**"
    salida.append(f"| {desc} | `{fg}` / `{bg}` | {r:.2f}:1 | {minimo}:1 | {crit} | {estado} |")
fallos = sum(1 for linea in salida if "NO CUMPLE" in linea)
salida.append(f"\n**Pares que no cumplen: {fallos}.**")
print("\n".join(salida))
