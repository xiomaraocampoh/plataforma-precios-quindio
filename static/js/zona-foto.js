/* Zona para la foto del producto: arrastrar y soltar, pegar (Ctrl+V) o buscar el archivo.
   Mejora progresiva: sin JavaScript queda el campo de archivo normal. El servidor vuelve a
   validar tipo, peso y tamaño; esto solo evita equivocarse antes de enviar. */
(function () {
  "use strict";
  var entrada = document.querySelector("input[type=file][data-zona-foto]");
  if (!entrada || typeof DataTransfer === "undefined") return;

  var TIPOS = ["image/jpeg", "image/png", "image/webp"];
  var MAX = 5 * 1024 * 1024;

  var zona = document.createElement("div");
  zona.className = "zona-foto";
  var texto = document.createElement("p");
  texto.className = "zona-foto-texto";
  texto.textContent = "Arrastra la foto aquí o pégala con Ctrl+V";
  var estado = document.createElement("p");
  estado.className = "zona-foto-estado";
  estado.setAttribute("role", "status");
  estado.setAttribute("aria-live", "polite");
  var vista = document.createElement("img");
  vista.className = "zona-foto-vista";
  vista.alt = "Vista previa de la foto elegida";
  vista.width = 120;
  vista.height = 120;
  vista.hidden = true;

  entrada.parentNode.insertBefore(zona, entrada);
  zona.appendChild(texto);
  zona.appendChild(entrada);
  zona.appendChild(vista);
  zona.appendChild(estado);

  function avisar(mensaje, esError) {
    estado.textContent = mensaje;
    estado.classList.toggle("es-error", !!esError);
  }

  function mostrar(archivo) {
    if (vista.src) URL.revokeObjectURL(vista.src);
    vista.src = URL.createObjectURL(archivo);
    vista.hidden = false;
    avisar("Foto lista: " + (archivo.name || "imagen pegada") + ". Pulsa Guardar para subirla.");
  }

  function aceptar(archivo) {
    if (!archivo) return;
    if (TIPOS.indexOf(archivo.type) === -1) {
      avisar("Solo se admiten imágenes JPG, PNG o WebP.", true);
      return;
    }
    if (archivo.size > MAX) {
      avisar("La imagen pesa más de 5 MB.", true);
      return;
    }
    var lote = new DataTransfer();
    lote.items.add(archivo);
    entrada.files = lote.files;
    mostrar(archivo);
  }

  function primeraImagen(lista) {
    for (var i = 0; lista && i < lista.length; i++) {
      if (lista[i].type.indexOf("image/") === 0) return lista[i];
    }
    return null;
  }

  entrada.addEventListener("change", function () {
    if (entrada.files && entrada.files[0]) aceptar(entrada.files[0]);
  });

  ["dragenter", "dragover"].forEach(function (nombre) {
    zona.addEventListener(nombre, function (e) {
      e.preventDefault();
      zona.classList.add("es-activa");
    });
  });
  ["dragleave", "drop"].forEach(function (nombre) {
    zona.addEventListener(nombre, function () {
      zona.classList.remove("es-activa");
    });
  });
  zona.addEventListener("drop", function (e) {
    e.preventDefault();
    var archivo = primeraImagen(e.dataTransfer && e.dataTransfer.files);
    if (archivo) aceptar(archivo);
    else avisar("No se pudo tomar esa imagen. Cópiala y pégala con Ctrl+V, o descárgala y búscala.", true);
  });

  // Soltar fuera de la zona no debe abrir la imagen y sacar al editor del formulario.
  ["dragover", "drop"].forEach(function (nombre) {
    window.addEventListener(nombre, function (e) { e.preventDefault(); });
  });

  // Pegar una imagen copiada (clic derecho → «Copiar imagen»), sin descargarla.
  document.addEventListener("paste", function (e) {
    var archivo = primeraImagen(e.clipboardData && e.clipboardData.files);
    if (archivo) {
      e.preventDefault();
      aceptar(archivo);
    }
  });
})();
