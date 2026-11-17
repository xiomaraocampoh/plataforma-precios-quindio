/* RF-16: «Equivale a $X por kg» mientras se escribe el precio total del empaque.
   Solo es una ayuda visual: el precio por unidad que se guarda y se compara lo calcula el servidor
   (apps/catalogo/domain/normalizacion.py). Misma conversión: g → kg, ml → L, und → unidad.
   Delegación en document: el formulario se reemplaza con HTMX tras cada envío. */
(function () {
  "use strict";
  var BASE = { g: ["kg", 0.001], kg: ["kg", 1], ml: ["litro", 0.001], L: ["litro", 1], und: ["unidad", 1] };
  var pesos = new Intl.NumberFormat("es-CO", { maximumFractionDigits: 0 });

  function calcular(form) {
    var salida = form.querySelector("[data-equivale]");
    var precio = form.querySelector("[data-precio-total]");
    var select = form.querySelector("select[name='presentacion']");
    if (!salida || !precio || !select) return;
    var opcion = select.options[select.selectedIndex];
    var valor = parseFloat(String(precio.value).replace(",", "."));
    var cantidad = opcion ? parseFloat(opcion.getAttribute("data-cantidad")) : NaN;
    var conversion = opcion ? BASE[opcion.getAttribute("data-unidad")] : null;
    if (!conversion || !(valor > 0) || !(cantidad > 0)) {
      salida.textContent = "";
      return;
    }
    var porUnidad = valor / (cantidad * conversion[1]);
    salida.textContent = "Equivale a $" + pesos.format(Math.round(porUnidad)) + " por " + conversion[0];
  }

  function alCambiar(evento) {
    var form = evento.target && evento.target.closest && evento.target.closest("form");
    if (form && form.querySelector("[data-equivale]")) calcular(form);
  }

  document.addEventListener("input", alCambiar);
  document.addEventListener("change", alCambiar);
  function recalcularTodo() {
    document.querySelectorAll("[data-equivale]").forEach(function (s) { calcular(s.closest("form")); });
  }
  document.addEventListener("htmx:afterSwap", recalcularTodo);
  recalcularTodo(); // el script es defer: el formulario ya está (p. ej. de vuelta con un error)
})();
