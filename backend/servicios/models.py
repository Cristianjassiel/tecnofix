"""Modelos del sistema de servicio técnico de TecnoFix Dolores."""

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


# Roles del sistema. Se crean como grupos de Django con el comando crear_roles.
ROL_CLIENTE = "Cliente"
ROL_RECEPCIONISTA = "Recepcionista"
ROL_TECNICO = "Tecnico"
ROL_ADMINISTRADOR = "Administrador"

ROLES = [ROL_CLIENTE, ROL_RECEPCIONISTA, ROL_TECNICO, ROL_ADMINISTRADOR]

# Los nombres de los grupos van sin acento, para usarlos como identificadores.
# Esto es cómo se muestran en pantalla.
ROL_DISPLAY = {
    ROL_CLIENTE: "Cliente",
    ROL_RECEPCIONISTA: "Recepcionista",
    ROL_TECNICO: "Técnico",
    ROL_ADMINISTRADOR: "Administrador",
}


class Estado(models.TextChoices):
    """Los siete estados por los que pasa una orden de servicio."""

    RECIBIDO = "recibido", "Recibido"
    DIAGNOSTICO = "diagnostico", "En diagnóstico"
    REVISION = "revision", "En revisión"
    RECHAZADO = "rechazado", "Rechazado"
    ARREGLANDO = "arreglando", "Arreglando"
    TERMINADO = "terminado", "Terminado"
    ENTREGADO = "entregado", "Entregado"


# Transiciones válidas del flujo: estado actual -> (estado destino, rol que lo hace).
# Cualquier cambio que no esté aquí se rechaza en OrdenServicio.cambiar_estado().
TRANSICIONES = {
    Estado.RECIBIDO: {
        Estado.DIAGNOSTICO: ROL_TECNICO,
    },
    Estado.DIAGNOSTICO: {
        Estado.REVISION: ROL_TECNICO,
    },
    Estado.REVISION: {
        Estado.ARREGLANDO: ROL_CLIENTE,
        Estado.RECHAZADO: ROL_CLIENTE,
    },
    Estado.ARREGLANDO: {
        Estado.TERMINADO: ROL_TECNICO,
    },
    Estado.TERMINADO: {
        Estado.ENTREGADO: ROL_RECEPCIONISTA,
    },
    Estado.RECHAZADO: {},
    Estado.ENTREGADO: {},
}

# Estados en los que la orden ya no avanza más.
ESTADOS_FINALES = (Estado.RECHAZADO, Estado.ENTREGADO)


class TransicionInvalida(Exception):
    """Se intentó un cambio de estado que el flujo no permite."""


class Cliente(models.Model):
    """Cliente del taller. Puede tener o no una cuenta para entrar al sistema."""

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cliente",
        verbose_name="cuenta de acceso",
    )
    nombre_completo = models.CharField("nombre completo", max_length=150)
    telefono = models.CharField("teléfono", max_length=20)
    correo = models.EmailField("correo electrónico", blank=True)
    direccion = models.CharField("dirección", max_length=200, blank=True)

    class Meta:
        verbose_name = "cliente"
        verbose_name_plural = "clientes"
        ordering = ["nombre_completo"]

    def __str__(self):
        return self.nombre_completo


class Equipo(models.Model):
    """Equipo electrónico que ingresa al taller, asociado a un cliente."""

    class Tipo(models.TextChoices):
        CELULAR = "celular", "Celular"
        LAPTOP = "laptop", "Laptop"
        TABLET = "tablet", "Tablet"

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="equipos")
    tipo = models.CharField("tipo de dispositivo", max_length=20, choices=Tipo.choices)
    marca = models.CharField(max_length=50)
    modelo = models.CharField(max_length=50)
    numero_serie = models.CharField("número de serie o IMEI", max_length=100, blank=True)
    color = models.CharField(max_length=30, blank=True)

    class Meta:
        verbose_name = "equipo"
        verbose_name_plural = "equipos"
        ordering = ["marca", "modelo"]

    def __str__(self):
        return f"{self.get_tipo_display()} {self.marca} {self.modelo}"


