# Correr el proyecto en tu equipo (con datos y cuentas de prueba)

Guía para el equipo. Está pensada para Windows con PowerShell; al final hay notas para macOS y Linux.

## Antes de empezar: los datos NO están en una base compartida

Cada persona tiene **su propia base de datos**: un PostgreSQL que corre en Docker dentro de su
equipo (`DATABASE_URL` apunta a `localhost`). Lo que hace una persona (precios, cuentas,
denuncias) **no le aparece a las demás**.

Lo que sí se comparte por git es lo necesario para que todas tengan **los mismos datos de prueba**:

| Qué | Dónde | Cómo llega a tu base |
|---|---|---|
| Catálogo, tiendas y precios de prueba | `data/demo/*.csv` | `python manage.py migrate` (ADR-0023) |
| Cuentas de prueba por rol | `apps/cuentas/domain/cuentas_prueba.py` | `python manage.py migrate`, con `CUENTAS_PRUEBA_PASSWORD` en el `.env` |

Con `migrate`, cada persona obtiene en pocos segundos los mismos 70 productos, 13 locales,
438 precios y 8 cuentas. Las contraseñas no se comparten: **cada persona elige la suya** en su
terminal.

## Requisitos (una sola vez)

- Git, **Python 3.12** y **Docker Desktop** (abierto antes de empezar).
- Acceso al repositorio privado `xiomaraocampoh/plataforma-precios-quindio`.

## Paso a paso

### 1. Bajar el código al día

Si es la primera vez:

```powershell
git clone https://github.com/xiomaraocampoh/plataforma-precios-quindio.git
cd plataforma-precios-quindio
```

Si ya lo tenías:

```powershell
git switch main
git pull --ff-only
```

Si `git pull` se queja de cambios locales, guárdalos primero con `git stash push -u -m "respaldo"`.

### 2. Entorno de Python y dependencias

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements/dev.txt
```

Vuelve a correr `pip install -r requirements/dev.txt` cada vez que bajes cambios: hace poco se
añadieron `anthropic`, `pyotp` y `qrcode`. Si PowerShell no deja activar el entorno, ejecuta una
vez `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

### 3. Archivo `.env` (solo en tu equipo, nunca se sube)

```powershell
Copy-Item .env.example .env
```

Abre `.env` y revisa estas líneas:

| Variable | Valor para trabajar en local |
|---|---|
| `DEBUG` | `True` |
| `DATABASE_URL` | déjala como viene (`postgres://precios:precios@localhost:5432/precios`) |
| `PERMITIR_PRUEBA_SIN_2FA` | `True`: las cuentas de prueba entran sin el segundo paso. Solo funciona con `DEBUG=True` |
| `EMAIL_HOST` | **déjala vacía** (`EMAIL_HOST=`) si no tienes clave de Brevo: los correos se imprimen en la consola de `runserver`. Si dejas el valor de ejemplo, los envíos fallan |
| `CUENTAS_PRUEBA_PASSWORD` | puedes dejarla vacía aquí y definirla en la terminal (paso 6) |

Comprueba que el `.env` no esté en git con `git ls-files .env`: no debe mostrar nada. **Nunca pegues
el contenido del `.env` en el chat del grupo ni en un PR.**

### 4. Base de datos, caché, datos y cuentas de prueba

Antes de migrar, pon en tu `.env` la contraseña de las cuentas de prueba que el equipo comparte
por privado: `CUENTAS_PRUEBA_PASSWORD=...` (nunca en el código ni en git).

```powershell
docker compose up -d db redis
python manage.py migrate
```

Con `DEBUG=True`, `migrate` siembra los datos de `data/demo/` y las cuentas de prueba (ADR-0023).
Si migraste sin la variable, las cuentas quedan con contraseña inutilizable: defínela y corre
`python manage.py crear_cuentas_prueba`.

### 5. Recargar o renovar los datos de prueba (opcional)

```powershell
python manage.py refrescar_precios_prueba      # renueva las fechas si los precios vencieron
python manage.py cargar_datos_prueba --limpiar # borra los de prueba y los vuelve a cargar
```

- `cargar_datos_prueba` imprime un resumen: marcas, productos, presentaciones, establecimientos, precios, «Sigue
  igual», denuncias, solicitudes y sugeridos.
- `--limpiar` borra solo los datos de prueba y los vuelve a cargar; lo que hayas creado a mano se
  conserva.
- Es idempotente: si lo corres dos veces, no duplica nada.
- Los precios se guardan como «hace N días» desde el momento de la carga. Si pasa una semana y
  la comparación se ve vacía, corre `refrescar_precios_prueba`.
- Qué escenarios trae y de dónde salen los precios: [data/demo/README.md](../../data/demo/README.md).
  Son **datos de prueba**: pueden no coincidir con los precios actuales.

### 6. Cambiar o activar la contraseña de las cuentas de prueba (opcional)

`migrate` ya creó las cuentas. Para fijarles otra contraseña (al menos 8 caracteres, que no sea
común ni solo números), defínela en el `.env` o en la terminal, nunca en el código:

