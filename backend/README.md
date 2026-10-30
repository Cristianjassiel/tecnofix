# TecnoFix Dolores

Sistema de servicio técnico de electrónicos para el taller TecnoFix Dolores,
desarrollado con Django como proyecto de la materia Infraestructura de
Aplicaciones Web (Unidad 1, grupo GTI174).

Este repositorio es el backend en Django. Cada integrante del equipo
implementa las pantallas que le tocaron en el sorteo, sobre una base común.

## Base común (la define Cristian)

Todo el equipo trabaja sobre estas piezas, que viven en `servicios/models.py`:

- **Modelos**: `Cliente`, `Equipo`, `Accesorio`, `Servicio`, `OrdenServicio`,
  `Cotizacion`, `HistorialEstado`, `EvidenciaFoto`, `Calificacion`.
- **Flujo de estados**: una orden recorre
  `Recibido → En diagnóstico → En revisión → Arreglando → Terminado → Entregado`
  (o `Rechazado` desde «En revisión»). El método `orden.cambiar_estado()` es la
  única forma de avanzar una orden: valida que la transición exista, que el
  usuario tenga el rol que le corresponde y deja el registro en la bitácora.
  Quien programe una pantalla que cambie de estado debe llamar a ese método,
  no modificar el campo `estado` directamente.
- **Roles**: grupos de Django (`Cliente`, `Recepcionista`, `Tecnico`,
  `Administrador`) y los decoradores de `servicios/permisos.py`
  (`solo_recepcion`, `solo_tecnico`, `solo_cliente`, `solo_admin`).
- **Plantilla base**: `templates/base.html`, con Tailwind por CDN y el navbar
  según el rol.

Quién puede hacer cada transición:

| De | A | Quién |
|---|---|---|
| Recibido | En diagnóstico | Técnico |
| En diagnóstico | En revisión | Técnico (al enviar la cotización) |
| En revisión | Arreglando | Cliente (aprueba la cotización) |
| En revisión | Rechazado | Cliente (rechaza la cotización) |
| Arreglando | Terminado | Técnico (captura el costo final) |
| Terminado | Entregado | Recepcionista (cobra y entrega) |

## Pantallas de Cristian (este backend)

| Pantalla | Ruta | Rol | Qué hace |
|---|---|---|---|
| Inicio de sesión | `/entrar/` | Todos | Login y cierre de sesión. Tras 5 intentos fallidos con el mismo usuario bloquea la cuenta 15 minutos. Cada rol llega a su pantalla de inicio. |
| Nueva orden | `/recepcion/nueva-orden/` | Recepcionista | Captura cliente (existente o nuevo), equipo, accesorios, falla, técnico, prioridad y fotos. Calcula la entrega estimada (7 días normal, 3 urgente), asigna el folio y deja el primer registro en la bitácora. |
| Equipo | `/recepcion/equipos/nuevo/` y `/recepcion/equipos/<id>/` | Recepcionista | Alta y edición de un equipo, con el historial de órdenes que ha tenido. |
| Ticket | `/recepcion/ticket/<folio>/` | Recepcionista, Administrador | Ticket imprimible con folio, cliente, equipo, accesorios, falla y técnico. Agrega el costo final cuando el técnico termina, o el cargo por diagnóstico si el cliente rechazó. |
| Órdenes asignadas | `/tecnico/` | Técnico | Lista solo las órdenes del técnico que entró. |
| Mis órdenes | `/mis-ordenes/` | Cliente | Lista solo las órdenes de los equipos del cliente. |
| Detalle de orden | `/mis-ordenes/<folio>/` | Cliente | Barra de seguimiento por estado, datos de la orden, evidencia fotográfica. Un cliente no puede abrir la orden de otro. |
| Auditoría | `/administracion/auditoria/` | Administrador | Bitácora de cambios de estado: fecha, orden, cambio, usuario y su rol. |

## Enlaces entre pantallas del equipo

Las plantillas de este repositorio enlazan a pantallas de Daniel y Bryan
usando nombres de ruta. Mientras esas rutas no existan, el enlace
simplemente no se dibuja y nada se rompe; cuando agreguen su ruta con el
mismo nombre, el enlace aparece solo.

