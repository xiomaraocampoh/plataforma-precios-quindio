/* Apariencia: el botón de sol/luna (en la barra, o dentro del menú ☰ en celulares angostos) alterna entre clara y oscura. Sin elegir nada, manda el
   dispositivo (automático). Mejora progresiva: sin JS manda el dispositivo. La elección se guarda solo en
   este navegador (localStorage). WCAG 1.4.3 y 1.4.11 se cumplen en ambos temas. */
(() => {
  const CLAVE = "ahorrapues-tema";
  const raiz = document.documentElement;
  const sistema = window.matchMedia("(prefers-color-scheme: dark)");
  const guardar = (v) => { try { v ? localStorage.setItem(CLAVE, v) : localStorage.removeItem(CLAVE); } catch { /* sin almacenamiento */ } };
  const botones = document.querySelectorAll("[data-tema-alternar]");
  const avisos = document.getElementById("avisos");

  const efectivo = () => raiz.dataset.theme || (sistema.matches ? "dark" : "light");
  const pintar = () => {
    raiz.dataset.temaEfectivo = efectivo();
    const oscuro = efectivo() === "dark";
    botones.forEach((b) => {
      b.setAttribute("aria-label", oscuro ? "Cambiar a modo claro" : "Cambiar a modo oscuro");
      const texto = b.querySelector(".tema-texto");
      if (texto) texto.textContent = oscuro ? "Modo claro" : "Modo oscuro"; // dice lo que hará
    });
  };
  const aplicar = (valor) => {
    raiz.dataset.theme = valor;
    guardar(valor);
    pintar();
    if (avisos) {
      avisos.textContent = "";
      setTimeout(() => { avisos.textContent = valor === "dark" ? "Apariencia: oscura." : "Apariencia: clara."; }, 50);
    }
  };

  botones.forEach((b) => b.addEventListener("click", () => aplicar(efectivo() === "dark" ? "light" : "dark")));
  sistema.addEventListener("change", pintar);
  pintar();
})();