```powershell
$env:CUENTAS_PRUEBA_PASSWORD = "escribe-aqui-tu-contraseña"
python manage.py crear_cuentas_prueba
```

El comando imprime la tabla de cuentas, sin la contraseña:

| Usuario | Rol | Para probar |
|---|---|---|
| `admin_prueba` | administrador | `/panel/`, `/admin/` y moderación |
| `moderador_prueba` | moderador | Cola de moderación: reportes en revisión, denuncias, solicitudes |
| `editor_prueba` | editor de catálogo | Panel de catálogo |
| `reportante_prueba`, `reportante_ana`, `reportante_luis` | reportante | Registrar, «Sigue igual», denunciar |
| `comercio_prueba` | comercio | Portal `/comercios/`: «Tienda Doña Gloria» verificada, con precios oficiales y promociones (semilla `comercios.0002`) |
| `suspendido_prueba` | suspendida | Debe rechazar el ingreso |

Si cierras la terminal, la variable se pierde; solo hace falta definirla otra vez para volver a
correr `crear_cuentas_prueba`. Más detalle: [docs/nucleo/cuentas-de-prueba.md](../nucleo/cuentas-de-prueba.md).

### 7. Probar y abrir la app

```powershell
pytest -q                       # todo en verde (unas 770 pruebas, ~1,5 min)
python manage.py runserver
```

Abre http://localhost:8000 e **ingresa con Ctrl+F5** la primera vez para que el navegador tome el
CSS nuevo.

- Al arrancar verás el aviso `cuentas.W001`: es esperado mientras `PERMITIR_PRUEBA_SIN_2FA=True`.
- Algunas pruebas usan Chromium. Si fallan por falta del navegador, instálalo una vez con
  `python -m playwright install chromium`.

### Qué mirar para comprobar que todo quedó bien

1. Busca **«Arroz Roa»**: hay tarjetas de 500 g y 1 kg ordenadas por precio por kg, con dirección,
   «Ver en el mapa» y la confianza escrita.
2. Ingresa como `reportante_ana`, ve a **Registrar precio**, elige una presentación y escribe un
   precio: debajo aparece «Equivale a $X por kg».
3. Ingresa como `moderador_prueba`: en la cola hay un precio **en revisión** (Café Sello Rojo en
   D1 Granada) y **2 denuncias abiertas**.
4. Intenta ingresar como `suspendido_prueba`: debe rechazarlo.

## Problemas frecuentes

| Síntoma | Solución |
|---|---|
| La página se ve vieja: dice «góndola» o falta el menú nuevo | Hay otro `runserver` viejo en el puerto 8000. Ciérralo o usa `python manage.py runserver 8001`, y recarga con Ctrl+F5 |
| `ModuleNotFoundError: anthropic` (o `pyotp`, `qrcode`) | `pip install -r requirements/dev.txt` |
| `connection refused` en el puerto 5432 | Abre Docker Desktop y corre `docker compose up -d db redis` |
| `crear_cuentas_prueba` dice que falta `CUENTAS_PRUEBA_PASSWORD` | Defínela en la terminal (paso 6) |
| `crear_cuentas_prueba` rechaza la contraseña | Usa una más larga, que no sea común ni solo números |
| Te pide el código de verificación en dos pasos | Revisa `DEBUG=True` y `PERMITIR_PRUEBA_SIN_2FA=True` en el `.env` y reinicia `runserver`. Solo funciona con las cuentas `*_prueba` |
| La comparación aparece vacía | Los precios vencieron; corre `refrescar_precios_prueba` |

## macOS y Linux

Cambian tres comandos: `source .venv/bin/activate` para activar el entorno, `cp .env.example .env`
para copiar el archivo y `export CUENTAS_PRUEBA_PASSWORD="..."` para la contraseña.

## Qué falta por organizar en el equipo

| Pendiente | Quién decide |
|---|---|
| Juan Manuel debe aceptar la invitación al repositorio, y su usuario de GitHub se anota en `CLAUDE.md` (regla 6) | Juan Manuel y Xiomara |
| Borrar o conservar las ramas ya fusionadas en `main`: hoy no queda ninguna rama remota sin fusionar ni ningún PR abierto | Xiomara |
| Revisión manual de accesibilidad con axe o Lighthouse y un lector de pantalla, antes del cierre del corte (M-03). Las pruebas automáticas cubren contraste, tamaño de objetivos y ARIA, pero no la reemplazan | Equipo |
| Verificar las direcciones de las sedes de cadena marcadas «aproximado» en `data/demo/establecimientos.csv`; solo 2 tienen fuente documental | Quien conozca Armenia y el Quindío |
| **Corte III:** módulo `apps/comercios` (perfil, precio oficial y promociones). No se adelanta antes, para no invalidar la medición de EC-05 | Equipo, al iniciar el corte |
| Si el equipo quiere **datos compartidos** entre todas (una sola base en línea), hay que acordar un servidor desplegado ([despliegue.md](despliegue.md)). Hoy no existe; cada persona trabaja con su base local | Equipo |
