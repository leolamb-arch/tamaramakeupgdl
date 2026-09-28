> Actualización del panel (28/09/2026): consulta [la guía del panel de referencia](docs/PANEL_REFERENCIA.md). El nuevo administrador guarda directamente y sustituye el flujo de borrador/publicación descrito en apartados históricos de esta guía.

# Tamara Aldrete · sitio y administración local

Aplicación Flask con SQLite, página pública y editor privado. La reestructuración conserva los textos, colores, fotografías, fuentes y datos existentes. No hay cobros, agenda real ni envío automático de mensajes: el formulario prepara un resumen local.

## Requisitos

- Windows con PowerShell y Python 3.12 o superior. La verificación de esta entrega usa Python 3.12.
- Un navegador actualizado con módulos JavaScript (Edge, Chrome o Firefox).
- Internet solo para instalar dependencias por primera vez.
- Node.js solo si quieres ejecutar las pruebas de navegador; no es necesario para usar el sitio.

## Ejecutar en la carpeta habitual

Abre PowerShell y ejecuta:

```powershell
Set-Location -LiteralPath 'C:\Users\sirle\OneDrive\Desktop\TAMARA WEBSITE\tamara-local\TamaraMakeUpGDL\tamara-admin'
./start-local.ps1
```

Abre `http://127.0.0.1:8765/`. Para administrar, abre `http://127.0.0.1:8765/admin`. Si ya existe un usuario, conserva su acceso habitual. Para detener este servidor, pulsa Ctrl+C en esa terminal.

También puedes abrir `abrir-tamara.vbs`: verifica que el servidor responda y abre `/login`. No abras los HTML con doble clic ni uses Live Server o `python -m http.server`: no implementan la API y pueden exponer archivos privados.

Tras actualizar el código, reinicia el servidor y recarga con Ctrl+F5. Cerrar el navegador no detiene un servidor iniciado de forma oculta. Si lo abriste con el acceso directo y necesitas detenerlo, identifica la instancia de `python.exe` de Tamara en el Administrador de tareas; no cierres otros procesos Python.

## Instalación manual desde cero

Desde la carpeta del proyecto:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
$env:APP_SECRET = & .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
$env:APP_ORIGIN = 'http://127.0.0.1:8765'
.\.venv\Scripts\python.exe manage.py create-admin
.\.venv\Scripts\python.exe manage.py serve
```

Ejecuta `create-admin` solamente cuando no exista un administrador. La contraseña se solicita sin mostrarla; debe tener de 14 a 1024 caracteres y coincidir con la confirmación. No hay contraseña predeterminada ni registro público. La clave temporal anterior dura esa terminal; usa el script habitual para mantener una clave estable protegida con DPAPI.

Si `py -3.12` no existe, instala Python 3.12 o usa una versión compatible con `python -m venv .venv`. Un entorno `.venv` copiado desde otra máquina o instalación puede no funcionar: se regenera a partir del archivo de dependencias; nunca se debe borrar `private/` al repararlo.

## Configuración

`.env.example` es una referencia: el programa no carga archivos `.env` automáticamente.

| Variable | Valor y uso |
| --- | --- |
| `APP_SECRET` | Obligatoria; al menos 32 caracteres aleatorios. No debe aparecer en Git, HTML ni mensajes. |
| `APP_ORIGIN` | Origen exacto; por defecto `http://127.0.0.1:8765`. Sin ruta ni credenciales. |
| `APP_ENV` | `development` para uso local; `production` exige HTTPS. |
| `PORT` | Puerto de Waitress; debe corresponder al origen local. Por defecto 8765. |
| `DATA_DIR` | Carpeta privada; por defecto `private/` en la raíz del proyecto. |
| `SESSION_SECONDS` | Duración máxima: 28800 segundos por defecto. Debe ser positiva. |
| `SESSION_IDLE_SECONDS` | Inactividad: 1800 segundos por defecto. La actualización de actividad se agrupa en intervalos de hasta 30 segundos. |

`start-local.ps1` administra la clave estable en `%LOCALAPPDATA%\TamaraAdmin\server-key.dpapi`, protegida para tu cuenta de Windows. No la copies a la carpeta pública. Al cambiar la clave se invalidan las sesiones, pero los usuarios y el contenido permanecen.

No cambies `DATA_DIR` sin trasladar deliberadamente tus datos: una carpeta nueva comienza sin tu usuario y sin tus ediciones. No se ha movido la base actual. Aunque la carpeta entregada está bajo OneDrive, la base activa debe permanecer en almacenamiento local sin sincronización simultánea; planifica su traslado con un respaldo y el servidor detenido.

## Estructura y mantenimiento

- `tamara/config.py`, `database.py`, `security.py`, `validation.py`: configuración, persistencia, seguridad y esquema del editor.
- `tamara/routes/`: páginas públicas, autenticación, administrador y archivos multimedia.
- `tamara/services/`: contenido, renderizado, subidas y respaldos.
- `templates/`: HTML público y privado.
- `static/css/`, `static/js/public/`, `static/js/admin/`, `static/js/shared/`: presentación y lógica por responsabilidad.
- `static/assets/`: imágenes y fuentes conservadas byte por byte.
- `content/`: valores originales y etiquetas del editor. El contenido vigente está en SQLite, no se sustituye editando los valores originales.
- `private/`: SQLite, usuarios, versiones y fotografías cargadas. No se publica ni se incluye en el ZIP de código.
- `tests/`: pruebas que usan datos temporales.
- `docs/legacy/`: documentación histórica, conservada como referencia; las instrucciones actuales son las de esta entrega.

`app.py` mantiene las importaciones compatibles. Las URL `/css/`, `/js/`, `/assets/` y `/admin-assets/` siguen funcionando aunque los archivos estén reorganizados. No se necesita compilación del frontend.

## Pruebas

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -t . -v
```

Las pruebas crean usuarios y bases temporales; no utilizan tu cuenta real. Los resultados y su alcance están en `docs/VERIFICACION.md`.

## Documentación de uso

- [Guía de la página principal](docs/GUIA_DE_USO.md)
- [Administración paso a paso](docs/ADMINISTRACION.md)
- [Auditoría y correcciones](docs/AUDITORIA.md)
- [Verificación y limitaciones](docs/VERIFICACION.md)

No se desplegó ni publicó el sitio en un servicio externo. Para producción se requiere configurar HTTPS, proxy, permisos y respaldos; la configuración local no equivale a un despliegue listo para Internet.
