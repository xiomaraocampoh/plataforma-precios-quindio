// Auditoría WCAG 2.2 AA: Lighthouse (accesibilidad) + axe-core + pruebas de teclado.
// Uso: node auditar-a11y.mjs <dir_salida> <archivo_cookie_sesion>
import { spawn, spawnSync } from "node:child_process";
import { mkdirSync, readFileSync, writeFileSync, rmSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const AQUI = path.dirname(fileURLToPath(import.meta.url));
const [SALIDA, ARCHIVO_COOKIE] = process.argv.slice(2);
const BASE = "http://127.0.0.1:8000";
const CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe";
const COOKIE = readFileSync(ARCHIVO_COOKIE, "utf8").trim();
const [COOKIE_NOMBRE, COOKIE_VALOR] = COOKIE.split("=");
const AXE = readFileSync(path.join(AQUI, "node_modules/axe-core/axe.min.js"), "utf8");
const ETIQUETAS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];
mkdirSync(path.join(SALIDA, "lighthouse"), { recursive: true });
mkdirSync(path.join(SALIDA, "axe"), { recursive: true });

const PANTALLAS = [
  { id: "inicio", url: "/" },
  { id: "comparacion", url: "/productos/1/" },
  { id: "registro-precio", url: "/precios/registrar/", sesion: true },
  { id: "registro-cuenta", url: "/cuentas/registro/" },
  { id: "ingreso", url: "/cuentas/ingresar/" },
];

// ---------- 1. Lighthouse ----------
const resumenLH = {};
const cabeceras = path.join(SALIDA, "..", ".lh-cabeceras.json");
writeFileSync(cabeceras, JSON.stringify({ Cookie: COOKIE }));
for (const p of PANTALLAS) {
  const base = path.join(SALIDA, "lighthouse", p.id);
  const args = [
    path.join(AQUI, "node_modules/lighthouse/cli/index.js"), BASE + p.url,
    "--only-categories=accessibility", "--output=html", "--output=json", `--output-path=${base}`,
    "--chrome-flags=--headless=new --no-first-run", "--quiet", "--form-factor=mobile",
  ];
  if (p.sesion) args.push(`--extra-headers=${cabeceras}`);
  const r = spawnSync(process.execPath, args, { env: { ...process.env, CHROME_PATH: CHROME }, encoding: "utf8", timeout: 180000 });
  try {
    const j = JSON.parse(readFileSync(`${base}.report.json`, "utf8"));
    const fallos = Object.values(j.audits)
      .filter((a) => a.score === 0 && j.categories.accessibility.auditRefs.some((ref) => ref.id === a.id))
      .map((a) => ({ id: a.id, titulo: a.title, elementos: a.details?.items?.length ?? 0 }));
    resumenLH[p.id] = { url: j.finalDisplayedUrl, puntaje: Math.round(j.categories.accessibility.score * 100), fallos };
    rmSync(`${base}.report.json`); // el HTML ya contiene el informe completo
  } catch (e) {
    resumenLH[p.id] = { error: (r.stderr || String(e)).slice(-600) };
  }
}
rmSync(cabeceras);
writeFileSync(path.join(SALIDA, "lighthouse", "resumen.json"), JSON.stringify(resumenLH, null, 2));

// ---------- 2. axe-core + teclado vía CDP ----------
const PUERTO = 9334;
const perfil = path.join(SALIDA, "..", ".perfil-chrome");
const chrome = spawn(CHROME, ["--headless=new", `--remote-debugging-port=${PUERTO}`, `--user-data-dir=${perfil}`, "--no-first-run", "about:blank"], { stdio: "ignore" });
const espera = (ms) => new Promise((r) => setTimeout(r, ms));
let ws; let n = 0; const pend = new Map();
const cdp = (method, params = {}) => new Promise((res, rej) => { const i = ++n; pend.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method, params })); });
for (let k = 0; k < 60 && !ws; k++) {
  try {
    const t = (await (await fetch(`http://127.0.0.1:${PUERTO}/json/list`)).json()).find((x) => x.type === "page");
    if (t) {
      ws = new WebSocket(t.webSocketDebuggerUrl);
      await new Promise((r) => ws.addEventListener("open", r));
      ws.addEventListener("message", (e) => { const m = JSON.parse(e.data); if (m.id && pend.has(m.id)) { const { res, rej } = pend.get(m.id); pend.delete(m.id); m.error ? rej(new Error(m.error.message)) : res(m.result); } });
    }
  } catch {}
  await espera(300);
}
if (!ws) throw new Error('Chrome no expuso una página por CDP');
const ev = async (expr) => {
  const r = await cdp("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true });
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || JSON.stringify(r.exceptionDetails));
  return r.result.value;
};
const sesion = async (activa) => { await cdp("Network.clearBrowserCookies"); if (activa) await cdp("Network.setCookie", { name: COOKIE_NOMBRE, value: COOKIE_VALOR, url: BASE }); };
const ir = async (url) => { await cdp("Page.navigate", { url }); await espera(1400); };
const tecla = async (key, code, vk, mods = 0) => {
  for (const type of ["keyDown", "keyUp"]) await cdp("Input.dispatchKeyEvent", { type, key, code, windowsVirtualKeyCode: vk, modifiers: mods, ...(key === "Enter" && type === "keyDown" ? { text: "\r" } : {}) });
  await espera(120);
};
const escribir = async (texto) => { for (const c of texto) await cdp("Input.dispatchKeyEvent", { type: "char", text: c }); await espera(900); };
const axe = async () => {
  await ev(`window.axe || (()=>{ ${AXE}; })()`).catch(() => {});
  if (!(await ev("!!window.axe"))) await ev(AXE + ";1");
  return ev(`axe.run(document, { runOnly: { type: "tag", values: ${JSON.stringify(ETIQUETAS)} }, resultTypes: ["violations","incomplete"] })
    .then(r => ({ violaciones: r.violations.map(v => ({ id: v.id, impacto: v.impact, criterios: v.tags.filter(t => /^wcag\\d{3,4}$/.test(t)), ayuda: v.help, nodos: v.nodes.map(x => ({ selector: x.target.join(" "), resumen: x.failureSummary })) })),
                   revisar: r.incomplete.map(v => ({ id: v.id, nodos: v.nodes.length })) }))`);
};

