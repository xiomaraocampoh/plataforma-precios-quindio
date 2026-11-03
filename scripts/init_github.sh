#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Inicializa el repositorio PRIVADO en GitHub e invita ÚNICAMENTE a LuisaL1.
# Ejecutar desde la raíz del proyecto, autenticada con TU cuenta de GitHub:
#     bash scripts/init_github.sh
# Variables opcionales: REPO_NAME, SKIP_SETUP=1 (no crear venv ni migraciones)
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

REPO_NAME="${REPO_NAME:-plataforma-precios-quindio}"
COLABORADORA="LuisaL1"
DESCRIPCION="Plataforma colaborativa de comparación de precios (Armenia/Quindío) - Proyecto Nuclear 6.º semestre (II-2026)"

# Regla inviolable: lista blanca de colaboradores. Nada de bots ni identidades de IA.
# Añadir aquí el usuario de GitHub de Juan Manuel cuando acepte la invitación por correo.
ALLOWLIST=("$COLABORADORA" "ddeelena")

err() { echo "ERROR: $*" >&2; exit 1; }
info() { echo "▶ $*"; }

# ── 0. Prerrequisitos ────────────────────────────────────────────────────────
command -v git >/dev/null || err "Instala git."
command -v gh  >/dev/null || err "Instala GitHub CLI: https://cli.github.com"
[ -f manage.py ] || err "Ejecuta el script desde la raíz del proyecto (donde está manage.py)."
git config user.name  >/dev/null || err "Configura: git config --global user.name \"Tu Nombre\""
git config user.email >/dev/null || err "Configura: git config --global user.email \"tu@correo\""

if ! gh auth status >/dev/null 2>&1; then
  info "Iniciando sesión en GitHub CLI (cuenta humana propietaria)…"
  gh auth login --hostname github.com --git-protocol https --web
fi
OWNER="$(gh api user --jq .login)"
info "Propietaria del repositorio: $OWNER"

# ── 1. Migraciones iniciales y pruebas (para que el CI pase desde el primer push) ─
if [ "${SKIP_SETUP:-0}" != "1" ]; then
  PY="$(command -v python3 || command -v python)"
  [ -d .venv ] || "$PY" -m venv .venv
  if [ -f .venv/Scripts/python.exe ]; then VPY=.venv/Scripts/python.exe; else VPY=.venv/bin/python; fi
  "$VPY" -m pip install -q -r requirements/dev.txt
  info "Generando migraciones iniciales…"
  DJANGO_SETTINGS_MODULE=config.settings.test "$VPY" manage.py makemigrations \
    cuentas catalogo establecimientos precios moderacion
  info "Aplicando formato PEP 8 (ruff)…"
  "$VPY" -m ruff format . >/dev/null
  "$VPY" -m ruff check . --fix || echo "  ⚠ Ruff reporta hallazgos; corrígelos en el primer PR."
  info "Ejecutando pruebas…"
  "$VPY" -m pytest -q || echo "  ⚠ Hay pruebas fallando; revisa antes de abrir el primer PR."
fi

# ── 2. Repositorio git local + commit inicial ───────────────────────────────
[ -d .git ] || git init -b main
git add -A
if git diff --cached --quiet; then
  info "No hay cambios nuevos para commitear."
else
  git commit -m "chore: estructura inicial del proyecto

- Monolito modular multicapa Django 5.2 + DRF + HTMX + PostgreSQL
- Apps: cuentas, catalogo, establecimientos, precios, comparacion, moderacion, integraciones
- Reglas de dominio con TDD (normalización, vigencia, confianza, orden neutral)
- CI (ruff + pytest + cobertura), ADR 0001-0003, CLAUDE.md"
fi

# ── 3. Crear el repositorio PRIVADO y subir ─────────────────────────────────
if gh repo view "$OWNER/$REPO_NAME" >/dev/null 2>&1; then
  info "El repositorio ya existe; no se recrea."
  git remote get-url origin >/dev/null 2>&1 || \
    git remote add origin "https://github.com/$OWNER/$REPO_NAME.git"
  git push -u origin main
else
  gh repo create "$OWNER/$REPO_NAME" --private --description "$DESCRIPCION" \
    --source=. --remote=origin --push
fi

# ── 4. Verificar visibilidad privada ────────────────────────────────────────
VIS="$(gh repo view "$OWNER/$REPO_NAME" --json visibility --jq .visibility)"
if [ "$VIS" != "PRIVATE" ]; then
  info "Visibilidad $VIS detectada; cambiando a privado…"
  gh repo edit "$OWNER/$REPO_NAME" --visibility private --accept-visibility-change-consequences
fi
gh repo edit "$OWNER/$REPO_NAME" --enable-wiki=false --delete-branch-on-merge >/dev/null

# ── 5. Rama develop ─────────────────────────────────────────────────────────
if ! git ls-remote --exit-code --heads origin develop >/dev/null 2>&1; then
  git branch develop 2>/dev/null || true
  git push -u origin develop
fi

# ── 6. Invitar a la colaboradora con permiso de escritura (push) ────────────
info "Invitando a $COLABORADORA con permiso de escritura…"
gh api --method PUT "repos/$OWNER/$REPO_NAME/collaborators/$COLABORADORA" \
  -f permission=push >/dev/null

# ── 7. Auditoría de acceso: solo propietaria + lista blanca, sin bots ───────
info "Auditando colaboradores e invitaciones…"
permitido() {
  local login="$1"
  [ "$login" = "$OWNER" ] && return 0
  for ok in "${ALLOWLIST[@]}"; do [ "$login" = "$ok" ] && return 0; done
  return 1
}
INTRUSOS=0
while IFS=$'\t' read -r login tipo; do
  [ -z "$login" ] && continue
  if ! permitido "$login" || [ "$tipo" = "Bot" ]; then
    echo "  ⚠ Colaborador NO permitido: $login ($tipo)"
    echo "    Quitar con: gh api -X DELETE repos/$OWNER/$REPO_NAME/collaborators/$login"
    INTRUSOS=1
  fi
done < <(gh api "repos/$OWNER/$REPO_NAME/collaborators" --paginate --jq '.[] | [.login, .type] | @tsv')

while IFS=$'\t' read -r id login; do
  [ -z "$login" ] && continue
  if ! permitido "$login"; then
    echo "  ⚠ Invitación NO permitida: $login"
    echo "    Cancelar con: gh api -X DELETE repos/$OWNER/$REPO_NAME/invitations/$id"
    INTRUSOS=1
  fi
done < <(gh api "repos/$OWNER/$REPO_NAME/invitations" --jq '.[] | [.id, .invitee.login] | @tsv')

[ "$INTRUSOS" -eq 0 ] || err "Hay accesos fuera de la lista blanca. Revísalos arriba."

# ── 8. (Opcional) Proteger main: requiere GitHub Pro/Education en repos privados ─
gh api --method PUT "repos/$OWNER/$REPO_NAME/branches/main/protection" --input - >/dev/null 2>&1 <<'JSON' \
  && info "Rama main protegida (PR + 1 revisión + CI)." \
  || echo "  ℹ No se pudo proteger main (en repos privados requiere GitHub Pro; gratis con GitHub Education)."
{
  "required_status_checks": { "strict": true, "contexts": ["calidad"] },
  "enforce_admins": false,
  "required_pull_request_reviews": { "required_approving_review_count": 1 },
  "restrictions": null
}
JSON

echo
info "Listo: https://github.com/$OWNER/$REPO_NAME (privado)"
info "$COLABORADORA debe aceptar la invitación en https://github.com/$OWNER/$REPO_NAME/invitations"
