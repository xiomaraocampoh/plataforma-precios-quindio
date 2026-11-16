/* Titular animado de la portada: cambia la última palabra unas cuantas veces y se detiene sola
   en la palabra inicial (sin dependencias).
   WCAG 2.2.2: el movimiento automático dura menos de 5 s, por eso no necesita un botón de pausa.
   Mejora progresiva: sin JS o con "reducir movimiento" se queda con la palabra inicial.
   WCAG 1.4.12: si cambia el espaciado o el tamaño del texto, el ancho se recalcula y la palabra
   no se recorta. */
(() => {
  const cont = document.querySelector(".rota");
  if (!cont || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  // La lista termina en la palabra inicial: tras el último cambio el titular queda como empezó.
  const palabras = (cont.dataset.palabras || "").split(",").filter(Boolean);
  let actual = cont.querySelector(".rota-palabra");
  if (palabras.length < 2 || !actual) return;

  const INTERVALO_MS = 1200;       // (cambios × intervalo) + 700 ms de transición ≤ 5 s
  const enEm = (px) => px / parseFloat(getComputedStyle(cont).fontSize);
  const fijarAncho = (el) => { cont.style.width = enEm(el.getBoundingClientRect().width) + "em"; };
  const observador = new ResizeObserver(() => fijarAncho(actual));

  fijarAncho(actual);
  observador.observe(actual);
  cont.classList.add("rota-activa");

  let i = 0;
  const rotar = () => {
    i += 1;
    const siguiente = document.createElement("span");
    siguiente.className = "rota-palabra entra";
    siguiente.textContent = palabras[i];
    cont.appendChild(siguiente);
    fijarAncho(siguiente);        // el ancho se anima hasta la nueva palabra
    void siguiente.offsetWidth;   // fuerza el estado inicial antes de la transición
    actual.classList.add("sale");
    siguiente.classList.remove("entra");
    const vieja = actual;
    observador.unobserve(vieja);
    actual = siguiente;
    observador.observe(actual);
    setTimeout(() => vieja.remove(), 700);
    if (i < palabras.length - 1) setTimeout(rotar, INTERVALO_MS);
  };
  setTimeout(rotar, INTERVALO_MS);
})();
