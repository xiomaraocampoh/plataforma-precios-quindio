/* Comportamientos de accesibilidad comunes (sin dependencias, mejora progresiva).
   - WCAG 2.2.2: pausar y reanudar la actualización automática de la comparación.
   - WCAG 4.1.3: anunciar en la región viva #avisos los cambios que no mueven el foco.
   - WCAG 2.4.3: tras un intercambio HTMX en el registro de precio, llevar el foco al primer
     campo con error o al título de la confirmación, en lugar de dejarlo perdido en <body>. */
(() => {
  const avisos = document.getElementById("avisos");
  const anunciar = (texto) => {
    if (!avisos) return;
    avisos.textContent = "";
    setTimeout(() => { avisos.textContent = texto; }, 50); // vaciar y escribir fuerza el anuncio
  };

  // Comparación: la recarga cada 60 s se filtra con window.actualizacionPausada (hx-trigger).
  const control = document.getElementById("control-actualizacion");
  const botonPausa = document.getElementById("pausar-actualizacion");
  if (control && botonPausa) {
    control.hidden = false;
    botonPausa.addEventListener("click", () => {
      window.actualizacionPausada = !window.actualizacionPausada;
      botonPausa.textContent = window.actualizacionPausada
        ? "Reanudar actualización" : "Pausar actualización";
      anunciar(window.actualizacionPausada
        ? "Actualización automática en pausa." : "Actualización automática activada.");
    });
  }

  const resultados = document.getElementById("resultados");
  let huellaResultados = resultados ? resultados.textContent.trim() : "";

  document.body.addEventListener("htmx:afterSwap", (evento) => {
    const destino = evento.detail.target;
    if (destino.id === "resultados") {
      const huella = destino.textContent.trim();
      if (huella !== huellaResultados) anunciar("Los precios se actualizaron.");
      huellaResultados = huella;
      return;
    }
    if (destino.id !== "registro") return;
    const invalido = destino.querySelector('[aria-invalid="true"]');
    const titulo = destino.querySelector("h2");
    if (invalido) {
      invalido.focus();          // el lector lee la etiqueta y el error asociado
    } else if (titulo) {
      titulo.tabIndex = -1;
      titulo.focus();
      anunciar(titulo.textContent.trim());
    } else {
      destino.querySelector("select, input:not([type=hidden])")?.focus();  // «Registrar otro»
    }
  });
})();
