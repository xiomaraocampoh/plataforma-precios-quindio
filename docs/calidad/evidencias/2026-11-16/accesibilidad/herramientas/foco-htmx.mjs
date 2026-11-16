// 2.4.3 / 4.1.3: foco y anuncios tras los intercambios HTMX del registro de precio y la comparación.
import { spawn } from "node:child_process"; import { readFileSync, writeFileSync, mkdirSync } from "node:fs"; import path from "node:path";
const [SALIDA, COOKIE_F, PERFIL] = process.argv.slice(2); const [cn, cv] = readFileSync(COOKIE_F, "utf8").trim().split("=");
mkdirSync(PERFIL, { recursive: true });
const chrome = spawn("C:/Program Files/Google/Chrome/Application/chrome.exe", ["--headless=new", "--remote-debugging-port=9336", `--user-data-dir=${PERFIL}`, "--no-first-run", "about:blank"], { stdio: "ignore" });
const espera = (ms) => new Promise((r) => setTimeout(r, ms)); let ws, n = 0; const pend = new Map();
const cdp = (m, p = {}) => new Promise((res) => { const i = ++n; pend.set(i, res); ws.send(JSON.stringify({ id: i, method: m, params: p })); });
for (let k = 0; k < 60 && !ws; k++) { try { const t = (await (await fetch("http://127.0.0.1:9336/json/list")).json()).find((x) => x.type === "page"); if (t) { ws = new WebSocket(t.webSocketDebuggerUrl); await new Promise((r) => ws.addEventListener("open", r)); ws.addEventListener("message", (e) => { const m = JSON.parse(e.data); if (pend.has(m.id)) { pend.get(m.id)(m.result); pend.delete(m.id); } }); } } catch {} await espera(300); }
const ev = async (x) => (await cdp("Runtime.evaluate", { expression: x, awaitPromise: true, returnByValue: true })).result.value;
const ir = async (u) => { await cdp("Page.navigate", { url: "http://127.0.0.1:8000" + u }); await espera(1500); };
const foco = "(() => { const e = document.activeElement; return { elemento: e.tagName + (e.id ? '#' + e.id : ''), texto: (e.textContent || '').trim().slice(0, 60), avisos: document.getElementById('avisos').textContent }; })()";
const r = {};
await cdp("Page.enable"); await cdp("Network.enable"); await cdp("Network.setCookie", { name: cn, value: cv, url: "http://127.0.0.1:8000" });
await ir("/precios/registrar/");
await ev("document.querySelector('#registro button[type=submit]').click()"); await espera(1500);
r.registro_con_errores = await ev(foco);
await ev("(() => { const s = (i) => document.getElementById(i); s('id_establecimiento').selectedIndex = 1; s('id_presentacion').selectedIndex = 2; s('id_precio').value = '4800'; document.querySelector('#registro button[type=submit]').click(); })()"); await espera(1800);
r.registro_confirmado = await ev(foco); r.registro_confirmado.contenido = await ev("document.getElementById('registro').innerText.slice(0, 200)");
await ev("document.querySelector('#registro a.btn').click()"); await espera(1500);
r.registrar_otro = await ev(foco);
await ir("/productos/1/");
await ev("document.getElementById('pausar-actualizacion').click()"); await espera(300);
r.pausa_actualizacion = await ev("({ boton: document.getElementById('pausar-actualizacion').textContent, pausada: window.actualizacionPausada === true, avisos: document.getElementById('avisos').textContent })");
await ir("/");
await ev("document.getElementById('pausar-rotacion').click()"); const a = await ev("document.querySelector('.rota').textContent"); await espera(3200);
r.pausa_rotacion = { boton: await ev("document.getElementById('pausar-rotacion').textContent"), palabra_antes: a.trim(), palabra_tras_3_2_s: (await ev("document.querySelector('.rota').textContent")).trim() };
writeFileSync(path.join(SALIDA, "foco-y-anuncios-htmx.json"), JSON.stringify(r, null, 2)); console.log(JSON.stringify(r, null, 1));
ws.close(); chrome.kill(); await espera(500); process.exit(0);
