// EC-04 / M-08, M-09: 500 usuarios concurrentes consultando comparaciones (pico de quincena).
// Uso: k6 run -e BASE_URL=https://staging.example -e PRODUCTOS=1,2,3 loadtests/k6/comparacion.js
import http from "k6/http";
import { check, sleep } from "k6";

const BASE = __ENV.BASE_URL || "http://localhost:8000";
const PRODUCTOS = (__ENV.PRODUCTOS || "1").split(",");

export const options = {
  stages: [
    { duration: "1m", target: 100 },
    { duration: "2m", target: 500 },
    { duration: "5m", target: 500 },
    { duration: "1m", target: 0 },
  ],
  thresholds: {
    http_req_duration: ["p(95)<2000"], // mínimo aceptable (objetivo 1500)
    http_req_failed: ["rate<0.01"],    // M-09 mínimo 1 % (objetivo 0,5 %)
  },
};

export default function () {
  const id = PRODUCTOS[Math.floor(Math.random() * PRODUCTOS.length)];
  const r = http.get(`${BASE}/api/v1/comparacion/${id}/`);
  check(r, { "200": (res) => res.status === 200 });
  sleep(Math.random() * 3 + 1);
}
