import http from 'k6/http';
import { check, sleep } from 'k6';

// ====== DATOS DE LA APP (ya configurados) ======
const BASE = 'https://plataforma-precios-quindio.onrender.com';
const PRODUCTOS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11];   // los 11 tienen precios en Armenia
const MUNICIPIO = 'Armenia';
// ===============================================

// Búsquedas que coinciden con productos reales del catálogo
const BUSQUEDAS = ['arroz', 'aceite', 'cafe', 'frijol', 'huevos', 'leche',
                   'lentejas', 'panela', 'papa', 'queso', 'tomate'];

export const options = {
  stages: [
    { duration: '1m', target: 10 },  { duration: '2m', target: 10 },   // escalón 10 usuarios
    { duration: '1m', target: 25 },  { duration: '2m', target: 25 },   // escalón 25 usuarios
    { duration: '1m', target: 50 },  { duration: '2m', target: 50 },   // escalón 50 usuarios
    { duration: '1m', target: 100 }, { duration: '2m', target: 100 },  // escalón 100 usuarios
    { duration: '1m', target: 0 },                                     // bajada
  ],
  thresholds: {
    'http_req_duration{escenario:comparacion}': ['p(95)<2000'], // EC-04: p95 <= 2 s
    'http_req_failed': ['rate<0.01'],                           // EC-04: errores <= 1 %
  },
};

const azar = (lista) => lista[Math.floor(Math.random() * lista.length)];

export default function () {
  const r = Math.random();

  if (r < 0.7) {
    // 70 %: comparar precios de un producto
    const res = http.get(`${BASE}/api/v1/comparacion/${azar(PRODUCTOS)}/?municipio=${MUNICIPIO}`,
      { tags: { escenario: 'comparacion', name: 'comparacion' } });
    check(res, {
      'comparacion 200': (x) => x.status === 200,
      'comparacion trae criterio de orden': (x) => x.status === 200 && x.body.includes('criterio_orden'),
    });

  } else if (r < 0.9) {
    // 20 %: buscar un producto
    const res = http.get(`${BASE}/api/v1/catalogo/productos/?q=${azar(BUSQUEDAS)}`,
      { tags: { escenario: 'busqueda', name: 'busqueda' } });
    check(res, { 'busqueda 200': (x) => x.status === 200 });

  } else {
    // 10 %: ver el directorio de establecimientos
    const res = http.get(`${BASE}/api/v1/establecimientos/?municipio=${MUNICIPIO}`,
      { tags: { escenario: 'directorio', name: 'directorio' } });
    check(res, { 'directorio 200': (x) => x.status === 200 });
  }

  sleep(1 + Math.random() * 2); // el usuario mira la pantalla entre 1 y 3 s
}