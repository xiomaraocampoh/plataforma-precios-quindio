// Diagnóstico corto: cuenta los códigos HTTP que devuelve la app bajo carga.
import http from 'k6/http';
import { sleep } from 'k6';
import { Counter } from 'k6/metrics';

const BASE = 'https://plataforma-precios-quindio.onrender.com';
const codigos = new Counter('codigos_http');

export const options = {
  stages: [
    { duration: '30s', target: 10 },
    { duration: '1m', target: 25 },
    { duration: '30s', target: 0 },
  ],
  summaryTrendStats: ['avg', 'p(95)'],
  // Umbrales triviales solo para que k6 reporte cada código por separado
  thresholds: Object.fromEntries(['0', '200', '403', '429', '500', '502', '503', '504']
    .map((c) => [`codigos_http{codigo:${c}}`, ['count>=0']])),
};

export default function () {
  const id = Math.floor(Math.random() * 11) + 1;
  const res = http.get(`${BASE}/api/v1/comparacion/${id}/?municipio=Armenia`, { tags: { name: 'comparacion' } });
  codigos.add(1, { codigo: String(res.status) });
  if (res.status !== 200 && __ITER % 20 === 0) {
    console.log(`t=${new Date().toISOString()} codigo=${res.status} retry-after=${res.headers['Retry-After']} cuerpo=${String(res.body).slice(0, 150)}`);
  }
  sleep(1 + Math.random() * 2);
}

export function handleSummary(data) {
  const filas = Object.keys(data.metrics)
    .filter((k) => k.startsWith('codigos_http{'))
    .map((k) => `${k}: ${data.metrics[k].values.count}`);
  return { stdout: '\nCODIGOS HTTP\n' + filas.join('\n') + `\nTotal: ${data.metrics.codigos_http.values.count}\n` };
}
