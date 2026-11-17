#!/usr/bin/env bash
# Prueba de humo del núcleo contra una URL en ejecución (local, contenedor o despliegue en la nube).
#
#   BASE_URL=http://localhost:8080 CLAVE_MODERADOR='…' ./scripts/prueba_de_humo.sh
#
# Variables (todas opcionales):
#   BASE_URL         URL base. Por defecto http://localhost:8000
#   PRODUCTO_ID      Producto con precios cargados. Por defecto 1
#   CLAVE_MODERADOR  Clave de moderador_demo (DEMO_ADMIN_PASSWORD). Si falta, se omite esa parte
#   HTTPS_SIMULADO   1 = añade «X-Forwarded-Proto: https» (para probar con FORZAR_HTTPS=True)
#
# Requiere los datos de ejemplo (`cargar_demo`). Crea UNA cuenta nueva y registra UN precio.
# Termina con código distinto de cero si alguna comprobación falla.
set -u

BASE="${BASE_URL:-http://localhost:8000}"
PRODUCTO="${PRODUCTO_ID:-1}"
ENCABEZADO=(-H "Referer: $BASE/")
[ "${HTTPS_SIMULADO:-0}" = "1" ] && ENCABEZADO+=(-H "X-Forwarded-Proto: https")

FALLAS=0
JAR_USUARIO=$(mktemp); JAR_MODERADOR=$(mktemp)
trap 'rm -f "$JAR_USUARIO" "$JAR_MODERADOR"' EXIT

# ${ENCABEZADO[@]+…}: en bash 3.2 (macOS) un arreglo vacío con `set -u` es «variable sin definir»
codigo() { curl -s -o /dev/null -w "%{http_code}" ${ENCABEZADO[@]+"${ENCABEZADO[@]}"} "$@"; }
cuerpo() { curl -s ${ENCABEZADO[@]+"${ENCABEZADO[@]}"} "$@"; }
token() { grep -o 'csrfmiddlewaretoken" value="[^"]*' | head -1 | sed 's/.*value="//'; }
opcion() {  # primera opción de un <select name="$2"> dentro del HTML $1
  echo "$1" | awk -v n="name=\"$2\"" '$0 ~ n {f=1} f && /<option value="[0-9]+"/ {match($0,/value="[0-9]+"/); print substr($0,RSTART+7,RLENGTH-8); exit}'
}
chequear() {  # descripción, obtenido, patrón esperado (regex)
  if [[ "$2" =~ $3 ]]; then printf "  ✔ %-64s %s\n" "$1" "$2"
  else printf "  ✘ %-64s %s  (se esperaba /%s/)\n" "$1" "$2" "$3"; FALLAS=$((FALLAS + 1)); fi
}

echo "Prueba de humo contra $BASE"
echo "== Lectura pública =="
chequear "/healthz/ (PostgreSQL y caché)"  "$(cuerpo "$BASE/healthz/")" '"estado": "ok".*"bd": "ok".*"cache": "ok"'
chequear "/ portada"                        "$(codigo "$BASE/")" '^200$'
chequear "/sugerencias/?q=ar (HTMX)"        "$(codigo "$BASE/sugerencias/?q=ar")" '^200$'
chequear "/productos/?q=ARROZ (sin tildes ni mayúsculas)" "$(cuerpo "$BASE/productos/?q=ARROZ" | grep -c Arroz)" '^[1-9]'
chequear "/productos/$PRODUCTO/ (comparación)"           "$(codigo "$BASE/productos/$PRODUCTO/")" '^200$'
chequear "  el criterio de orden está a la vista"        "$(cuerpo "$BASE/productos/$PRODUCTO/" | grep -c 'Menor precio por unidad')" '^[1-9]'
chequear "  filtro por municipio y barrio"               "$(codigo "$BASE/productos/$PRODUCTO/?municipio=Armenia&barrio=Centro")" '^200$'
chequear "/establecimientos/ (directorio con mapa)"      "$(cuerpo "$BASE/establecimientos/" | grep -c openstreetmap)" '^[1-9]'