class Accesorio(models.Model):
    """Catálogo de accesorios que el cliente puede dejar junto con el equipo."""

    nombre = models.CharField(max_length=50, unique=True)

    class Meta:
        verbose_name = "accesorio"
        verbose_name_plural = "accesorios"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Servicio(models.Model):
    """Catálogo de servicios y refacciones con precio de referencia.

    Sirve para que los técnicos coticen con los mismos precios. No lleva
    control de existencias: el inventario de refacciones quedó fuera del
    alcance del sistema.
    """

    nombre = models.CharField(max_length=100)
    tipo_equipo = models.CharField(
        max_length=20, choices=Equipo.Tipo.choices, blank=True
    )
    precio_refaccion = models.DecimalField(
        "precio de refacción", max_digits=8, decimal_places=2, default=0
    )
    precio_mano_obra = models.DecimalField(
        "precio de mano de obra", max_digits=8, decimal_places=2, default=0
    )
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "servicio"
        verbose_name_plural = "servicios y refacciones"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class OrdenServicio(models.Model):
    """Orden de servicio: la entidad que recorre todo el flujo del taller."""

    class Prioridad(models.TextChoices):
        NORMAL = "normal", "Normal"
        URGENTE = "urgente", "Urgente"

    folio = models.CharField(max_length=20, unique=True, editable=False)
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, related_name="ordenes")
    tecnico = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="ordenes_asignadas",
        verbose_name="técnico asignado",
    )
    recibida_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ordenes_recibidas",
        verbose_name="recibida por",
    )

    falla_reportada = models.TextField(
        "falla reportada", help_text="Descripción de la falla en palabras del cliente."
    )
    diagnostico_tecnico = models.TextField("diagnóstico técnico", blank=True)
    notas_reparacion = models.TextField("notas de la reparación", blank=True)

    accesorios = models.ManyToManyField(Accesorio, blank=True)
    otros_accesorios = models.CharField(
        "otros accesorios", max_length=200, blank=True
    )

    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.RECIBIDO
    )
    prioridad = models.CharField(
        max_length=10, choices=Prioridad.choices, default=Prioridad.NORMAL
    )

    fecha_recepcion = models.DateTimeField("fecha de recepción", auto_now_add=True)
    fecha_entrega_estimada = models.DateField(
        "entrega estimada", null=True, blank=True
    )
    fecha_entrega = models.DateTimeField("fecha de entrega", null=True, blank=True)

    costo_final = models.DecimalField(
        "costo final", max_digits=8, decimal_places=2, null=True, blank=True
    )
    metodo_pago = models.CharField("método de pago", max_length=30, blank=True)

    garantia_dias = models.PositiveIntegerField("días de garantía", default=30)
    orden_original = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ordenes_garantia",
        verbose_name="orden original (garantía)",
    )

    class Meta:
        verbose_name = "orden de servicio"
        verbose_name_plural = "órdenes de servicio"
        ordering = ["-fecha_recepcion"]

    def __str__(self):
        return f"Orden {self.folio}"

    def save(self, *args, **kwargs):
        if not self.folio:
            self.folio = self._siguiente_folio()
        super().save(*args, **kwargs)

    @staticmethod
    def _siguiente_folio():
        """Folios consecutivos a partir de 1001."""
        ultimo = OrdenServicio.objects.order_by("-id").values_list("folio", flat=True).first()
        if ultimo and ultimo.isdigit():
            return str(int(ultimo) + 1)
        return "1001"

    # --- Flujo de estados -------------------------------------------------

    @property
    def es_de_garantia(self):
        return self.orden_original_id is not None

    @property
    def esta_cerrada(self):
        return self.estado in ESTADOS_FINALES

    @property
    def en_garantia(self):
        """True si la orden se entregó y sigue dentro del periodo de garantía."""
        if self.estado != Estado.ENTREGADO or not self.fecha_entrega:
            return False
        dias = (timezone.now() - self.fecha_entrega).days
        return dias <= self.garantia_dias

    def transiciones_posibles(self):
        """Estados a los que puede pasar la orden desde su estado actual."""
        return TRANSICIONES.get(self.estado, {})

    def puede_cambiar_a(self, nuevo_estado, usuario):
        """True si ese usuario puede llevar la orden a ese estado."""
        rol_requerido = self.transiciones_posibles().get(nuevo_estado)
        if rol_requerido is None:
            return False
        return usuario_tiene_rol(usuario, rol_requerido)

    def cambiar_estado(self, nuevo_estado, usuario, comentario=""):
        """Cambia el estado de la orden y lo registra en la bitácora.

        Valida dos cosas: que la transición exista en el flujo y que el
        usuario tenga el rol que esa transición requiere. Si alguna falla,
        lanza TransicionInvalida y no se modifica nada.
        """
        estado_anterior = self.estado
        rol_requerido = self.transiciones_posibles().get(nuevo_estado)

        if rol_requerido is None:
            raise TransicionInvalida(
                f"La orden {self.folio} no puede pasar de "
                f"«{self.get_estado_display()}» a «{Estado(nuevo_estado).label}»."
            )

        if not usuario_tiene_rol(usuario, rol_requerido):
            raise TransicionInvalida(
                f"Solo el rol {rol_requerido} puede llevar la orden "
                f"a «{Estado(nuevo_estado).label}»."
            )

        self.estado = nuevo_estado
        if nuevo_estado == Estado.ENTREGADO and not self.fecha_entrega:
            self.fecha_entrega = timezone.now()
        self.save()

        HistorialEstado.objects.create(
            orden=self,
            estado_anterior=estado_anterior,
            estado_nuevo=nuevo_estado,
            usuario=usuario,
            comentario=comentario,
        )
        return self


