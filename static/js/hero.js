/* Titular animado de la portada: rota la última palabra (sin dependencias).
   Mejora progresiva: sin JS o con "reducir movimiento" se queda con la palabra inicial. */
(() => {
  const cont = document.querySelector(".rota");
  if (!cont || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  const palabras = (cont.dataset.palabras || "").split(",").filter(Boolean);
  let actual = cont.querySelector(".rota-palabra");
  if (palabras.length < 2 || !actual) return;

  const enEm = (px) => px / parseFloat(getComputedStyle(cont).fontSize);
  const fijarAncho = (el) => { cont.style.width = enEm(el.getBoundingClientRect().width) + "em"; };

  fijarAncho(actual);
  cont.classList.add("rota-activa");

  let i = 0;
  setInterval(() => {
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
    actual = siguiente;
    setTimeout(() => vieja.remove(), 700);
  }, 2600);
})();
