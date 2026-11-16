/* Pantalla de escaneo (RF-04): código de barras y, si está activada, foto del producto con IA.
 *
 * Privacidad:
 *  - Código de barras: la imagen se decodifica en el navegador; al servidor solo viajan los
 *    dígitos (GET /escanear/?codigo=…).
 *  - Foto del producto (ADR-019): se reduce a 1024 px y se recodifica aquí (se pierde el EXIF,
 *    incluida la ubicación) antes de enviarla; el servidor no la guarda.
 * La cámara en vivo exige contexto seguro (HTTPS o localhost). Sin ella queda la foto/galería. */
(function () {
  "use strict";
  var boton = document.querySelector("[data-escanear]");
  var dlg = document.getElementById("escaner");
  if (!boton || !dlg || typeof dlg.showModal !== "function") {
    if (boton) boton.hidden = true; // sin <dialog>: queda la búsqueda por nombre
    return;
  }
  function $(s) { return dlg.querySelector(s); }
  var video = $("video"), guia = $("[data-estado]"), hoja = $("[data-hoja]");
  var salida = $("[data-resultado]"), vacio = $("[data-vacio]"), manual = $("[data-manual]");
  var disparador = $("[data-disparar]"), teclado = $("[data-teclado]");
  var galeria = $("[data-galeria]"), captura = $("[data-captura]");
  var urlIA = dlg.getAttribute("data-foto-url") || "";
  var hayIA = urlIA !== "";
  var formatos = ["ean_13", "ean_8", "upc_a"];
  var modo = hayIA ? "producto" : "codigo";
  var flujo = null, lector = null, detector = null, activo = false, zxing = null, enVivo = false;

  /* ---------- utilidades ---------- */
  function esGtinValido(c) {
    if (!/^\d+$/.test(c) || [8, 12, 13, 14].indexOf(c.length) < 0 || /^0+$/.test(c)) return false;
    var suma = 0, d = c.slice(0, -1).split("").reverse();
    for (var i = 0; i < d.length; i++) suma += Number(d[i]) * (i % 2 === 0 ? 3 : 1);
    return (10 - (suma % 10)) % 10 === Number(c.slice(-1));
  }
  function csrf() {
    try { return JSON.parse(document.body.getAttribute("hx-headers"))["X-CSRFToken"]; }
    catch (e) { return ""; }
  }
  function decir(t) { guia.textContent = t; }
  function textoGuia() {
    if (dlg.hasAttribute("data-sincamara")) { decir(""); return; }
    decir(modo === "producto" ? "Encuadra el producto completo y toca el botón"
                              : "Alinea el código de barras dentro del marco");
  }
  function mostrarHoja(html, esHtml) {
    if (esHtml) salida.innerHTML = html; else salida.textContent = html; // html: fragmento propio
    hoja.hidden = false;
  }
  function cerrarHoja() { hoja.hidden = true; salida.textContent = ""; }

  /* ---------- modos ---------- */
  function ponerModo(m) {
    modo = m;
    dlg.setAttribute("data-modo", m);
    dlg.querySelectorAll("[data-modo]").forEach(function (b) {
      if (b !== dlg) b.setAttribute("aria-pressed", String(b.getAttribute("data-modo") === m));
    });
    cerrarHoja();
    textoGuia();
    if (m === "codigo" && activo) arrancarLectura();
  }
  dlg.querySelectorAll("button[data-modo]").forEach(function (b) {
    b.addEventListener("click", function () { ponerModo(b.getAttribute("data-modo")); });
  });

  /* ---------- código de barras ---------- */
  function terminar(codigo) {
    detener();
    window.location.href = boton.dataset.destino + "?codigo=" + encodeURIComponent(codigo);
  }
  function aceptar(crudo) {
    var codigo = String(crudo || "").replace(/\D/g, "");
    if (esGtinValido(codigo)) { terminar(codigo); return true; }
    return false;
  }
  function cargarZxing() {
    if (window.ZXing) return Promise.resolve(window.ZXing);
    if (!zxing) {
      zxing = new Promise(function (ok, fallo) {
        var s = document.createElement("script");
        s.src = boton.dataset.zxing;
        s.onload = function () { ok(window.ZXing); };
        s.onerror = function () { zxing = null; fallo(new Error("zxing")); };
        document.head.appendChild(s);
      });
    }
    return zxing;
  }
  function nuevoLectorZxing(Z) {
    var pistas = new Map();
    pistas.set(Z.DecodeHintType.POSSIBLE_FORMATS,
      [Z.BarcodeFormat.EAN_13, Z.BarcodeFormat.EAN_8, Z.BarcodeFormat.UPC_A]);
    pistas.set(Z.DecodeHintType.TRY_HARDER, true);
    return new Z.BrowserMultiFormatReader(pistas, 300);
  }
  function bucleDetector() {
    if (!activo || modo !== "codigo") return;
    detector.detect(video).then(function (r) {
      for (var i = 0; i < r.length; i++) if (aceptar(r[i].rawValue)) return;
      setTimeout(bucleDetector, 250);
    }).catch(function () { setTimeout(bucleDetector, 400); });
  }
  function arrancarLectura() {
    if (!flujo || modo !== "codigo") return;
    if ("BarcodeDetector" in window) {
      detector = detector || new window.BarcodeDetector({ formats: formatos });
      bucleDetector();
    } else if (!lector) {
      cargarZxing().then(function (Z) {
        if (!activo) return;
        lector = nuevoLectorZxing(Z);
        lector.decodeFromStream(flujo, video, function (r) {
          if (r && modo === "codigo") aceptar(r.getText());
        });
      }).catch(function () { decir("No pudimos cargar el lector. Toma una foto o escribe el código."); });
    }
  }
  function leerCodigoDeArchivo(archivo, alNoEncontrar) {
    var url = URL.createObjectURL(archivo);
    var fin = function () { URL.revokeObjectURL(url); };
    var noLeido = alNoEncontrar || function () {
      textoGuia();
      mostrarHoja("No encontramos un código de barras en la imagen. Acércate, mejora la luz o escribe el número.");
    };
    if (!alNoEncontrar) decir("Leyendo la imagen…");
    if ("BarcodeDetector" in window) {
      var d = new window.BarcodeDetector({ formats: formatos });
      createImageBitmap(archivo).then(function (b) { return d.detect(b); }).then(function (r) {
        for (var i = 0; i < r.length; i++) if (aceptar(r[i].rawValue)) return;
        noLeido();
      }).catch(noLeido).then(fin);
    } else {
      cargarZxing().then(function (Z) { return nuevoLectorZxing(Z).decodeFromImageUrl(url); })
        .then(function (r) { if (!aceptar(r.getText())) noLeido(); })
        .catch(noLeido).then(fin);
    }
  }

  /* ---------- foto del producto con IA ---------- */
  function reducir(fuente, ancho, alto) {
    var k = Math.min(1, 1024 / Math.max(ancho, alto));
    var c = document.createElement("canvas");
    c.width = Math.round(ancho * k); c.height = Math.round(alto * k);
    c.getContext("2d").drawImage(fuente, 0, 0, c.width, c.height);
    return new Promise(function (ok) { c.toBlob(ok, "image/jpeg", 0.85); });
  }
  function enviarIA(blobPromesa) {
    mostrarHoja("Identificando el producto…");
    blobPromesa.then(function (blob) {
      var datos = new FormData();
      datos.append("foto", blob, "foto.jpg");
      return fetch(urlIA, { method: "POST", body: datos, headers: { "X-CSRFToken": csrf() }, credentials: "same-origin" });
    }).then(function (r) { return r.text(); })
      .then(function (html) { mostrarHoja(html, true); })
      .catch(function () { mostrarHoja("No pudimos enviar la foto. Busca por nombre o con el código de barras."); });
  }
  function fotogramaActual() {
    if (!enVivo || !video.videoWidth) return null;
    return reducir(video, video.videoWidth, video.videoHeight);
  }

  /* ---------- una imagen que llega por galería, cámara del sistema, pegado o arrastre ---------- */
  function procesarArchivo(archivo) {
    if (!dlg.open) dlg.showModal();
    if (hayIA && modo === "producto") {
      enviarIA(createImageBitmap(archivo).then(function (b) { return reducir(b, b.width, b.height); }));
    } else {
      leerCodigoDeArchivo(archivo);
    }
  }
  function alElegir(entrada) {
    entrada.addEventListener("change", function () {
      var a = entrada.files && entrada.files[0];
      entrada.value = "";
      if (a) procesarArchivo(a);
    });
  }
  alElegir(galeria);
  alElegir(captura);

  disparador.addEventListener("click", function () {
    var foto = fotogramaActual();
    if (foto && hayIA && modo === "producto") enviarIA(foto);
    else if (!enVivo) captura.click(); // sin cámara en vivo: abre la cámara del sistema
  });

  teclado.addEventListener("click", function () {
    var abrir = manual.hidden;
    manual.hidden = !abrir;
    teclado.setAttribute("aria-expanded", String(abrir));
    if (abrir) { cerrarHoja(); $("#codigo-manual").focus(); }
  });
  $("[data-otra]").addEventListener("click", function () { cerrarHoja(); textoGuia(); });

  /* ---------- pegar y arrastrar ---------- */
  function imagenDe(t) {
    var lista = t && t.files ? Array.prototype.slice.call(t.files) : [];
    return lista.filter(function (a) { return /^image\//.test(a.type); })[0] || null;
  }
  /* Foto pegada en la página: miniatura junto al buscador; Enter (o «Buscar») la identifica ahí mismo. */
  var buscador = document.getElementById("q");
  var chip = document.querySelector("[data-adjunto]");
  var barra = document.querySelector("[data-buscador]");
  var ident = document.querySelector("[data-buscar-adjunto]");
  var marcador = buscador ? buscador.getAttribute("placeholder") : "";
  function marcarAdjunto(si) {
    if (barra) barra.classList.toggle("con-foto", si);
    if (ident) ident.hidden = !si;
    if (chip) chip.hidden = !si;
    if (buscador) buscador.setAttribute("placeholder", si ? "Enter para identificar" : marcador);
  }
  var panel = document.querySelector("[data-pagina-resultado]");
  var adjunto = null, urlMiniatura = "";
  function ponerPanel(html, esHtml) {
    if (!panel) return;
    if (esHtml) panel.innerHTML = html; else panel.textContent = html; // html: fragmento propio
    panel.hidden = !panel.textContent.trim() && !panel.children.length;
  }
  function quitarAdjunto() {
    adjunto = null;
    if (urlMiniatura) { URL.revokeObjectURL(urlMiniatura); urlMiniatura = ""; }
    marcarAdjunto(false);
  }
  function adjuntar(archivo) {
    quitarAdjunto();
    adjunto = archivo;
    urlMiniatura = URL.createObjectURL(archivo);
    chip.querySelector("img").src = urlMiniatura;
    marcarAdjunto(true);
    ponerPanel("");
    if (buscador) buscador.focus();
  }
  function buscarAdjunto() {
    if (!adjunto) return;
    var archivo = adjunto;
    ponerPanel("Identificando el producto…");
    if (hayIA) {
      createImageBitmap(archivo).then(function (b) { return reducir(b, b.width, b.height); })
        .then(function (blob) {
          var datos = new FormData();
          datos.append("foto", blob, "foto.jpg");
          return fetch(urlIA, { method: "POST", body: datos, headers: { "X-CSRFToken": csrf() }, credentials: "same-origin" });
        }).then(function (r) { return r.text(); })
        .then(function (html) { ponerPanel(html, true); })
        .catch(function () { ponerPanel("No pudimos enviar la foto. Busca por nombre o con el código de barras."); });
    } else {
      leerCodigoDeArchivo(archivo, function () {
        ponerPanel("No encontramos un código de barras en la imagen. Escribe el nombre del producto o prueba otra foto.");
      });
    }
  }
  if (chip) {
    ident.addEventListener("click", buscarAdjunto);
    chip.querySelector("[data-quitar-adjunto]").addEventListener("click", function () {
      quitarAdjunto(); ponerPanel(""); if (buscador) buscador.focus();
    });
  }
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && panel && !panel.hidden && !dlg.open) ponerPanel("");
  });
  if (buscador) {
    buscador.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && adjunto) { e.preventDefault(); buscarAdjunto(); }
    });
    buscador.addEventListener("input", function () { if (panel && buscador.value) ponerPanel(""); });
  }

  document.addEventListener("paste", function (e) {
    var archivo = imagenDe(e.clipboardData);
    if (!archivo) return; // texto: comportamiento normal
    if (dlg.open) { e.preventDefault(); procesarArchivo(archivo); return; }
    var activo = document.activeElement;
    var libre = !activo || activo === document.body || activo.id === "q";
    if (chip && libre) { e.preventDefault(); adjuntar(archivo); }
  });
  ["dragover", "drop"].forEach(function (tipo) {
    dlg.addEventListener(tipo, function (e) {
      var archivo = imagenDe(e.dataTransfer);
      if (!archivo && tipo === "drop") return;
      e.preventDefault();
      if (tipo === "drop") procesarArchivo(archivo);
    });
  });

  /* ---------- cámara en vivo ---------- */
  function detener() {
    activo = false; enVivo = false;
    if (lector) { try { lector.reset(); } catch (e) { /* ya detenido */ } lector = null; }
    if (flujo) { flujo.getTracks().forEach(function (t) { t.stop(); }); flujo = null; }
    video.srcObject = null;
    dlg.removeAttribute("data-camara");
  }
  function sinCamara(texto) {
    video.hidden = true; vacio.hidden = false;
    dlg.setAttribute("data-sincamara", "");
    vacio.querySelector("p").textContent = texto;
    decir("");
  }
  function iniciarCamara() {
    var puede = window.isSecureContext && navigator.mediaDevices && navigator.mediaDevices.getUserMedia;
    dlg.removeAttribute("data-sincamara");
    if (!puede) { sinCamara("La cámara en vivo no está disponible aquí. Toma una foto, elige una imagen o escribe el código."); return; }
    video.hidden = false; vacio.hidden = true;
    decir("Pidiendo acceso a la cámara…");
    navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" }, audio: false })
      .then(function (s) {
        if (!dlg.open) { s.getTracks().forEach(function (t) { t.stop(); }); return; }
        flujo = s; activo = true; enVivo = true;
        dlg.setAttribute("data-camara", "");
        video.srcObject = s;
        video.play();
        textoGuia();
        arrancarLectura();
      })
      .catch(function () { sinCamara("No pudimos usar la cámara (¿negaste el permiso?). Toma una foto, elige una imagen o escribe el código."); });
  }

  /* ---------- abrir y cerrar ---------- */
  boton.addEventListener("click", function () {
    cerrarHoja(); manual.hidden = true;
    ponerModo(modo);
    dlg.showModal();
    iniciarCamara();
  });
  dlg.addEventListener("close", function () { detener(); cerrarHoja(); });
  dlg.querySelectorAll("[data-cerrar]").forEach(function (b) {
    b.addEventListener("click", function () { dlg.close(); });
  });
})();
