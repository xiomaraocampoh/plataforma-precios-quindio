/* Chat del asistente de compras: mejora progresiva. Sin JS el formulario funciona igual (página completa).
   - Enter envía; Mayús+Enter baja de línea.
   - La caja crece con el texto y se vacía al enviar; la conversación baja al último mensaje.
   - Muestra el nombre del archivo adjunto. */
(() => {
  const forma = document.querySelector(".chat-entrada");
  const hilo = document.getElementById("chat-hilo");
  if (!forma || !hilo) return;
  const caja = forma.querySelector("textarea");
  const archivo = forma.querySelector("[data-archivo]");
  const nombre = forma.querySelector("[data-nombre-archivo]");

  const ajustar = () => { caja.style.height = "auto"; caja.style.height = Math.min(caja.scrollHeight, 160) + "px"; };
  const bajar = () => { const ult = hilo.lastElementChild; if (ult) ult.scrollIntoView({ block: "end", behavior: "smooth" }); };

  caja.addEventListener("input", ajustar);
  caja.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); forma.requestSubmit(); }
  });
  if (archivo && nombre) {
    archivo.addEventListener("change", () => {
      nombre.hidden = !archivo.files.length;
      nombre.textContent = archivo.files.length ? "📎 " + archivo.files[0].name : "";
    });
  }
  document.body.addEventListener("htmx:afterSwap", (e) => {
    if (e.target !== hilo) return;
    caja.value = ""; ajustar();
    if (archivo) { archivo.value = ""; if (nombre) { nombre.hidden = true; nombre.textContent = ""; } }
    bajar();
  });
})();