class Cotizacion(models.Model):
    """Cotización que el técnico genera tras el diagnóstico."""

    orden = models.OneToOneField(
        OrdenServicio, on_delete=models.CASCADE, related_name="cotizacion"
    )
    costo_refaccion = models.DecimalField(
        "costo de refacciones", max_digits=8, decimal_places=2, default=0
    )
    costo_mano_obra = models.DecimalField(
        "costo de mano de obra", max_digits=8, decimal_places=2, default=0
    )
    cargo_diagnostico = models.DecimalField(
        "cargo por diagnóstico", max_digits=8, decimal_places=2, default=0,
        help_text="Se cobra solo si el cliente rechaza la cotización.",
    )
    aprobada = models.BooleanField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_respuesta = models.DateTimeField(
        "fecha de respuesta del cliente", null=True, blank=True
    )

    class Meta:
        verbose_name = "cotización"
        verbose_name_plural = "cotizaciones"

    def __str__(self):
        return f"Cotización de la orden {self.orden.folio}"

    @property
    def total(self):
        return self.costo_refaccion + self.costo_mano_obra

    @property
    def pendiente(self):
        return self.aprobada is None


class HistorialEstado(models.Model):
    """Bitácora: un registro por cada cambio de estado de una orden."""

    orden = models.ForeignKey(
        OrdenServicio, on_delete=models.CASCADE, related_name="historial"
    )
    estado_anterior = models.CharField(
        max_length=20, choices=Estado.choices, blank=True
    )
    estado_nuevo = models.CharField(max_length=20, choices=Estado.choices)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    fecha = models.DateTimeField(auto_now_add=True)
    comentario = models.TextField(blank=True)

    class Meta:
        verbose_name = "cambio de estado"
        verbose_name_plural = "bitácora de auditoría"
        ordering = ["-fecha"]

    def __str__(self):
        anterior = self.get_estado_anterior_display() or "—"
        return f"{self.orden.folio}: {anterior} → {self.get_estado_nuevo_display()}"


class EvidenciaFoto(models.Model):
    """Fotografías del estado físico del equipo al recibirlo y al entregarlo."""

    class Momento(models.TextChoices):
        RECEPCION = "recepcion", "Al recibir"
        REPARACION = "reparacion", "Durante la reparación"
        ENTREGA = "entrega", "Al entregar"

    orden = models.ForeignKey(
        OrdenServicio, on_delete=models.CASCADE, related_name="evidencias"
    )
    imagen = models.ImageField(upload_to="evidencias/%Y/%m/")
    momento = models.CharField(
        max_length=15, choices=Momento.choices, default=Momento.RECEPCION
    )
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "evidencia fotográfica"
        verbose_name_plural = "evidencias fotográficas"
        ordering = ["fecha"]

    def __str__(self):
        return f"{self.get_momento_display()} - orden {self.orden.folio}"


class Calificacion(models.Model):
    """Calificación que el cliente deja cuando se le entrega su equipo."""

    orden = models.OneToOneField(
        OrdenServicio, on_delete=models.CASCADE, related_name="calificacion"
    )
    puntuacion = models.PositiveSmallIntegerField(
        "puntuación",
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    comentario = models.TextField(blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "calificación"
        verbose_name_plural = "calificaciones"
        ordering = ["-fecha"]

    def __str__(self):
        return f"Orden {self.orden.folio}: {self.puntuacion}/5"


# --- Utilidades de roles --------------------------------------------------


def usuario_tiene_rol(usuario, rol):
    """True si el usuario pertenece a ese grupo.

    El administrador tiene acceso completo al sistema, así que se le
    considera parte de cualquier rol.
    """
    if not usuario or not usuario.is_authenticated:
        return False
    if usuario.groups.filter(name=ROL_ADMINISTRADOR).exists():
        return True
    return usuario.groups.filter(name=rol).exists()


def rol_de(usuario):
    """Devuelve el rol principal del usuario, o None si no tiene ninguno."""
    if not usuario or not usuario.is_authenticated:
        return None
    nombres = set(usuario.groups.values_list("name", flat=True))
    for rol in (ROL_ADMINISTRADOR, ROL_RECEPCIONISTA, ROL_TECNICO, ROL_CLIENTE):
        if rol in nombres:
            return rol
    return None
