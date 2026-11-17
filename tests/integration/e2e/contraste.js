// WCAG 1.4.3: contraste de cada texto visible de las tarjetas de precio contra su fondo real.
// Mezcla las capas translúcidas de los ancestros. Devuelve los textos que no llegan a 4.5:1
// (3:1 si el texto es grande: ≥ 24 px, o ≥ 18,66 px en negrita). Lo usa test_tarjetas_navegador.py.
() => {
  const rgba = (c) => {
    const m = c.match(/[\d.]+/g).map(Number);
    return [m[0], m[1], m[2], m.length > 3 ? m[3] : 1];
  };
  const lum = ([r, g, b]) => {
    const f = (v) => {
      v /= 255;
      return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
    };
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
  };
  const mezclar = (arriba, abajo) => {
    const a = arriba[3];
    return [0, 1, 2].map((i) => arriba[i] * a + abajo[i] * (1 - a)).concat(1);
  };
  const fondo = (el) => {
    const capas = [];
    for (let n = el; n; n = n.parentElement) {
      const c = rgba(getComputedStyle(n).backgroundColor);
      if (c[3] > 0) capas.push(c);
      if (c[3] >= 1) break;
    }
    let base = [255, 255, 255, 1];
    if (capas.length && capas[capas.length - 1][3] >= 1) base = capas.pop();
    return capas.reverse().reduce((abajo, arriba) => mezclar(arriba, abajo), base);
  };
  const fallos = [];
  document.querySelectorAll(".tarjeta-precio *").forEach((el) => {
    const texto = [...el.childNodes]
      .filter((n) => n.nodeType === 3)
      .map((n) => n.textContent.trim())
      .join("");
    const r = el.getBoundingClientRect();
    if (!texto || r.width <= 1 || r.height <= 1) return;
    const cs = getComputedStyle(el);
    const bg = fondo(el);
    const fg = mezclar(rgba(cs.color), bg);
    const [a, b] = [lum(fg), lum(bg)].sort((x, y) => y - x);
    const ratio = (a + 0.05) / (b + 0.05);
    const tam = parseFloat(cs.fontSize);
    const grande = tam >= 24 || (tam >= 18.66 && Number(cs.fontWeight) >= 700);
    if (ratio < (grande ? 3 : 4.5)) fallos.push(texto.slice(0, 40) + ": " + ratio.toFixed(2));
  });
  return fallos;
};
