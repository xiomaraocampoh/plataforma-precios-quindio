/* Escáner de códigos de barras (RF-04).
 * La imagen se decodifica en el navegador y NUNCA se envía: al servidor solo viajan los dígitos
 * (GET /escanear/?codigo=…). Usa BarcodeDetector si existe; si no, ZXing (cargado bajo demanda).
 * La cámara en vivo exige contexto seguro (HTTPS o localhost); sin ella queda «Tomar una foto». */
(function () {
  "use strict";
  var boton = document.querySelector("[data-escanear]");
  var dialogo = document.getElementById("escaner");
  if (!boton || !dialogo || typeof dialogo.showModal !== "function") {
    if (boton) boton.hidden = true; // sin <dialog>: queda la búsqueda por nombre
    return;
  }

  var video = dialogo.querySelector("video");
  var estado = dialogo.querySelector("[data-estado]");
  var foto = dialogo.querySelector("input[type=file]");
  var formatos = ["ean_13", "ean_8", "upc_a"];
  var flujo = null, lector = null, detector = null, activo = false, zxingCargado = null;

  function esGtinValido(c) {
    if (!/^\d+$/.test(c) || [8, 12, 13, 14].indexOf(c.length) < 0 || /^0+$/.test(c)) return false;
    var suma = 0, d = c.slice(0, -1).split("").reverse();
    for (var i = 0; i < d.length; i++) suma += Number(d[i]) * (i % 2 === 0 ? 3 : 1);
    return (10 - (suma % 10)) % 10 === Number(c.slice(-1));
  }

  function decir(texto) { estado.textContent = texto; }

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
    if (!zxingCargado) {
      zxingCargado = new Promise(function (ok, fallo) {
        var s = document.createElement("script");
        s.src = boton.dataset.zxing;
        s.onload = function () { ok(window.ZXing); };
        s.onerror = function () { zxingCargado = null; fallo(new Error("zxing")); };
        document.head.appendChild(s);
      });
    }
    return zxingCargado;
  }

  function nuevoLectorZxing(Z) {
    var pistas = new Map();
    pistas.set(Z.DecodeHintType.POSSIBLE_FORMATS,
      [Z.BarcodeFormat.EAN_13, Z.BarcodeFormat.EAN_8, Z.BarcodeFormat.UPC_A]);
    pistas.set(Z.DecodeHintType.TRY_HARDER, true);
    return new Z.BrowserMultiFormatReader(pistas, 300);
  }

  function detener() {
    activo = false;
    if (lector) { try { lector.reset(); } catch (e) { /* ya detenido */ } lector = null; }
    if (flujo) { flujo.getTracks().forEach(function (t) { t.stop(); }); flujo = null; }
    video.srcObject = null;
  }

  function bucleDetector() {
    if (!activo) return;
    detector.detect(video).then(function (r) {
      for (var i = 0; i < r.length; i++) if (aceptar(r[i].rawValue)) return;
      setTimeout(bucleDetector, 250);
    }).catch(function () { setTimeout(bucleDetector, 400); });
  }

  function iniciarCamara() {
    var hayCamara = window.isSecureContext && navigator.mediaDevices && navigator.mediaDevices.getUserMedia;
    video.hidden = true; // se muestra cuando la cámara ya entrega imagen
    if (!hayCamara) {
      decir("La cámara en vivo no está disponible aquí. Toma una foto del código o escríbelo abajo.");
      return;
    }
    decir("Pidiendo acceso a la cámara…");
    navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" }, audio: false })
      .then(function (s) {
        if (!dialogo.open) { s.getTracks().forEach(function (t) { t.stop(); }); return; }
        flujo = s; activo = true;
        video.srcObject = s;
        video.hidden = false;
        video.play();
        decir("Apunta al código de barras y mantén el celular quieto.");
        if ("BarcodeDetector" in window) {
          detector = new window.BarcodeDetector({ formats: formatos });
          bucleDetector();
        } else {
          cargarZxing().then(function (Z) {
            if (!activo) return;
            lector = nuevoLectorZxing(Z);
            lector.decodeFromStream(s, video, function (r) { if (r) aceptar(r.getText()); });
          }).catch(function () { decir("No pudimos cargar el lector. Toma una foto o escribe el código."); });
        }
      })
      .catch(function () {
        video.hidden = true;
        decir("No pudimos usar la cámara (¿negaste el permiso?). Toma una foto o escribe el código.");
      });
  }

  function leerFoto(archivo) {
    decir("Leyendo la foto…");
    var url = URL.createObjectURL(archivo);
    var fin = function () { URL.revokeObjectURL(url); };
    var noLeido = function () { decir("No encontramos un código en la foto. Acércate, mejora la luz o escríbelo abajo."); };
    if ("BarcodeDetector" in window) {
      var d = new window.BarcodeDetector({ formats: formatos });
      createImageBitmap(archivo).then(function (b) { return d.detect(b); }).then(function (r) {
        for (var i = 0; i < r.length; i++) if (aceptar(r[i].rawValue)) return;
        noLeido();
      }).catch(noLeido).then(fin);
    } else {
      cargarZxing().then(function (Z) {
        return nuevoLectorZxing(Z).decodeFromImageUrl(url);
      }).then(function (r) { if (!aceptar(r.getText())) noLeido(); })
        .catch(noLeido).then(fin);
    }
  }

  boton.addEventListener("click", function () {
    dialogo.showModal();
    iniciarCamara();
  });
  dialogo.addEventListener("close", detener);
  dialogo.querySelectorAll("[data-cerrar]").forEach(function (b) {
    b.addEventListener("click", function () { dialogo.close(); });
  });
  foto.addEventListener("change", function () {
    if (foto.files && foto.files[0]) leerFoto(foto.files[0]);
    foto.value = "";
  });
})();
