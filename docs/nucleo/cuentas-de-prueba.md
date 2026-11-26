# Cuentas de prueba

Una cuenta por rol, para probar la aplicación **en local**. Desde el ADR-0023 las crea `migrate`,
junto con los datos de `data/demo/`.

## Primera vez

1. `git pull`
2. `pip install -r requirements/dev.txt`
3. `docker compose up -d db redis`
4. En tu `.env`, define `CUENTAS_PRUEBA_PASSWORD` con la contraseña que el equipo comparte **por
   privado**. Nunca va en el código, en `.env.example`, en un commit ni en un mensaje público.
5. `python manage.py migrate`
6. `python manage.py runserver` e ingresa con cualquier usuario de la tabla de abajo.

Si migraste **sin** la variable, las cuentas se crean igual, pero con una contraseña inutilizable.
`migrate` lo avisa: *«Define CUENTAS_PRUEBA_PASSWORD y corre python manage.py crear_cuentas_prueba
para activarlas»*. Haz justo eso:

```bash
python manage.py crear_cuentas_prueba   # lee CUENTAS_PRUEBA_PASSWORD del .env
```

### Si los precios ya no aparecen

Los precios de prueba se fechan «hace N días» desde el momento en que migraste, así que envejecen.
Pasada una semana casi todos quedan vencidos y la comparación sale vacía. Para renovarlos:

```bash
python manage.py refrescar_precios_prueba
```

El comando vuelve a poner cada precio a la misma distancia de hoy. Los escenarios vencidos (8, 4 y
31 días) siguen vencidos, y los «Sigue igual» de prueba pasan a hoy. Solo toca los precios con
`es_demo=True`, nunca los reales. En un despliegue de demostración, `scripts/start.sh` lo corre al
iniciar.

### Cuándo siembra `migrate`

| Situación | Datos de `data/demo/` | Cuentas de prueba |
|---|---|---|
| `DEBUG=True` (local) | Sí | Sí |
| `DEBUG=False` (producción), por defecto | No | **No** |
| `DEBUG=False` y `SEMBRAR_DATOS_PRUEBA=True` | Sí; los precios, solo si existen las cuentas (son sus autores) | No |
| `DEBUG=False` y `SEMBRAR_CUENTAS_PRUEBA=True` | — | Sí |

- Una migración corre una sola vez. Si después cambian los CSV o activas una variable, usa
  `python manage.py cargar_datos_prueba`, que usa la misma lógica.
- Las cuentas que ya tenían contraseña la conservan: `migrate` no la cambia. Para cambiarla, usa
  `crear_cuentas_prueba`.

## El comando `crear_cuentas_prueba`

Crea o actualiza las cuentas y les fija la contraseña:

```bash
python manage.py crear_cuentas_prueba
```

- Todas las cuentas usan la contraseña de `CUENTAS_PRUEBA_PASSWORD`. Si la variable no existe, el
  comando se detiene. **No genera ni imprime contraseñas.**
- La contraseña debe cumplir los validadores de Django: longitud mínima, que no sea común y que
  no sea solo numérica.
- Por defecto los correos usan `example.com` (RFC 2606), así que nunca llegan a una persona real.
  Con `CUENTAS_PRUEBA_CORREO_BASE` usan un buzón del equipo (ver abajo). Quedan ya verificados y
  con el consentimiento de datos (Ley 1581) aceptado.
- El grupo y los permisos salen del rol (`apps/cuentas/domain/roles.py`).
- Correr el comando otra vez actualiza las cuentas: rol, estado, grupo y contraseña. No las duplica.

| Usuario | Rol | Qué puede probar |
|---|---|---|
| `admin_prueba` | administrador (staff y superusuario) | Todo: `/panel/` (catálogo, directorio, roles, auditoría), `/admin/` y moderación |
| `moderador_prueba` | moderador (staff) | Cola de moderación: reportes en revisión, denuncias, solicitudes y sugerencias |
| `editor_prueba` | editor de catálogo | Panel de catálogo: marcas, categorías, productos y presentaciones |
| `reportante_prueba` | reportante | Registrar precios, «Sigue igual», denunciar, pedir productos y sugerir tiendas |
| `reportante_ana` | reportante | Segunda persona: confirmar con «Sigue igual» precios de otra cuenta |
| `reportante_luis` | reportante | Tercera persona: confianza alta (varios reportes iguales) y denuncias |
| `comercio_prueba` | comercio | El rol existe, pero el portal es del Corte III: ve lo mismo que un consumidor con cuenta |
| `suspendido_prueba` | reportante (inactiva) | El ingreso se rechaza: bloqueo de una cuenta suspendida (RF-22) |