echo "== API y documentación =="
chequear "/api/docs/ (Swagger)"            "$(codigo "$BASE/api/docs/")" '^200$'
chequear "/api/schema/ (OpenAPI)"          "$(codigo "$BASE/api/schema/")" '^200$'
chequear "/api/v1/comparacion/$PRODUCTO/"  "$(codigo "$BASE/api/v1/comparacion/$PRODUCTO/")" '^200$'
API_COMPARACION=$(cuerpo "$BASE/api/v1/comparacion/$PRODUCTO/")
# «0/N»: ninguna aparición de autor/correo y la respuesta SÍ trae precios (no basta con un cuerpo vacío)
chequear "  la respuesta pública NO expone autor ni correo (M-15)" \
  "$(echo "$API_COMPARACION" | grep -ciE 'autor|usuario|correo|email')/$(echo "$API_COMPARACION" | grep -c '"precio"')" '^0/[1-9]'
chequear "/api/v1/catalogo/productos/?q=arroz" "$(codigo "$BASE/api/v1/catalogo/productos/?q=arroz")" '^200$'

echo "== Escribir exige cuenta (M-13) =="
chequear "POST /api/v1/precios/reportes/ sin sesión" "$(codigo -X POST -H 'Content-Type: application/json' -d '{}' "$BASE/api/v1/precios/reportes/")" '^(401|403)$'
chequear "/precios/registrar/ sin sesión redirige"    "$(codigo "$BASE/precios/registrar/")" '^302$'

echo "== Cuenta nueva, registro de un precio y CSRF =="
USUARIO="humo_$(date +%s)"
T=$(cuerpo -c "$JAR_USUARIO" "$BASE/cuentas/registro/" | token)
chequear "crear cuenta con autorización de datos" \
  "$(codigo -b "$JAR_USUARIO" -c "$JAR_USUARIO" -d "username=$USUARIO&email=&password1=Clave-de-humo-2026&password2=Clave-de-humo-2026&acepto_tratamiento_datos=on&csrfmiddlewaretoken=$T&next=" "$BASE/cuentas/registro/")" '^302$'
PAGINA=$(cuerpo -b "$JAR_USUARIO" -c "$JAR_USUARIO" "$BASE/precios/registrar/")
T=$(echo "$PAGINA" | token)
chequear "formulario de registro con token CSRF" "$([ -n "$T" ] && echo si || echo no)" '^si$'
RESPUESTA=$(cuerpo -b "$JAR_USUARIO" -c "$JAR_USUARIO" -H "HX-Request: true" \
  -d "establecimiento=$(opcion "$PAGINA" establecimiento)&presentacion=$(opcion "$PAGINA" presentacion)&precio=3333&csrfmiddlewaretoken=$T" "$BASE/precios/registrar/")
chequear "registrar un precio muestra la confirmación" "$(echo "$RESPUESTA" | grep -ciE 'ya está publicado|en revisión')" '^[1-9]'
chequear "  aparece en «Mis aportes»" "$(cuerpo -b "$JAR_USUARIO" "$BASE/precios/mis-aportes/" | grep -c 3333)" '^[1-9]'
chequear "POST sin token CSRF es rechazado" "$(codigo -b "$JAR_USUARIO" -d 'precio=3334' "$BASE/precios/registrar/")" '^403$'

echo "== Moderación (solo rol moderador) =="
chequear "/moderacion/ con una cuenta común" "$(codigo -b "$JAR_USUARIO" "$BASE/moderacion/")" '^(302|403)$'
if [ -n "${CLAVE_MODERADOR:-}" ]; then
  T=$(cuerpo -c "$JAR_MODERADOR" "$BASE/cuentas/ingresar/" | token)
  chequear "ingresar como moderador_demo" "$(codigo -b "$JAR_MODERADOR" -c "$JAR_MODERADOR" -d "username=moderador_demo&password=$CLAVE_MODERADOR&csrfmiddlewaretoken=$T&next=" "$BASE/cuentas/ingresar/")" '^302$'
  chequear "/moderacion/ como moderador" "$(codigo -b "$JAR_MODERADOR" "$BASE/moderacion/")" '^200$'
else
  echo "  – (se omite: defina CLAVE_MODERADOR para probar el ingreso de moderación)"
fi

echo
if [ "$FALLAS" -eq 0 ]; then echo "RESULTADO: todas las comprobaciones pasaron."; else echo "RESULTADO: $FALLAS comprobación(es) fallaron."; fi
exit "$FALLAS"
