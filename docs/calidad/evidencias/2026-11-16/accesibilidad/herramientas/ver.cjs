const path = require("path"); const d = path.resolve(process.argv[2]);
const t = require(path.join(d, "teclado.json")); console.log("error:", t.error || "ninguno");
const a = require(path.join(d, "axe/resumen.json"));
for (const [k, v] of Object.entries(a)) console.log(k.padEnd(36), (v.url || "").padEnd(20), String(v.violaciones).padStart(2), v.reglas.join(" "), "| revisar:", v.revisar.join(","));
const l = require(path.join(d, "lighthouse/resumen.json"));
for (const [k, v] of Object.entries(l)) console.log("LH", k.padEnd(16), v.puntaje ?? v.error, (v.fallos || []).map((f) => f.id + "(" + f.elementos + ")").join(" "));
if (process.argv[3]) console.log(JSON.stringify({ saltar: t.saltar_contenido, buscador: t.buscador, rotacion: t.rotacion, recarga: t.recarga_automatica, espaciado: t.espaciado_texto, reflujo: t.reflujo_320,
  sin_foco_visible: Object.fromEntries(Object.entries(t).filter(([, v]) => v && v.sin_foco_visible).map(([k, v]) => [k, v.sin_foco_visible])),
  pequenos: Object.fromEntries(Object.entries(t).filter(([, v]) => v && v.pequenos).map(([k, v]) => [k, v.pequenos])) }, null, 1));