| Nombre de ruta (`name=`) | Argumentos | Pantalla | Se enlaza desde |
|---|---|---|---|
| `aprobar_cotizacion` | `folio` | Aprobar o rechazar cotización | Mis órdenes, detalle de orden |
| `calificar` | `folio` | Calificar el servicio | Mis órdenes, detalle de orden |
| `tecnico_orden` | `folio` | Detalle de la orden del técnico | Órdenes asignadas |
| `equipos` | — | Lista de equipos | Formulario de equipo, navbar |
| `clientes` | — | Lista de clientes | Navbar |
| `buscar_ordenes` | — | Búsqueda avanzada | Ticket, navbar |
| `entrega_cobro` | — | Entrega y cobro | Navbar |
| `admin_dashboard` | — | Dashboard del administrador | Navbar; el administrador entra ahí si existe |
| `password_reset` | — | Recuperar contraseña | Login |

## Tecnología

- Python 3 y Django 5.2
- PostgreSQL (SQLite opcional durante el desarrollo)
- Tailwind CSS por CDN
- Pillow para las fotografías de evidencia

## Cómo correrlo

### 1. Base de datos

```bash
docker compose up -d
```

Levanta PostgreSQL con los datos de conexión que el proyecto espera. Si
prefieres no usar Docker, instala PostgreSQL y crea la base y el usuario, o
usa SQLite exportando `DB_ENGINE=sqlite`.

### 2. Entorno y dependencias

```bash
python3 -m venv venv
source venv/bin/activate        # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Migraciones y datos de ejemplo

```bash
python manage.py migrate
python manage.py crear_roles
python manage.py seed_demo
```

`seed_demo` carga clientes, equipos y siete órdenes en distintos estados,
avanzadas con el flujo real, de modo que la bitácora y las pantallas ya tienen
datos para probar.

### 4. Servidor

```bash
python manage.py runserver
```

El sistema queda en http://127.0.0.1:8000/

## Cuentas de ejemplo

Las crea `seed_demo`. La contraseña de todas es `demo1234`, y son solo para
desarrollo.

| Usuario | Rol | Pantalla que verás |
|---|---|---|
| `ana` | Recepcionista | Nueva orden, equipo, ticket |
| `luis` | Técnico (celulares) | Órdenes asignadas |
| `jorge` | Técnico (laptops y tablets) | Órdenes asignadas |
| `maria` | Cliente | Mis órdenes y detalle |
| `joseluis`, `anakaren` | Cliente | Mis órdenes y detalle |
| `roberto` | Administrador | Auditoría |

## Pruebas

```bash
python manage.py test servicios
```

Cubren el flujo de estados (que una orden no pueda saltarse pasos ni ser
cambiada por el rol equivocado), la bitácora, los permisos por rol, que cada
usuario vea solo lo suyo, la recepción de órdenes, el ticket, el seguimiento
del cliente, la auditoría y el bloqueo de cuenta del login.

## Estructura

```
tecnofix/          configuración del proyecto
servicios/         modelos, vistas, formularios y permisos
  models.py        entidades y flujo de estados (base común)
  permisos.py      decoradores de acceso por rol (base común)
  views.py         vistas de las pantallas de Cristian
  urls.py          rutas de las pantallas de Cristian
  management/      comandos crear_roles y seed_demo
templates/         plantillas, organizadas por rol
docker-compose.yml PostgreSQL para desarrollo
```

## Variables de entorno

Todas tienen un valor por defecto para desarrollo:

| Variable | Para qué |
|---|---|
| `SECRET_KEY` | Clave de Django. En producción es obligatorio cambiarla. |
| `DEBUG` | `1` en desarrollo, `0` en producción. |
| `DB_ENGINE` | `sqlite` para usar SQLite en lugar de PostgreSQL. |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | Conexión a PostgreSQL. |

## Nota sobre el bloqueo de cuenta

El conteo de intentos fallidos se guarda en la caché de Django, que en
desarrollo es en memoria (`CACHES` en `settings.py`). Se reinicia al reiniciar
el servidor. En producción, con varios procesos, hay que usar una caché
compartida como Redis.
