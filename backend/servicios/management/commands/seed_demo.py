"""Carga datos de ejemplo para probar el sistema sin capturar todo a mano.

Crea los cuatro roles, el personal de TecnoFix Dolores, algunos clientes con
sus equipos y órdenes en distintos puntos del flujo.

    python manage.py seed_demo

La contraseña de todas las cuentas es demo1234. Es solo para desarrollo.
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from servicios.models import (
    ROL_ADMINISTRADOR,
    ROL_CLIENTE,
    ROL_RECEPCIONISTA,
    ROL_TECNICO,
    ROLES,
    Accesorio,
    Calificacion,
    Cliente,
    Cotizacion,
    Equipo,
    Estado,
    HistorialEstado,
    OrdenServicio,
    Servicio,
)

PASSWORD = "demo1234"

ACCESORIOS = ["Cargador", "Cable USB", "Funda", "Memoria SD", "Tarjeta SIM"]

SERVICIOS = [
    ("Cambio de pantalla", "celular", "1400.00", "450.00"),
    ("Cambio de batería", "celular", "550.00", "250.00"),
    ("Cambio de puerto de carga", "celular", "300.00", "350.00"),
    ("Limpieza por líquido", "celular", "0.00", "600.00"),
    ("Cambio de teclado", "laptop", "700.00", "400.00"),
    ("Cambio de disco a SSD", "laptop", "1200.00", "350.00"),
    ("Reinstalación de sistema operativo", "laptop", "0.00", "500.00"),
    ("Cambio de cristal", "tablet", "900.00", "450.00"),
]

PERSONAL = [
    ("roberto", "Roberto", "Salinas", ROL_ADMINISTRADOR),
    ("ana", "Ana", "Martínez", ROL_RECEPCIONISTA),
    ("luis", "Luis", "Torres", ROL_TECNICO),
    ("jorge", "Jorge", "Ramírez", ROL_TECNICO),
]

CLIENTES = [
    ("maria", "María Fernanda Ruiz Soto", "418 555 0142", "maria.ruiz@ejemplo.com"),
    ("joseluis", "José Luis Pérez Ramírez", "418 555 0177", "jl.perez@ejemplo.com"),
    ("anakaren", "Ana Karen Gómez Díaz", "418 555 0163", "ak.gomez@ejemplo.com"),
]


class Command(BaseCommand):
    help = "Carga usuarios, catálogos y órdenes de ejemplo."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limpiar",
            action="store_true",
            help="Borra las órdenes, equipos y clientes antes de cargar los datos.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["limpiar"]:
            OrdenServicio.objects.all().delete()
            Equipo.objects.all().delete()
            Cliente.objects.all().delete()
            self.stdout.write("Datos anteriores borrados.")

        grupos = {rol: Group.objects.get_or_create(name=rol)[0] for rol in ROLES}

        accesorios = {
            nombre: Accesorio.objects.get_or_create(nombre=nombre)[0]
            for nombre in ACCESORIOS
        }

        for nombre, tipo, refaccion, mano_obra in SERVICIOS:
            Servicio.objects.get_or_create(
                nombre=nombre,
                defaults={
                    "tipo_equipo": tipo,
                    "precio_refaccion": Decimal(refaccion),
                    "precio_mano_obra": Decimal(mano_obra),
                },
            )

        # Personal del taller
        usuarios = {}
        for username, nombre, apellido, rol in PERSONAL:
            usuario = self._usuario(username, nombre, apellido, grupos[rol])
            if rol == ROL_ADMINISTRADOR:
                usuario.is_staff = True
                usuario.is_superuser = True
                usuario.save()
            usuarios[username] = usuario

        ana = usuarios["ana"]
        luis = usuarios["luis"]
        jorge = usuarios["jorge"]

        # Clientes con su cuenta de acceso
        clientes = {}
        for username, nombre_completo, telefono, correo in CLIENTES:
            partes = nombre_completo.split()
            usuario = self._usuario(
                username, partes[0], " ".join(partes[1:]), grupos[ROL_CLIENTE]
            )
            cliente, _ = Cliente.objects.get_or_create(
                nombre_completo=nombre_completo,
                defaults={"telefono": telefono, "correo": correo},
            )
            cliente.usuario = usuario
            cliente.telefono = telefono
            cliente.correo = correo
            cliente.save()
            clientes[username] = cliente

        # Órdenes de ejemplo, una por cada punto del flujo
        self._crear_ordenes(clientes, ana, luis, jorge, accesorios)

        self.stdout.write(self.style.SUCCESS("\nDatos de ejemplo cargados."))
        self.stdout.write("\nCuentas (contraseña: demo1234)")
        self.stdout.write("  roberto   Administrador")
        self.stdout.write("  ana       Recepcionista")
        self.stdout.write("  luis      Técnico, celulares")
        self.stdout.write("  jorge     Técnico, laptops y tablets")
        self.stdout.write("  maria     Cliente, con una cotización pendiente")
        self.stdout.write("  joseluis  Cliente")
        self.stdout.write("  anakaren  Cliente")

    # --- Auxiliares -------------------------------------------------------

    def _usuario(self, username, nombre, apellido, grupo):
        usuario, creado = User.objects.get_or_create(
            username=username,
            defaults={
                "first_name": nombre,
                "last_name": apellido,
                "email": f"{username}@tecnofix.mx",
            },
        )
        if creado:
            usuario.set_password(PASSWORD)
            usuario.save()
        usuario.groups.add(grupo)
        return usuario

    def _crear_ordenes(self, clientes, ana, luis, jorge, accesorios):
        """Crea órdenes en distintos estados, avanzándolas por el flujo real."""
        if OrdenServicio.objects.exists():
            self.stdout.write("Ya hay órdenes registradas; no se crean más.")
            return

        hoy = timezone.localdate()

        definiciones = [
            # (cliente, tipo, marca, modelo, serie, falla, técnico, prioridad, estado destino)
            (
                "maria", "celular", "Samsung", "Galaxy A54", "356938110123456",
                "Se me cayó y la pantalla se ve con rayas verdes; a veces no responde al tacto.",
                luis, "normal", Estado.REVISION,
            ),
            (
                "joseluis", "celular", "Motorola", "G32", "356938110987654",
                "La pantalla está estrellada.",
                luis, "normal", Estado.RECHAZADO,
            ),
            (
                "anakaren", "celular", "Huawei", "P30 Lite", "356938110555111",
                "No enciende después de que se mojó.",
                luis, "urgente", Estado.ARREGLANDO,
            ),
            (
                "maria", "laptop", "HP", "Pavilion 15", "5CD1234ABC",
                "Se calienta mucho y se apaga sola.",
                jorge, "normal", Estado.TERMINADO,
            ),
            (
                "joseluis", "tablet", "Lenovo", "Tab M10", "HA1B2C3D",
                "La batería ya no dura nada.",
                jorge, "normal", Estado.ENTREGADO,
            ),
            (
                "anakaren", "celular", "Xiaomi", "Redmi Note 12", "356938110222333",
                "No carga; el puerto de carga se siente flojo.",
                luis, "urgente", Estado.DIAGNOSTICO,
            ),
            (
                "maria", "laptop", "Dell", "Inspiron 14", "7HK88L2",
                "El teclado tiene varias teclas que no responden.",
                jorge, "normal", Estado.RECIBIDO,
            ),
        ]

        for (
            clave_cliente, tipo, marca, modelo, serie, falla, tecnico, prioridad, destino
        ) in definiciones:
            cliente = clientes[clave_cliente]
            equipo = Equipo.objects.create(
                cliente=cliente,
                tipo=tipo,
                marca=marca,
                modelo=modelo,
                numero_serie=serie,
            )
            dias = 3 if prioridad == "urgente" else 7
            orden = OrdenServicio.objects.create(
                equipo=equipo,
                tecnico=tecnico,
                recibida_por=ana,
                falla_reportada=falla,
                prioridad=prioridad,
                fecha_entrega_estimada=hoy + timedelta(days=dias),
            )
            orden.accesorios.set(
                [accesorios["Cargador"], accesorios["Cable USB"]]
                if tipo != "celular"
                else [accesorios["Cargador"], accesorios["Funda"], accesorios["Tarjeta SIM"]]
            )
            HistorialEstado.objects.create(
                orden=orden,
                estado_anterior="",
                estado_nuevo=Estado.RECIBIDO,
                usuario=ana,
                comentario="Recepción del equipo",
            )

            self._avanzar(orden, destino, tecnico, cliente, ana)

        self.stdout.write(f"  {OrdenServicio.objects.count()} órdenes creadas.")

    def _avanzar(self, orden, destino, tecnico, cliente, ana):
        """Lleva la orden hasta el estado destino pasando por el flujo real.

        Usa cambiar_estado(), así que cada paso queda registrado en la
        bitácora igual que si lo hubiera hecho una persona.
        """
        if destino == Estado.RECIBIDO:
            return

        orden.cambiar_estado(Estado.DIAGNOSTICO, tecnico, "Inicia el diagnóstico")
        if destino == Estado.DIAGNOSTICO:
            return

        orden.diagnostico_tecnico = (
            "Se revisó el equipo y se identificó la pieza dañada. "
            "Se requiere reemplazo de refacción."
        )
        orden.save()
        Cotizacion.objects.create(
            orden=orden,
            costo_refaccion=Decimal("1400.00"),
            costo_mano_obra=Decimal("450.00"),
            cargo_diagnostico=Decimal("150.00"),
        )
        orden.cambiar_estado(Estado.REVISION, tecnico, "Cotización enviada al cliente")
        if destino == Estado.REVISION:
            return

        usuario_cliente = cliente.usuario
        if destino == Estado.RECHAZADO:
            orden.cotizacion.aprobada = False
            orden.cotizacion.fecha_respuesta = timezone.now()
            orden.cotizacion.save()
            orden.cambiar_estado(
                Estado.RECHAZADO, usuario_cliente, "El cliente rechazó la cotización"
            )
            return

        orden.cotizacion.aprobada = True
        orden.cotizacion.fecha_respuesta = timezone.now()
        orden.cotizacion.save()
        orden.cambiar_estado(
            Estado.ARREGLANDO, usuario_cliente, "El cliente aprobó la cotización"
        )
        if destino == Estado.ARREGLANDO:
            return

        orden.notas_reparacion = "Se reemplazó la pieza y se probó el equipo."
        orden.costo_final = orden.cotizacion.total
        orden.save()
        orden.cambiar_estado(Estado.TERMINADO, tecnico, "Reparación concluida")
        if destino == Estado.TERMINADO:
            return

        orden.metodo_pago = "efectivo"
        orden.save()
        orden.cambiar_estado(Estado.ENTREGADO, ana, "Equipo entregado y cobrado")
        Calificacion.objects.create(
            orden=orden,
            puntuacion=5,
            comentario="Muy buena atención y entregaron antes de lo que me dijeron.",
        )
