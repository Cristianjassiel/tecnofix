# TecnoFix · Parte de Daniel

Implementación de las pantallas de Daniel sobre la base común `backend`.
El contrato de modelos, roles y estados está en [backend/README.md](backend/README.md).

## Arranque rápido en Windows (PowerShell)

Abre PowerShell en la raíz del proyecto.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
cd backend
$env:DB_ENGINE = "sqlite"
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Abrir http://127.0.0.1:8000/. Las cuentas de prueba son `roberto`, `ana`,
`luis`, `jorge`, `maria`, `joseluis` y `anakaren`, con contraseña `demo1234`.
Son únicamente para desarrollo. Para PostgreSQL, seguir el README del backend.
En Linux/macOS activar con `source .venv/bin/activate` y usar
`export DB_ENGINE=sqlite`.

## Pantallas conectadas

| Template original | Ruta | Acceso |
|---|---|---|
| AltaCliente.html | `/recepcion/clientes/nuevo/`, `/recepcion/clientes/<id>/` | Recepción y administrador |
| ListaEquipos.html | `/recepcion/equipos/` | Recepción y administrador |
| AvanzadaOrdenes.html | `/ordenes/buscar/` | Recepción y administrador |
| DetalleOrden.html | `/tecnico/orden/<folio>/` | Técnico asignado y administrador |
| GenerarCotizacion.html | `/tecnico/orden/<folio>/cotizar/` | Técnico asignado y administrador |
| DashboardPrincipalAdmin.html | `/administracion/` | Administrador |
| GraficaAdmin.html | `/administracion/reportes/` | Administrador |

Se agregó `/recepcion/clientes/` para navegar al alta, edición e historial.
Los originales quedan en `prototipos/`; las versiones dinámicas están en
`backend/templates/`. Mantienen el estilo Tailwind y reutilizan `base.html`.
No se requiere una API ni un frontend separado.

## Comportamiento

- Los formularios validan del lado del servidor y muestran errores sin perder datos.
- El listado de equipos tiene búsqueda y paginación. Las órdenes admiten filtros combinados y fechas validadas.
- Cada técnico solo puede abrir y modificar sus órdenes; el administrador puede acceder a todas.
- Se usa `orden.cambiar_estado()` para cada transición. Enviar una cotización guarda sus importes y pasa de diagnóstico a revisión en una transacción.
- No se puede forzar la aprobación desde la pantalla del técnico. El cliente responde desde la pantalla de aprobación incluida en la base común.
- El modelo común guarda un importe agregado de refacciones y otro de mano de obra. No se añadió una tabla de partidas ni se modificaron modelos compartidos.
- El costo final es obligatorio al terminar; las reparaciones por garantía solo admiten importes cero.
- Dashboard y gráficas consultan datos reales. Ingresos y órdenes por técnico corresponden a órdenes entregadas dentro del periodo elegido; no son una pasarela de pagos.
- Las fotos se sirven mediante `/evidencias/<id>/` con permisos por orden; no se exponen por `/media/`. En producción también deben mantenerse privadas.
- El flujo común de recuperación usa tokens de Django y muestra el correo en la terminal durante el desarrollo.

## Archivos de integración

La lógica propia está en `servicios/forms_daniel.py`, `views_daniel.py`,
`urls_daniel.py` y `tests_daniel.py`. Cambios mínimos a archivos comunes:
registro de rutas, navegación del administrador y del directorio de clientes,
URLs privadas de fotos y expectativa de inicio del administrador en una prueba.
No se cambiaron modelos ni migraciones.

La recuperación de contraseña y la aprobación de cotizaciones usan las
rutas existentes de la base común.

## Pruebas

Desde `backend/`, con el entorno activado y la base configurada:

```bash
python manage.py test servicios
python manage.py check
```

Incluyen aislamiento entre técnicos, restricciones por rol, altas y edición,
filtros inválidos, transiciones, importes negativos, cálculos decimales,
recuperación completa de contraseña y privacidad de evidencias.

## Trabajo en equipo

Los cambios de Daniel se revisan contra la rama `backend`.

```bash
git diff origin/backend...daniel-backend
```

El servidor y las cuentas demo son para desarrollo. El README común detalla
los ajustes de producción pendientes, incluida una caché compartida para el
bloqueo de login. Tailwind y Chart.js se cargan por CDN.
