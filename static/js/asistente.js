/* K-nasta: botón flotante en todas las páginas y chat. Mejora progresiva: sin JS el botón es un enlace
   a /asistente/ y el formulario envía la página completa.
   - Abre y cierra el panel; Esc lo cierra y el foco vuelve al botón; recuerda si estaba abierto.
   - Al enviar, el mensaje aparece al instante, la caja se vacía y se ven los puntos de «escribiendo»
     dentro de la conversación; cuando llega la respuesta, el servidor reemplaza todo (sin duplicados).
   - Si el envío falla, el texto vuelve a la caja y se avisa. No se envía otro mensaje mientras se espera.
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
  const anunciar = (texto) => {
    const region = document.getElementById("avisos");
    if (!region) return;
    region.textContent = "";
    setTimeout(() => { region.textContent = texto; }, 50);
  };

  // --- Panel flotante ---------------------------------------------------------------------------
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
    panel.querySelector("[data-asistente-cerrar]").addEventListener("click", () => cerrar());
    // Esc cierra el panel estés donde estés, salvo que haya otro diálogo abierto (p. ej. el escáner)
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && !panel.hidden && !document.querySelector("dialog[open]")) cerrar();
    });
    // Tras cargar la página (y haber iniciado htmx) se reabre si estaba abierto al cambiar de página
    window.addEventListener("load", () => { if (recordado()) abrir(false); });
  }

  // --- Chat: el mensaje se ve al instante ---------------------------------------------------------
  let enVuelo = false;
  let respaldo = null; // { texto, esCaja } para devolverlo a la caja si el envío falla

  const nodo = (clase, texto) => {
    const n = document.createElement("div");
    n.className = clase;
    n.setAttribute("aria-hidden", "true"); // lo anuncia #avisos; así el lector no lee dos veces
    const c = document.createElement("div");
    c.className = "cuerpo";
    if (texto !== undefined) { const p = document.createElement("p"); p.textContent = texto; c.appendChild(p); }
    n.appendChild(c);
    return [n, c];
  };
  const avatar = () => {
    const origen = document.querySelector(".knasta-avatar");
    const a = document.createElement("span");
    a.className = "avatar";
    if (origen) { const i = document.createElement("img"); i.src = origen.src; i.alt = ""; i.width = 32; i.height = 32; a.appendChild(i); }
    return a;
  };
  const pintarPendiente = (texto, archivo) => {
    const h = hilo();
    if (!h) return;
    const [mio] = nodo("burbuja usuario pendiente", [texto, archivo ? "📎 " + archivo : ""].filter(Boolean).join("\n"));
    const [suyo, cuerpo] = nodo("burbuja asistente pendiente");
    suyo.prepend(avatar());
    cuerpo.innerHTML = '<span class="puntos"><i></i><i></i><i></i></span>';
    h.append(mio, suyo);
    bajar();
  };
  const quitarPendientes = () => { const h = hilo(); if (h) h.querySelectorAll(".pendiente, [data-error-envio]").forEach((n) => n.remove()); };

  const esDelChat = (elt) => elt && elt.closest && (elt.matches(".chat-entrada") || elt.closest("#chat-hilo") || elt.closest(".asistente-reiniciar"));

  document.body.addEventListener("htmx:beforeRequest", (e) => {
    const forma = e.detail.elt;
    if (!esDelChat(forma)) return;
    if (enVuelo) { e.preventDefault(); return; } // una respuesta a la vez
    const campo = forma.querySelector("[name=mensaje]");
    const archivo = forma.querySelector("[data-archivo]");
    const reinicio = forma.querySelector("[name=reiniciar]");
    const texto = campo ? campo.value.trim() : "";
    const nombre = archivo && archivo.files.length ? archivo.files[0].name : "";
    if (!reinicio && !texto && !nombre) { e.preventDefault(); return; }
    enVuelo = true;
    quitarPendientes();
    if (reinicio) return;
    respaldo = { texto: campo ? campo.value : "", esCaja: forma.matches(".chat-entrada") };
    pintarPendiente(texto, nombre);
    if (respaldo.esCaja) { // el contenido ya viajó en la petición: la caja queda libre para seguir
      campo.value = ""; ajustar();
      if (archivo) { archivo.value = ""; const n = forma.querySelector("[data-nombre-archivo]"); if (n) { n.hidden = true; n.textContent = ""; } }
      campo.focus({ preventScroll: true });
    }
    anunciar("K-nasta está escribiendo…");
  });

  const fallo = () => {
    enVuelo = false;
    quitarPendientes();
    const c = caja();
    if (respaldo && respaldo.esCaja && c && !c.value) { c.value = respaldo.texto; ajustar(); }
    const h = hilo();
    if (h) {
      const [aviso, cuerpo] = nodo("burbuja asistente error");
      aviso.removeAttribute("aria-hidden");
      aviso.setAttribute("data-error-envio", "");
      aviso.setAttribute("role", "alert");
      cuerpo.textContent = "No pude enviar tu mensaje. Revisa tu conexión e inténtalo de nuevo.";
      h.appendChild(aviso);
      bajar();
    }
  };
  ["htmx:responseError", "htmx:sendError", "htmx:timeout"].forEach((nombre) =>
    document.body.addEventListener(nombre, (e) => { if (esDelChat(e.detail.elt)) fallo(); }));

  document.body.addEventListener("htmx:afterRequest", (e) => { if (esDelChat(e.detail.elt) && e.detail.successful) enVuelo = false; });

  document.body.addEventListener("htmx:afterSwap", (e) => {
    const destino = e.target;
    if (destino === hilo()) {
      bajar();
      const c = caja();
      if (c && panel && !panel.hidden) c.focus({ preventScroll: true });
      const ultima = hilo().querySelector(".burbuja.asistente:last-child .cuerpo p");
      if (ultima) anunciar("K-nasta: " + ultima.textContent.trim());
    } else if (destino.matches && destino.matches("[data-cuerpo]")) {
      bajar();
    }
  });

  document.addEventListener("input", (e) => { if (e.target.id === "chat-mensaje") ajustar(); });
  document.addEventListener("keydown", (e) => {
    if (e.target.id === "chat-mensaje" && e.key === "Enter" && !e.shiftKey && !e.isComposing) {
      e.preventDefault();
      if (!enVuelo) e.target.form.requestSubmit(); // si está esperando, el texto queda en la caja
    }
  });
  document.addEventListener("change", (e) => {
    if (!e.target.matches("[data-archivo]")) return;
    const nombre = e.target.form.querySelector("[data-nombre-archivo]");
    nombre.hidden = !e.target.files.length;
    nombre.textContent = e.target.files.length ? "📎 " + e.target.files[0].name : "";
  });
})();
