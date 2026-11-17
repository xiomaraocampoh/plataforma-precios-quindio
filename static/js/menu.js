/* Menú de hamburguesa de la cabecera (celular y tablet hasta 1023 px; en escritorio los enlaces van en línea).
   Patrón «disclosure»: el botón abre y cierra el panel con los enlaces principales.
   Accesible: aria-expanded, Esc cierra y devuelve el foco al botón, y se cierra al elegir un enlace
   o al tocar fuera. Sin JavaScript, los enlaces quedan visibles como siempre (clase .js en <html>). */
(() => {
  const cabecera = document.querySelector(".cabecera");
  const boton = cabecera && cabecera.querySelector(".menu-boton");
  const nav = document.getElementById("nav-principal");
  if (!boton || !nav) return;
  const icono = boton.querySelector("use");
  const escritorio = window.matchMedia("(min-width: 1024px)");

  const poner = (abierto, devolverFoco = false) => {
    cabecera.classList.toggle("menu-abierto", abierto);
    boton.setAttribute("aria-expanded", String(abierto));
    icono.setAttribute("href", abierto ? "#i-x" : "#i-menu");
    if (!abierto && devolverFoco) boton.focus();
  };

  boton.addEventListener("click", () => poner(boton.getAttribute("aria-expanded") !== "true"));
  nav.addEventListener("click", (e) => { if (e.target.closest("a")) poner(false); });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && boton.getAttribute("aria-expanded") === "true") poner(false, true);
  });
  document.addEventListener("click", (e) => {
    if (boton.getAttribute("aria-expanded") === "true" && !cabecera.contains(e.target)) poner(false);
  });
  escritorio.addEventListener("change", (e) => { if (e.matches) poner(false); });
})();
