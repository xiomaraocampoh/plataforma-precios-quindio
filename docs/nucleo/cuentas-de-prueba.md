# Cuentas de prueba

Una cuenta por rol, para probar la aplicación **en local**. Las crea o actualiza este comando:

```bash
# La contraseña la elige cada quien y vive solo en su .env (nunca en el código ni en git)
CUENTAS_PRUEBA_PASSWORD=...  python manage.py crear_cuentas_prueba
```

- Todas las cuentas usan la contraseña de `CUENTAS_PRUEBA_PASSWORD`. Si la variable no existe, el
  comando se detiene. **No genera ni imprime contraseñas.**
- La contraseña debe cumplir los validadores de Django: longitud mínima, que no sea común y que
  no sea solo numérica.
- Los correos usan `example.com` (RFC 2606), así que nunca llegan a una persona real. Quedan ya
  verificados y con el consentimiento de datos (Ley 1581) aceptado.
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

Los datos de `python manage.py cargar_datos_prueba` (ver `data/demo/README.md`) usan estas mismas
cuentas como autores. Por eso, al ingresar, cada reportante ya tiene aportes.

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
3. la cuenta tiene `es_cuenta_prueba=True`. Solo `crear_cuentas_prueba` marca cuentas así.

Ninguna otra cuenta se salta el 2FA. Las condiciones se revisan en cada petición: si se apaga
`DEBUG`, la sesión de prueba se cierra.

- `config/settings/prod.py` fija `PERMITIR_PRUEBA_SIN_2FA = False` pase lo que pase en el entorno.
  Lo comprueba `tests/unit/test_settings_produccion.py`.
- Con el ajuste activo, `runserver` muestra al arrancar el aviso `cuentas.W001`. Si además
  `DEBUG=False`, muestra `cuentas.W002`: el ajuste se ignora.

Pruebas: `tests/unit/cuentas/test_cuentas_prueba.py` y
`tests/integration/cuentas/test_cuentas_prueba.py`.