Los datos de prueba (ver `data/demo/README.md`) usan estas mismas cuentas como autores. Por eso, al
ingresar, cada reportante ya tiene aportes.

## Correos de las cuentas: `CUENTAS_PRUEBA_CORREO_BASE`

En producción (`DEBUG=False`) el 2FA no se puede omitir: el administrador, el moderador y el staff
reciben el código por correo. Con los correos `@example.com` ese código no le llega a nadie y no
se puede ingresar. Para eso, define en el entorno un buzón real del equipo:

```
CUENTAS_PRUEBA_CORREO_BASE=equipo@gmail.com
```

Cada cuenta usa `parte_local+sufijo@dominio`. Gmail y la mayoría de proveedores entregan
`equipo+admin@gmail.com` en el buzón `equipo@gmail.com`, así que un solo buzón recibe los códigos
de todas las cuentas.

| Usuario | Sufijo | Correo con `equipo@gmail.com` |
|---|---|---|
| `admin_prueba` | `admin` | `equipo+admin@gmail.com` |
| `moderador_prueba` | `moderador` | `equipo+moderador@gmail.com` |
| `editor_prueba` | `editor` | `equipo+editor@gmail.com` |
| `reportante_prueba` | `reportante` | `equipo+reportante@gmail.com` |
| `reportante_ana` | `ana` | `equipo+ana@gmail.com` |
| `reportante_luis` | `luis` | `equipo+luis@gmail.com` |
| `comercio_prueba` | `comercio` | `equipo+comercio@gmail.com` |
| `suspendido_prueba` | `suspendido` | `equipo+suspendido@gmail.com` |

- Vacía (el valor por defecto): se conservan los `@example.com`. Las pruebas y el CI siempre la
  usan vacía (`config/settings/test.py`).
- La base debe tener la forma `parte_local@dominio`, sin espacios ni `+`. Si no la tiene, el
  comando y la siembra se detienen con un error que nombra la variable, sin escribir nada.
- La regla vive en `apps/cuentas/domain/cuentas_prueba.py::correo_de_prueba`. La usan
  `crear_cuentas_prueba` y la siembra de `migrate` (`apps/cuentas/semilla.py`, ADR-0023).
- La migración ya aplicada no vuelve a correr. En una base que ya tiene las cuentas, actualiza
  solo el correo, sin tocar contraseñas, roles ni grupos y sin pedir `CUENTAS_PRUEBA_PASSWORD`:

```bash
python manage.py crear_cuentas_prueba --solo-correos
```

  Solo cambia las cuentas marcadas `es_cuenta_prueba=True`; no crea las que faltan.

## Verificación en dos pasos en local: `PERMITIR_PRUEBA_SIN_2FA`

El administrador, el moderador y el editor tienen el 2FA obligatorio (RF-27). Para probarlos en
local sin configurar una app autenticadora, se puede activar en el `.env`:

```
PERMITIR_PRUEBA_SIN_2FA=True
```

Una cuenta se salta el segundo paso **solo si se cumplen las tres condiciones**
(`apps/cuentas/domain/segundo_factor.py::omitir_segundo_factor_de_prueba`):

1. `PERMITIR_PRUEBA_SIN_2FA=True`;
2. `DEBUG=True`;
3. la cuenta tiene `es_cuenta_prueba=True`. Solo `migrate` (`cuentas.0006`) y
   `crear_cuentas_prueba` marcan cuentas así.

Ninguna otra cuenta se salta el 2FA. Las condiciones se revisan en cada petición: si se apaga
`DEBUG`, la sesión de prueba se cierra.

- `config/settings/prod.py` fija `PERMITIR_PRUEBA_SIN_2FA = False` pase lo que pase en el entorno.
  Lo comprueba `tests/unit/test_settings_produccion.py`.
- Con el ajuste activo, `runserver` muestra al arrancar el aviso `cuentas.W001`. Si además
  `DEBUG=False`, muestra `cuentas.W002`: el ajuste se ignora.

Pruebas: `tests/unit/cuentas/test_cuentas_prueba.py`,
`tests/integration/cuentas/test_cuentas_prueba.py` y
`tests/integration/test_semilla_migraciones.py` (siembra en `migrate`).
