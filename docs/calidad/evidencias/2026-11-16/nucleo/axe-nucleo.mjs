// axe-core (WCAG 2.2 A/AA) y objetivos ≥ 24 px en las pantallas nuevas del núcleo.
// Uso: node axe-nucleo.mjs <salida.json> <cookie_reportante> <cookie_moderador> <perfil> <id_producto>
import { spawn } from "node:child_process";
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const AQUI = path.dirname(fileURLToPath(import.meta.url));
const [SALIDA, C_REP, C_MOD, PERFIL, PRODUCTO] = process.argv.slice(2);
const AXE = readFileSync(path.join(AQUI, "node_modules/axe-core/axe.min.js"), "utf8");
const BASE = "http://127.0.0.1:8000";
mkdirSync(PERFIL, { recursive: true });
const chrome = spawn("C:/Program Files/Google/Chrome/Application/chrome.exe", ["--headless=new", "--remote-debugging-port=9337", `--user-data-dir=${PERFIL}`, "--no-first-run", "about:blank"], { stdio: "ignore" });
const espera = (ms) => new Promise((r) => setTimeout(r, ms));
let ws, n = 0; const pend = new Map();
const cdp = (m, p = {}) => new Promise((res) => { const i = ++n; pend.set(i, res); ws.send(JSON.stringify({ id: i, method: m, params: p })); });
for (let k = 0; k < 60 && !ws; k++) { try { const t = (await (await fetch("http://127.0.0.1:9337/json/list")).json()).find((x) => x.type === "page"); if (t) { ws = new WebSocket(t.webSocketDebuggerUrl); await new Promise((r) => ws.addEventListener("open", r)); ws.addEventListener("message", (e) => { const m = JSON.parse(e.data); if (pend.has(m.id)) { pend.get(m.id)(m.result); pend.delete(m.id); } }); } } catch {} await espera(300); }
const ev = async (x) => (await cdp("Runtime.evaluate", { expression: x, awaitPromise: true, returnByValue: true })).result.value;
const sesion = async (cookie) => { await cdp("Network.clearBrowserCookies"); if (cookie) { const [a, b] = readFileSync(cookie, "utf8").trim().split("="); await cdp("Network.setCookie", { name: a, value: b, url: BASE }); } };
const PANTALLAS = [
  ["productos", "/productos/?q=a", null], ["comparacion-filtros", `/productos/${PRODUCTO}/`, C_REP],
  ["establecimientos", "/establecimientos/", null], ["sugerir-establecimiento", "/establecimientos/sugerir/", C_REP],
  ["solicitar-producto", "/catalogo/solicitar/", C_REP], ["mis-aportes", "/precios/mis-aportes/", C_REP],
  ["mis-datos", "/cuentas/mis-datos/", C_REP], ["suprimir-cuenta", "/cuentas/mis-datos/suprimir/", C_REP],
  ["recuperar-contrasena", "/cuentas/contrasena/recuperar/", null], ["bandeja-moderacion", "/moderacion/", C_MOD],
];
const r = {};
await cdp("Page.enable"); await cdp("Network.enable");
await cdp("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
for (const tema of ["light", "dark"]) {
  await cdp("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: tema }] });
  for (const [id, url, cookie] of PANTALLAS) {
    await sesion(cookie); await cdp("Page.navigate", { url: BASE + url }); await espera(1500);
    if (id === "comparacion-filtros") { await ev("document.querySelector('details.panel-plegable')?.setAttribute('open','')"); await espera(1200); }
    await ev(AXE + ";1");
    const v = await ev(`axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa']}}).then(x=>x.violations.map(v=>({id:v.id,nodos:v.nodes.map(n=>n.target.join(' '))})))`);
    const pequenos = await ev(`[...document.querySelectorAll('a[href],button,input:not([type=hidden]),select,textarea,summary')].filter(e=>{const b=e.getBoundingClientRect();const s=getComputedStyle(e);return b.width>0&&s.visibility!=='hidden'&&(b.width<24||b.height<24)&&!(e.tagName==='A'&&e.closest('p,li,td,dd')&&e.closest('p,li,td,dd').textContent.trim().length>e.textContent.trim().length+3)}).map(e=>e.tagName+' '+(e.textContent||e.name||'').trim().slice(0,30)+' '+Math.round(e.getBoundingClientRect().width)+'x'+Math.round(e.getBoundingClientRect().height))`);
    const url_final = await ev("location.pathname");
    r[`${id}-${tema === "light" ? "claro" : "oscuro"}`] = { url: url_final, violaciones: v, objetivos_menores_24px: pequenos };
  }
}
writeFileSync(SALIDA, JSON.stringify(r, null, 2));
for (const [k, v] of Object.entries(r)) console.log(k.padEnd(32), v.url.padEnd(30), "axe:", v.violaciones.map((x) => `${x.id}(${x.nodos.length})`).join(" ") || "0", "| <24px:", v.objetivos_menores_24px.join(", ") || "0");
ws.close(); chrome.kill(); await espera(500); process.exit(0);
