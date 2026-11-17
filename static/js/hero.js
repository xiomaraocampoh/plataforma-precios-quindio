/* Titular animado de la portada: rota la última palabra (sin dependencias).
   Mejora progresiva: sin JS o con "reducir movimiento" se queda con la palabra inicial.
   Decisión del equipo: la rotación es continua y SIN botón de pausa (ver docs/nucleo/alcance-y-limites.md).
   Quien tiene activado «reducir movimiento» en su sistema no ve la animación (ver más abajo).
   WCAG 1.4.12: si cambia el espaciado o el tamaño del texto, el ancho se recalcula y la palabra
   no se recorta. */
(() => {
  const cont = document.querySelector(".rota");
  if (!cont || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  const palabras = (cont.dataset.palabras || "").split(",").filter(Boolean);
  let actual = cont.querySelector(".rota-palabra");
  if (palabras.length < 2 || !actual) return;

  const INTERVALO_MS = 2600;
  const enEm = (px) => px / parseFloat(getComputedStyle(cont).fontSize);
  const fijarAncho = (el) => { cont.style.width = enEm(el.getBoundingClientRect().width) + "em"; };
  const observador = new ResizeObserver(() => fijarAncho(actual));

  fijarAncho(actual);
  observador.observe(actual);
  cont.classList.add("rota-activa");

  let i = 0;
  const rotar = () => {
    if (document.hidden) return;
    i = (i + 1) % palabras.length;
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
  };
  setInterval(rotar, INTERVALO_MS);
})();
