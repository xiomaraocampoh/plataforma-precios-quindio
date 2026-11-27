/* Conserva la posición de la página cuando la persona sigue en la misma pantalla: paginar, filtrar
   o guardar un formulario que vuelve a la misma ruta. Otra ruta empieza arriba, como siempre. */
(() => {
  const CLAVE = "ahorrapues-posicion";
  const VIGENCIA_MS = 15000;
  const guardar = () => {
    try {
      sessionStorage.setItem(CLAVE, JSON.stringify({ ruta: location.pathname, y: window.scrollY, t: Date.now() }));
    } catch (e) { /* sin almacenamiento: la página simplemente empieza arriba */ }
  };
  document.addEventListener("click", (ev) => {
    const a = ev.target.closest && ev.target.closest("a[href]");
    if (!a || ev.defaultPrevented || ev.button !== 0 || ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey) return;
    if (a.target && a.target !== "_self") return;
    const destino = new URL(a.href, location.href);
    if (destino.origin === location.origin && destino.pathname === location.pathname && !destino.hash) guardar();
  });
  document.addEventListener("submit", (ev) => {
    if (ev.defaultPrevented || ev.target.hasAttribute("hx-post") || ev.target.hasAttribute("hx-get")) return;
    guardar();
  });
  const restaurar = () => {
    let datos = null;
    try { datos = JSON.parse(sessionStorage.getItem(CLAVE) || "null"); sessionStorage.removeItem(CLAVE); } catch (e) { return; }
    if (!datos || datos.ruta !== location.pathname || Date.now() - datos.t > VIGENCIA_MS || location.hash) return;
    let movida = false;  // si la persona ya desplazó, no se le quita el control
    ["wheel", "touchstart", "keydown", "mousedown"].forEach((n) =>
      window.addEventListener(n, () => { movida = true; }, { once: true, passive: true }));
    const ir = () => { if (!movida) window.scrollTo({ top: datos.y, behavior: "instant" }); };
    ir();
    window.addEventListener("load", () => { ir(); [150, 400, 900].forEach((ms) => setTimeout(ir, ms)); }, { once: true });
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", restaurar);
  else restaurar();
})();
