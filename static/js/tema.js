/* Apariencia: Automática (sigue al sistema), Clara u Oscura. Mejora progresiva: sin JS manda el
   sistema, como antes. La elección se guarda solo en este navegador (localStorage). WCAG 1.4.3 y 1.4.11
   se cumplen en ambos temas; esto solo permite elegir cuál ver. */
(() => {
  const CLAVE = "ahorrapues-tema";
  const raiz = document.documentElement;
  const sistema = window.matchMedia("(prefers-color-scheme: dark)");
  const leer = () => { try { return localStorage.getItem(CLAVE); } catch { return null; } };
  const guardar = (v) => { try { v ? localStorage.setItem(CLAVE, v) : localStorage.removeItem(CLAVE); } catch { /* sin almacenamiento */ } };
  const botones = document.querySelectorAll(".tema button[data-tema]");
  const alternar = document.querySelector(".tema-alternar");
  const avisos = document.getElementById("avisos");

  const efectivo = () => raiz.dataset.theme || (sistema.matches ? "dark" : "light");
  const pintar = () => {
    raiz.dataset.temaEfectivo = efectivo();
    const elegido = raiz.dataset.theme || "auto";
    botones.forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.tema === elegido)));
    if (alternar) alternar.setAttribute("aria-label", efectivo() === "dark" ? "Cambiar a modo claro" : "Cambiar a modo oscuro");
  };
  const aplicar = (valor, anunciar) => {
    if (valor === "light" || valor === "dark") raiz.dataset.theme = valor; else delete raiz.dataset.theme;
    guardar(valor === "light" || valor === "dark" ? valor : null);
    pintar();
    if (anunciar && avisos) {
      const texto = { light: "Apariencia: clara.", dark: "Apariencia: oscura.", auto: "Apariencia: automática, según tu dispositivo." }[valor] || "";
      avisos.textContent = ""; setTimeout(() => { avisos.textContent = texto; }, 50);
    }
  };

  botones.forEach((b) => b.addEventListener("click", () => aplicar(b.dataset.tema, true)));
  if (alternar) alternar.addEventListener("click", () => aplicar(efectivo() === "dark" ? "light" : "dark", true));
  sistema.addEventListener("change", pintar);
  pintar();
})();
