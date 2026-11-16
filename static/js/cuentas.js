/* Ingreso y registro: mejoras que solo ayudan (todo funciona igual sin JavaScript).
   El servidor siempre valida; esto solo adelanta pistas y evita errores de uso. */
(() => {
  // 1. Llevar la atención al resumen de errores al volver a cargar la página
  const resumen = document.getElementById("resumen-errores");
  if (resumen) resumen.focus();

  // 2. Mostrar u ocultar la contraseña
  document.querySelectorAll("[data-ver-clave]").forEach((boton) => {
    const campo = document.getElementById(boton.getAttribute("aria-controls"));
    if (!campo) return;
    boton.hidden = false; // nace oculto: sin JavaScript no hay un botón que no funcione
    boton.addEventListener("click", () => {
      const visible = campo.type === "text";
      campo.type = visible ? "password" : "text";
      boton.textContent = visible ? "Mostrar" : "Ocultar";
      boton.setAttribute("aria-pressed", String(!visible));
      boton.setAttribute("aria-label", (visible ? "Mostrar" : "Ocultar") + " contraseña");
    });
  });

  // 3. Requisitos de la contraseña, en vivo (solo una pista; decide el servidor)
  const clave = document.getElementById("id_password1");
  const repite = document.getElementById("id_password2");
  const reglas = document.querySelectorAll("[data-regla]");
  if (clave && reglas.length) {
    const cumple = {
      "largo": () => clave.value.length >= 8,
      "no-numerica": () => clave.value.length > 0 && !/^\d+$/.test(clave.value),
      "coinciden": () => clave.value.length > 0 && !!repite && clave.value === repite.value,
    };
    const actualizar = () => {
      reglas.forEach((item) => {
        const ok = (cumple[item.dataset.regla] || (() => false))();
        item.classList.toggle("cumple", ok);
        const estado = item.querySelector(".estado");
        if (estado) estado.textContent = ok ? " (cumplido)" : " (pendiente)";
      });
    };
    clave.addEventListener("input", actualizar);
    if (repite) repite.addEventListener("input", actualizar);
    actualizar();
  }

  // 4. Enviar una sola vez y avisar que está trabajando
  document.querySelectorAll("form[data-una-vez]").forEach((formulario) => {
    const boton = formulario.querySelector("[type=submit]");
    if (!boton) return;
    const original = boton.textContent;
    formulario.addEventListener("submit", () => {
      boton.disabled = true;
      boton.textContent = boton.dataset.enviando || "Enviando…";
    });
    // Si la persona vuelve con «Atrás», el botón no debe quedar bloqueado
    window.addEventListener("pageshow", () => {
      boton.disabled = false;
      boton.textContent = original;
    });
  });
})();
