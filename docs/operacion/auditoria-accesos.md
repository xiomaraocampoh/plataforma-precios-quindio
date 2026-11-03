# Auditoría de accesos al repositorio

Revisión periódica (por ejemplo, al inicio de cada corte) para confirmar que en el repositorio
privado solo están la propietaria y los colaboradores autorizados, y que no hay bots
(CLAUDE.md §2, regla 6).

**Autorizados:** `xiomaraocampoh` (propietaria) · `LuisaL1` · `ddeelena` (Derlye) ·
Juan Manuel (*pendiente: anotar su usuario de GitHub cuando acepte la invitación*).

Requiere [GitHub CLI](https://cli.github.com) autenticado con la cuenta de la propietaria.

```bash
REPO=xiomaraocampoh/plataforma-precios-quindio

# Colaboradores actuales (login, tipo de cuenta y permiso)
gh api "repos/$REPO/collaborators" --paginate \
  --jq '.[] | [.login, .type, .role_name] | @tsv'

# Invitaciones pendientes
gh api "repos/$REPO/invitations" --jq '.[] | [.id, .invitee.login] | @tsv'
```

Si aparece alguien fuera de la lista o una cuenta de tipo `Bot`, **solo la propietaria** decide
qué hacer:

```bash
gh api -X DELETE "repos/$REPO/collaborators/<login>"    # quitar colaborador
gh api -X DELETE "repos/$REPO/invitations/<id>"         # cancelar invitación
```

Cuando Juan Manuel acepte, actualizar su usuario aquí y en CLAUDE.md §2.