const ESTADOS = [
  { id: "inicio", url: "/" },
  { id: "inicio-sugerencias", url: "/", accion: async () => { await ev("document.getElementById('q').focus()"); await escribir("arr"); } },
  { id: "comparacion", url: "/productos/1/" },
  { id: "registro-precio", url: "/precios/registrar/", sesion: true },
  { id: "registro-precio-errores", url: "/precios/registrar/", sesion: true, accion: async () => { await ev("document.querySelector('#registro button[type=submit]').click()"); await espera(1200); } },
  { id: "registro-precio-confirmacion", url: "/precios/registrar/", sesion: true, accion: async () => {
      await ev(`(() => { const s = (id) => document.getElementById(id); s('id_establecimiento').selectedIndex = 1; s('id_presentacion').selectedIndex = 2; s('id_precio').value = '4800'; document.querySelector('#registro button[type=submit]').click(); })()`); await espera(1500); } },
  { id: "registro-cuenta", url: "/cuentas/registro/" },
  { id: "registro-cuenta-errores", url: "/cuentas/registro/", accion: async () => { await ev("document.querySelector('main form button[type=submit]').click()"); await espera(1500); } },
  { id: "ingreso", url: "/cuentas/ingresar/" },
  { id: "ingreso-errores", url: "/cuentas/ingresar/", accion: async () => { await ev("document.querySelector('main form button[type=submit]').click()"); await espera(1500); } },
];

