# ADR-021: Correo transaccional con Brevo (SMTP), outbox y verificación en dos pasos

- **Estado:** Propuesto
- **Fecha:** 2026-11-16
- **Autores:** Equipo; redactado con apoyo de IA
- **Requisitos:** RF-02, RF-03, RF-22, RF-24, RF-25, RF-26, RF-27
- **Atributos de calidad afectados:** seguridad (autenticidad, confidencialidad, responsabilidad),
  fiabilidad (tolerancia a fallos), privacidad (Ley 1581 de 2012)

## Contexto
La plataforma necesita enviar correos reales desde ya, en desarrollo y en producción. Son de dos
clases: de seguridad, que son obligatorios (verificación del correo, recuperación, contraseña
cambiada, ingreso desde un dispositivo nuevo, códigos de dos pasos, cuenta suspendida o suprimida),
e informativos, que se pueden apagar (bienvenida y resultados de moderación). Moderación y
administración pueden cambiar datos que otros ven, así que una contraseña filtrada no debe bastar
para entrar con esos roles. El equipo no tiene dominio propio y el despliegue es un solo proceso
web en un PaaS (ADR-017).

## Alternativas consideradas
| Alternativa | A favor | En contra |
|---|---|---|
| SMTP de Gmail con contraseña de aplicación | Gratis; cuenta ya existente | Límite bajo (~500/día) y frágil; Google puede bloquear el envío automatizado; exige 2FA en la cuenta personal y compartir su contraseña de aplicación |
| API REST de Brevo (HTTP) | Más rica (plantillas remotas, eventos) | Acopla el código a un proveedor; otra dependencia y otro formato. Cambiar de proveedor exigiría reescribir |
| **Relé SMTP de Brevo** + backend SMTP de Django | Estándar: se cambia de proveedor solo con variables de entorno; 300 correos/día gratis; remitente verificable | Límite del plan gratuito; sin eventos de entrega en el código |
| Celery + Redis para enviar en segundo plano | Reintentos y concurrencia robustos | Un *worker* y un *broker* más que operar para un volumen de decenas de correos al día |
| **Outbox en la base de datos** + comando `enviar_correos` | Sin infraestructura nueva; transaccional con los datos; reintentos verificables | Reintentos cada 30 s, no al instante |

## Decisión
- **Proveedor:** relé SMTP de Brevo (`smtp-relay.brevo.com:587` con STARTTLS; 2525 si el 587 está
  bloqueado). La clave **SMTP** (no la de API) y el resto de `EMAIL_*` viven solo en el entorno: el
  `.env` local, que no se versiona, o los secretos del PaaS. Sin `EMAIL_HOST`, el correo se imprime
  en la consola. Las pruebas y el CI usan el backend `locmem` y nunca salen a la red.
- **Remitente:** `AhorraPues <ahorrapuescolombia@gmail.com>`, verificado en Brevo. Las respuestas
  llegan a `EMAIL_REPLY_TO`.
- **Outbox (`CorreoPendiente`):**
  - Cada correo es una fila con una `clave_idempotencia` única: un evento produce un correo.
  - Se encola con `transaction.on_commit`, así un correo sale solo si la transacción se confirmó, y
    se intenta enviar enseguida.
  - Para enviarlo se «reclama» la fila con un `UPDATE` condicional (PENDIENTE → ENVIANDO). Dos
    procesos nunca envían el mismo correo; si el resultado queda incierto, se marca fallido y no se
    reintenta.
  - `manage.py enviar_correos [--continuo]` reintenta hasta 3 veces, esperando 1, 4 y 16 minutos.
- **Secretos fuera de la cola:**
  - Los códigos y los enlaces firmados nunca se guardan; viajan en memoria para el primer intento.
  - En un reintento, los enlaces se regeneran: `cuentas` registra un «regenerador», así
    `notificaciones` no depende de `cuentas`, lo que verifica import-linter.
  - Un código de un solo uso no se reenvía: la persona pide otro.
- **Plantillas:** una por correo, en HTML con tablas y estilos en línea (Gmail, Outlook, Apple Mail)
  y siempre una versión de texto, con los colores de `static/css/app.css`. Llevan cabecera
  `Reply-To`, un `Message-ID` propio y `List-Unsubscribe` con *one-click* (RFC 8058); la baja solo va
  en los informativos.
- **Verificación en dos pasos:**
  - Es opcional para los reportantes y obligatoria para moderadores, administradores, editores de
    catálogo y staff.
  - La sesión **no se abre** hasta superar el segundo paso; un *middleware* cierra cualquier sesión
    que no lo tenga. Así la API (SessionAuthentication) y `/admin/` también lo exigen.
  - **Código por correo:** 6 dígitos, vence en 10 minutos, máximo 5 intentos y luego 15 minutos de
    bloqueo. Solo se guarda su HMAC-SHA256.
  - **App autenticadora (TOTP, RFC 6238)** con **pyotp**: biblioteca pequeña, sin dependencias,
    mantenida y que implementa el estándar que usan Google y Microsoft Authenticator. Escribir TOTP
    a mano arriesgaría errores sutiles de tiempo y truncado. El QR se genera en SVG con **qrcode**,
    sin dependencias gráficas.
  - **Códigos de respaldo:** 10, de un solo uso; solo se guardan sus hashes.
  - **«Confiar en este dispositivo 30 días»:** una cookie firmada que se invalida subiendo
    `version_confianza`, sea al desactivar la 2FA, al usar «no fui yo» o al «olvidar dispositivos».
- **Privacidad:**
  - La huella de dispositivo es un HMAC del navegador y de la IP truncada (/24 o /48), nunca la IP
    completa.
  - Los logs muestran el correo enmascarado y jamás códigos ni claves.
  - Al suprimir una cuenta, el aviso se envía a la dirección anterior y la fila se redacta en cuanto
    termina el envío.

## Consecuencias
- (+) Correos reales desde el primer día, sin infraestructura nueva y con proveedor intercambiable.
- (+) Ningún fallo de SMTP pierde un correo, y un reintento nunca lo duplica.
- (+) Una contraseña filtrada no basta para entrar como moderador o administrador.
- (−) **Límite del plan gratuito de Brevo: 300 correos al día.** Basta para el piloto. Si se
  acerca, los informativos son los primeros en apagarse o resumirse, y el siguiente paso es un plan
  de pago.
- (−) **Riesgo de entrega con un remitente `@gmail.com`:** el correo sale por los servidores de
  Brevo, pero el dominio `gmail.com` publica una política DMARC que esos servidores no cumplen. Gmail,
  Outlook y Yahoo pueden mandarlo a spam o rechazarlo. **Mejora futura:** un dominio propio verificado
  en Brevo con SPF, DKIM y DMARC, por ejemplo `no-responder@ahorrapues.co`, cambiando solo
  `DEFAULT_FROM_EMAIL`.
- (−) El secreto TOTP se guarda en la base de datos, porque sin él no se puede verificar. Quien tenga
  acceso a la base podría generar códigos. **Mitigación futura:** cifrarlo con una clave de entorno.
- (−) Los reintentos necesitan correr `enviar_correos` (cron cada minuto o `--continuo` como proceso
  aparte en el PaaS). Sin eso, solo existe el primer intento.
- (−) Quien debe usar 2FA y no tiene correo ni app la configura al ingresar, justo después de la
  contraseña. Es lo habitual, pero alguien con esa contraseña podría inscribir su propia app. Se
  mitiga pidiendo un correo confirmado a moderadores y administradores.
