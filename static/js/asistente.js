/* Asistente de compras: botón flotante en todas las páginas y chat. Mejora progresiva: sin JS el botón es
   un enlace a /asistente/ y el formulario envía la página completa.
   - Abre y cierra el panel; Esc lo cierra y el foco vuelve al botón; recuerda si estaba abierto.
   - Enter envía; Mayús+Enter baja de línea; la caja crece; la conversación baja al último mensaje. */
(() => {
  const CLAVE = "ahorrapues-asistente-abierto";
  const raiz = document.querySelector("[data-asistente]");
  const lanzador = raiz && raiz.querySelector("[data-lanzador]");
  const panel = raiz && raiz.querySelector("[data-panel]");

  const hilo = () => document.getElementById("chat-hilo");
  const caja = () => document.getElementById("chat-mensaje");
  const ajustar = () => { const c = caja(); if (c) { c.style.height = "auto"; c.style.height = Math.min(c.scrollHeight, 140) + "px"; } };
  const bajar = () => { const h = hilo(); if (h && h.lastElementChild) h.lastElementChild.scrollIntoView({ block: "end" }); };
  const recordar = (valor) => { try { valor ? sessionStorage.setItem(CLAVE, "1") : sessionStorage.removeItem(CLAVE); } catch { /* sin almacenamiento */ } };
  const recordado = () => { try { return sessionStorage.getItem(CLAVE) === "1"; } catch { return false; } };

  const abrir = (enfocar = true) => {
    if (!panel) return;
    panel.hidden = false;
    lanzador.setAttribute("aria-expanded", "true");
    document.body.classList.add("asistente-abierto");
    recordar(true);
    const cuerpo = panel.querySelector("[data-cuerpo]");
    if (window.htmx && cuerpo) window.htmx.trigger(cuerpo, "asistente:abrir");
    if (enfocar) setTimeout(() => { const c = caja(); (c || panel).focus(); }, 60);
  };
  const cerrar = (devolverFoco = true) => {
    if (!panel) return;
    panel.hidden = true;
    lanzador.setAttribute("aria-expanded", "false");
    document.body.classList.remove("asistente-abierto");
    recordar(false);
    if (devolverFoco) lanzador.focus();
  };

  if (lanzador && panel) {
    lanzador.setAttribute("role", "button");
    lanzador.addEventListener("click", (e) => { e.preventDefault(); panel.hidden ? abrir() : cerrar(); });
    panel.querySelector("[data-cerrar]").addEventListener("click", () => cerrar());
    // Esc cierra el panel estés donde estés, salvo que haya otro diálogo abierto (p. ej. el escáner)
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && !panel.hidden && !document.querySelector("dialog[open]")) cerrar();
    });
    // Tras cargar la página (y haber iniciado htmx) se reabre si estaba abierto al cambiar de página
    window.addEventListener("load", () => { if (recordado()) abrir(false); });
  }

  document.addEventListener("input", (e) => { if (e.target.id === "chat-mensaje") ajustar(); });
  document.addEventListener("keydown", (e) => {
    if (e.target.id === "chat-mensaje" && e.key === "Enter" && !e.shiftKey && !e.isComposing) {
      e.preventDefault();
      e.target.form.requestSubmit();
    }
  });
  document.addEventListener("change", (e) => {
    if (!e.target.matches("[data-archivo]")) return;
    const nombre = e.target.form.querySelector("[data-nombre-archivo]");
    nombre.hidden = !e.target.files.length;
    nombre.textContent = e.target.files.length ? "📎 " + e.target.files[0].name : "";
  });
  document.body.addEventListener("htmx:afterSwap", (e) => {
    const destino = e.target;
    if (destino === hilo()) {
      const c = caja(); if (c) { c.value = ""; ajustar(); }
      const f = document.querySelector("[data-archivo]");
      if (f) { f.value = ""; const n = f.form.querySelector("[data-nombre-archivo]"); n.hidden = true; n.textContent = ""; }
      bajar();
    } else if (destino.matches && destino.matches("[data-cuerpo]")) {
      bajar();
    }
  });
})();