const resumenAxe = {};
const teclado = {};
try {
  await cdp("Page.enable"); await cdp("Runtime.enable"); await cdp("Network.enable");
  await cdp("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
  for (const tema of ["light", "dark"]) {
    await cdp("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: tema }] });
    for (const e of ESTADOS) {
      await sesion(!!e.sesion);
      await ir(BASE + e.url);
      if (e.accion) await e.accion();
      const r = await axe();
      r.url_auditada = await ev("location.pathname");
      const clave = `${e.id}-${tema === "light" ? "claro" : "oscuro"}`;
      writeFileSync(path.join(SALIDA, "axe", `${clave}.json`), JSON.stringify(r, null, 2));
      resumenAxe[clave] = { url: r.url_auditada, violaciones: r.violaciones.reduce((s, v) => s + v.nodos.length, 0), reglas: r.violaciones.map((v) => `${v.id}(${v.nodos.length})`), revisar: r.revisar.map((v) => v.id) };
    }
  }
  await cdp("Emulation.setEmulatedMedia", { features: [] });

  // ---------- 3. Teclado ----------
  const enfocado = `(() => { const e = document.activeElement; if (!e || e === document.body) return null; const s = getComputedStyle(e); const b = e.getBoundingClientRect();
      return { el: (e.tagName + (e.id ? '#' + e.id : '') + ' ' + (e.getAttribute('aria-label') || e.textContent || e.name || '').trim().replace(/\\s+/g, ' ')).slice(0, 60),
               foco_visible: (s.outlineStyle !== 'none' && parseFloat(s.outlineWidth) >= 1) || s.boxShadow !== 'none',
               contorno: s.outlineStyle + ' ' + s.outlineWidth + ' ' + s.outlineColor, tam: Math.round(b.width) + 'x' + Math.round(b.height) }; })()`;
  for (const p of PANTALLAS) {
    await sesion(!!p.sesion);
    await ir(BASE + p.url);
    await ev("document.activeElement && document.activeElement.blur()");
    const orden = []; const vistos = new Set();
    for (let i = 0; i < 45; i++) { await tecla("Tab", "Tab", 9); const f = await ev(enfocado); if (!f) continue; if (vistos.has(f.el)) break; vistos.add(f.el); orden.push(f); }
    teclado[p.id] = { recorrido_tab: orden, sin_foco_visible: orden.filter((f) => !f.foco_visible).map((f) => f.el), pequenos: orden.filter((f) => { const [w, h] = f.tam.split("x").map(Number); return w < 24 || h < 24; }).map((f) => `${f.el} ${f.tam}`) };
  }
  // Saltar al contenido: Tab + Enter debe llevar el foco a <main>
  await sesion(false); await ir(BASE + "/productos/1/"); await ev("document.activeElement.blur()");
  await tecla("Tab", "Tab", 9); const primero = await ev(enfocado); await tecla("Enter", "Enter", 13); await espera(400);
  teclado.saltar_contenido = { primer_tab: primero?.el, foco_tras_enter: await ev("document.activeElement.tagName + '#' + document.activeElement.id"), siguiente_tab: (await tecla("Tab", "Tab", 9), (await ev(enfocado))?.el) };
  // Buscador: escribir, bajar a una sugerencia con Tab, Enter navega; Esc limpia y oculta la lista
  await ir(BASE + "/"); await ev("document.getElementById('q').focus()"); await escribir("arr");
  const sug = await ev("[...document.querySelectorAll('#sugerencias li')].map(l => l.textContent.trim())");
  await tecla("Escape", "Escape", 27); await espera(1200);
  const trasEsc = await ev("({ valor: document.getElementById('q').value, items: [...document.querySelectorAll('#sugerencias li')].map(l => l.textContent.trim()), visible: getComputedStyle(document.getElementById('sugerencias')).display !== 'none' })");
  await escribir("arr"); await tecla("Tab", "Tab", 9); const enSug = await ev(enfocado); await tecla("Enter", "Enter", 13); await espera(1500);
  teclado.buscador = { sugerencias: sug, tras_esc: trasEsc, tab_desde_buscador: enSug?.el, url_tras_enter: await ev("location.pathname") };
  // Rotación del titular: ¿hay control para pausarla? (2.2.2)
  await ir(BASE + "/");
  teclado.rotacion = await ev(`(() => { const b = [...document.querySelectorAll('button')].find(x => /paus|deten|anima/i.test(x.textContent + (x.getAttribute('aria-label')||''))); const a = getComputedStyle(document.documentElement);
      return { rota_activa: !!document.querySelector('.rota-activa'), control_pausa: b ? b.textContent.trim() || b.getAttribute('aria-label') : null }; })()`);
  // Comparación: ¿se recarga sola? (2.2.2)
  await ir(BASE + "/productos/1/");
  teclado.recarga_automatica = await ev("[...document.querySelectorAll('[hx-trigger]')].map(e => e.id + ': ' + e.getAttribute('hx-trigger'))");
  // Espaciado de texto (1.4.12) y reflujo a 320 px (1.4.10)
  await cdp("Emulation.setDeviceMetricsOverride", { width: 320, height: 640, deviceScaleFactor: 1, mobile: true });
  const reflujo = {};
  for (const p of PANTALLAS) { await sesion(!!p.sesion); await ir(BASE + p.url); reflujo[p.id] = await ev("document.documentElement.scrollWidth <= innerWidth"); }
  await ir(BASE + "/");
  await ev(`(() => { const s = document.createElement('style'); s.textContent = '*{line-height:1.5!important;letter-spacing:.12em!important;word-spacing:.16em!important} p{margin-bottom:2em!important}'; document.head.appendChild(s); })()`);
  await espera(800);
  teclado.espaciado_texto = await ev("[...document.querySelectorAll('h1 *, .rota, .rota-palabra')].filter(e => e.scrollWidth > e.clientWidth + 2 && getComputedStyle(e).overflow !== 'visible').map(e => e.className)");
  teclado.reflujo_320 = reflujo;
} catch (e) {
  teclado.error = String(e.stack || e);
} finally {
  writeFileSync(path.join(SALIDA, "axe", "resumen.json"), JSON.stringify(resumenAxe, null, 2));
  writeFileSync(path.join(SALIDA, "teclado.json"), JSON.stringify(teclado, null, 2));
  try { ws?.close(); } catch {}
  chrome.kill();
  await espera(800);
  try { rmSync(perfil, { recursive: true, force: true }); } catch {}
  console.log(JSON.stringify({ lighthouse: Object.fromEntries(Object.entries(resumenLH).map(([k, v]) => [k, v.puntaje ?? v.error])), axe: resumenAxe }, null, 1));
  process.exit(0);
}
