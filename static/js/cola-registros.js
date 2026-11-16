/* Registro de precios sin conexión (RF-12, RNF-15, ADR-009, M-22). Sin dependencias.

   - Cada formulario [data-cola-registros] lleva un id_cliente (crypto.randomUUID).
   - Si el envío falla por red (sin señal, error de red o más de 15 s), el registro se guarda en
     localStorage con la hora en que se vio el precio y el formulario queda listo para otro.
   - La cola se reenvía al cargar cualquier página con sesión, al evento "online" y con el botón
     «Enviar ahora». El servidor es idempotente por id_cliente: si el primer envío sí llegó y solo
     se perdió la respuesta, el reenvío no crea un segundo registro.
   - El aviso vive en #registros-pendientes (role="status", aria-live="polite"; WCAG 4.1.3).
   - La cola es por usuario: en un celular compartido nadie envía registros ajenos (M-14).
   Mejora progresiva: sin JS o sin localStorage el formulario funciona como siempre. */
(() => {
  const script = document.currentScript;
  const region = document.getElementById("registros-pendientes");
  if (!script || !region) return;

  const URL_REGISTRO = script.dataset.urlRegistro;
  const CLAVE = `ahorrapues:registros-pendientes:v1:${script.dataset.usuario}`;
  const MARCA_GUARDADO = "data-registro-guardado";

  // ---------- id_cliente ----------
  const nuevoId = () => {
    if (window.crypto && typeof crypto.randomUUID === "function") return crypto.randomUUID();
    // randomUUID solo existe en contexto seguro (https o localhost): UUID v4 equivalente
    const b = crypto.getRandomValues(new Uint8Array(16));
    b[6] = (b[6] & 0x0f) | 0x40;
    b[8] = (b[8] & 0x3f) | 0x80;
    const h = [...b].map((x) => x.toString(16).padStart(2, "0")).join("");
    return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`;
  };

  const asignarIds = () => {
    document.querySelectorAll("form[data-cola-registros]").forEach((form) => {
      const campo = form.elements.namedItem("id_cliente");
      if (campo && !campo.value) campo.value = nuevoId();  // con errores se conserva el mismo
    });
  };

  // ---------- almacenamiento (puede fallar: modo privado, cuota, bloqueo) ----------
  const leer = () => {
    try {
      const lista = JSON.parse(localStorage.getItem(CLAVE) || "[]");
      return Array.isArray(lista) ? lista : [];
    } catch {
      return [];
    }
  };
  const escribir = (lista) => {
    try {
      if (lista.length) localStorage.setItem(CLAVE, JSON.stringify(lista));
      else localStorage.removeItem(CLAVE);
      return true;
    } catch {
      return false;
    }
  };
  const quitar = (idCliente) => escribir(leer().filter((r) => r.id_cliente !== idCliente));

  // ---------- aviso visible y anunciado ----------
  const plural = (n, uno, varios) => (n === 1 ? uno : varios);
  const textoPendientes = (n) =>
    `${n} ${plural(n, "registro pendiente", "registros pendientes")} de enviar`;
  let ultimoAviso = "";

  const pintar = ({ titulo, detalle = "", tipo = "", boton = false }) => {
    const huella = [titulo, detalle, tipo, boton].join("|");
    if (huella === ultimoAviso) return;  // no repetir el anuncio si nada cambió
    ultimoAviso = huella;
    region.replaceChildren();
    if (!titulo) return;

    const caja = document.createElement("div");
    caja.className = `aviso-pendientes ${tipo}`.trim();
    const icono = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    icono.setAttribute("class", "ico");
    icono.setAttribute("aria-hidden", "true");
    const uso = document.createElementNS("http://www.w3.org/2000/svg", "use");
    uso.setAttribute("href", tipo === "aviso-ok" ? "#i-check" : tipo === "aviso-error" ? "#i-info" : "#i-clock");
    icono.append(uso);

    const textos = document.createElement("div");
    const fuerte = document.createElement("p");
    fuerte.className = "aviso-titulo";
    fuerte.textContent = titulo;
    textos.append(fuerte);
    if (detalle) {
      const p = document.createElement("p");
      p.textContent = detalle;
      textos.append(p);
    }
    caja.append(icono, textos);
    if (boton) {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "btn btn-sec";
      b.textContent = "Enviar ahora";
      b.addEventListener("click", enviarPendientes);
      caja.append(b);
    }
    region.append(caja);
  };

  const pintarCola = (detalle) => {
    const n = leer().length;
    if (!n) return pintar({ titulo: "" });
    pintar({
      titulo: textoPendientes(n),
      detalle: detalle || "Están guardados en este celular y se enviarán solos cuando vuelva la conexión.",
      boton: navigator.onLine,
    });
  };

  // ---------- encolar un envío que falló por red ----------
  const textoOpcion = (form, nombre) => {
    const campo = form.elements.namedItem(nombre);
    return campo && campo.selectedOptions && campo.selectedOptions[0]
      ? campo.selectedOptions[0].textContent.trim() : "";
  };

  const encolar = (form) => {
    const datos = new FormData(form);
    const registro = {
      id_cliente: datos.get("id_cliente") || nuevoId(),
      establecimiento: datos.get("establecimiento"),
      presentacion: datos.get("presentacion"),
      precio: datos.get("precio"),
      fecha_observacion: new Date().toISOString(),  // la hora en que se vio el precio (RN-08)
      etiqueta: `${textoOpcion(form, "presentacion")} en ${textoOpcion(form, "establecimiento")}`,
    };
    const lista = leer().filter((r) => r.id_cliente !== registro.id_cliente);
    if (!escribir([...lista, registro])) {
      pintar({
        titulo: "No hay conexión y no pudimos guardar el precio en este celular",
        detalle: "Tus datos siguen en el formulario. Inténtalo de nuevo cuando tengas señal.",
        tipo: "aviso-error",
      });
      return;
    }
    // Listo para el siguiente precio en la misma tienda
    for (const nombre of ["presentacion", "precio"]) {
      const campo = form.elements.namedItem(nombre);
      if (campo) campo.value = "";
    }
    form.elements.namedItem("id_cliente").value = nuevoId();
    pintarCola("Sin conexión: guardamos tu precio en este celular y lo enviaremos al volver la señal.");
    form.elements.namedItem("presentacion")?.focus();
    region.scrollIntoView({ block: "nearest" });  // que el aviso se vea también en pantallas bajas
  };

  const esFormularioDeCola = (elt) => elt && elt.matches && elt.matches("form[data-cola-registros]");

  document.body.addEventListener("htmx:beforeRequest", (evento) => {
    const form = evento.detail.elt;
    if (esFormularioDeCola(form) && !navigator.onLine) {
      evento.preventDefault();  // sin señal: no esperar a que la petición falle
      encolar(form);
    }
  });
  for (const nombre of ["htmx:sendError", "htmx:timeout"]) {
    document.body.addEventListener(nombre, (evento) => {
      if (esFormularioDeCola(evento.detail.elt)) encolar(evento.detail.elt);
    });
  }
  document.body.addEventListener("htmx:afterSwap", asignarIds);

  // ---------- reenvío ----------
  const tokenCsrf = () => {
    try {
      return JSON.parse(document.body.getAttribute("hx-headers") || "{}")["X-CSRFToken"] || "";
    } catch {
      return "";
    }
  };

  // "guardado": el servidor lo tiene · "rechazado": respondió con errores · "pendiente": reintentar
  const enviar = async (registro) => {
    const cuerpo = new URLSearchParams();
    for (const campo of ["establecimiento", "presentacion", "precio", "id_cliente", "fecha_observacion"]) {
      cuerpo.append(campo, registro[campo] ?? "");
    }
    try {
      const respuesta = await fetch(URL_REGISTRO, {
        method: "POST",
        body: cuerpo,
        credentials: "same-origin",
        headers: { "X-CSRFToken": tokenCsrf(), "HX-Request": "true" },
      });
      // Redirección = sesión vencida (va al ingreso); 403, 429 y 5xx: se reintenta más tarde
      if (respuesta.redirected || !respuesta.ok) return "pendiente";
      return (await respuesta.text()).includes(MARCA_GUARDADO) ? "guardado" : "rechazado";
    } catch {
      return "pendiente";  // sin red
    }
  };

  let enviando = false;
  async function enviarPendientes() {
    if (enviando || !leer().length) return pintarCola();
    enviando = true;
    let enviados = 0;
    const rechazados = [];
    try {
      for (const registro of leer()) {
        const resultado = await enviar(registro);
        if (resultado === "pendiente") break;  // se intenta de nuevo con "online" o al recargar
        quitar(registro.id_cliente);
        if (resultado === "guardado") enviados += 1;
        else rechazados.push(registro.etiqueta);
      }
    } finally {
      enviando = false;
    }
    if (leer().length) return pintarCola();
    if (rechazados.length) {
      return pintar({
        titulo: `${rechazados.length} ${plural(rechazados.length, "registro no se pudo guardar", "registros no se pudieron guardar")}`,
        detalle: `El servidor los rechazó (por ejemplo, el precio ya venció o se alcanzó el límite por hora): ${rechazados.join("; ")}. Regístralos de nuevo si siguen vigentes.`,
        tipo: "aviso-error",
      });
    }
    if (enviados) {
      pintar({
        titulo: `${plural(enviados, "Se envió tu registro pendiente", `Se enviaron tus ${enviados} registros pendientes`)}`,
        detalle: "Gracias por aportar.",
        tipo: "aviso-ok",
      });
    }
  }

  window.addEventListener("online", enviarPendientes);
  window.addEventListener("offline", () => pintarCola());
  window.addEventListener("storage", (e) => { if (e.key === CLAVE) pintarCola(); });  // otra pestaña

  asignarIds();
  enviarPendientes();  // al cargar la página
})();
