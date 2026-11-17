#!/bin/sh
# Arranque del contenedor (PaaS). `migrate` ya siembra los datos y las cuentas de prueba cuando
# corresponde (ADR-0023: DEBUG, SEMBRAR_DATOS_PRUEBA, SEMBRAR_CUENTAS_PRUEBA); aquí no se carga
# nada aparte para no duplicar.
set -e
python manage.py migrate --noinput

activo() {
  case "$1" in [Tt]rue|TRUE|1|[Yy]es|[Ss]i|on) return 0 ;; *) return 1 ;; esac
}

# En una demostración los precios de prueba se fechan al migrar y envejecen: se renuevan al iniciar
if activo "${DEBUG:-}" || activo "${SEMBRAR_DATOS_PRUEBA:-}"; then
  python manage.py refrescar_precios_prueba
fi

exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers ${WEB_CONCURRENCY:-1} --access-logfile -
