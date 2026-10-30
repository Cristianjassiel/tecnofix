"""Vistas de las pantallas de Cristian.

Autenticación, recepción de órdenes (nueva orden, equipo, ticket), panel del
técnico, seguimiento del cliente y bitácora de auditoría.
"""

from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.contrib.auth.views import LoginView
from django.core.cache import cache
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from .forms import EquipoForm, NuevaOrdenForm
from .models import (
    ROL_ADMINISTRADOR,
    ROL_CLIENTE,
    ROL_DISPLAY,
    ROL_RECEPCIONISTA,
    ROL_TECNICO,
    Cliente,
    Equipo,
    Estado,
    EvidenciaFoto,
    HistorialEstado,
    OrdenServicio,
    rol_de,
)
from .permisos import recepcion_o_admin, solo_admin, solo_cliente, solo_recepcion, solo_tecnico

# Pasos que se muestran en la barra de seguimiento del cliente.
PASOS_FLUJO = [
    Estado.RECIBIDO,
    Estado.DIAGNOSTICO,
    Estado.REVISION,
    Estado.ARREGLANDO,
    Estado.TERMINADO,
    Estado.ENTREGADO,
]

# Bloqueo temporal de la cuenta tras varios intentos fallidos de inicio de sesión.
MAX_INTENTOS = 5
MINUTOS_BLOQUEO = 15


# --- Autenticación --------------------------------------------------------


class LoginConBloqueo(LoginView):
    """Inicio de sesión que bloquea la cuenta unos minutos tras varios fallos.

    Los intentos se cuentan por nombre de usuario en la caché de Django. Un
    inicio de sesión correcto reinicia la cuenta.
    """

    template_name = "auth/login.html"

    @staticmethod
    def _clave(username):
        return f"login-fallos:{(username or '').strip().lower()}"

    def post(self, request, *args, **kwargs):
        username = request.POST.get("username", "")
        if cache.get(self._clave(username), 0) >= MAX_INTENTOS:
            # Ni siquiera se revisa la contraseña mientras dure el bloqueo.
            form = self.get_form()
            form.is_valid()
            form.errors.clear()
            self.bloqueado = True
            return self.render_to_response(self.get_context_data(form=form))
        return super().post(request, *args, **kwargs)

    def form_invalid(self, form):
        username = self.request.POST.get("username", "")
        clave = self._clave(username)
        cache.set(clave, cache.get(clave, 0) + 1, MINUTOS_BLOQUEO * 60)
        self.bloqueado = cache.get(clave, 0) >= MAX_INTENTOS
        return super().form_invalid(form)

    def form_valid(self, form):
        cache.delete(self._clave(form.cleaned_data["username"]))
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["bloqueado"] = getattr(self, "bloqueado", False)
        contexto["minutos_bloqueo"] = MINUTOS_BLOQUEO
        return contexto


def _primera_url(*nombres):
    """La primera ruta que exista, para no depender de pantallas de otros."""
    for nombre in nombres:
        try:
            reverse(nombre)
        except NoReverseMatch:
            continue
        return nombre
    return None


@login_required
def inicio(request):
    """Manda a cada usuario a la pantalla que le corresponde según su rol."""
    destinos = {
        ROL_ADMINISTRADOR: _primera_url("admin_dashboard", "admin_auditoria"),
        ROL_RECEPCIONISTA: "nueva_orden",
        ROL_TECNICO: "tecnico_panel",
        ROL_CLIENTE: "mis_ordenes",
    }
    destino = destinos.get(rol_de(request.user))
    if destino:
        return redirect(destino)
    messages.warning(
        request,
        "Tu cuenta no tiene un rol asignado. Pide al administrador que te asigne uno.",
    )
    return render(request, "sin_rol.html")


# --- Recepción ------------------------------------------------------------


@solo_recepcion
def nueva_orden(request):
    """Recepción de un equipo: crea la orden y genera su ticket."""
    tecnicos = User.objects.filter(groups__name=ROL_TECNICO).order_by("first_name")

    if request.method == "POST":
        form = NuevaOrdenForm(request.POST, request.FILES, tecnicos=tecnicos)
        if form.is_valid():
            datos = form.cleaned_data

            cliente = datos["cliente_existente"]
            if not cliente:
                cliente = Cliente.objects.create(
                    nombre_completo=datos["nuevo_nombre"].strip(),
                    telefono=datos["nuevo_telefono"].strip(),
                    correo=datos["nuevo_correo"] or "",
                )

            equipo = Equipo.objects.create(
                cliente=cliente,
                tipo=datos["tipo"],
                marca=datos["marca"],
                modelo=datos["modelo"],
                numero_serie=datos["numero_serie"],
            )

            # La entrega estimada la calcula el sistema: una semana para la
            # prioridad normal, tres días para la urgente.
            dias = 3 if datos["prioridad"] == OrdenServicio.Prioridad.URGENTE else 7
            orden = OrdenServicio.objects.create(
                equipo=equipo,
                tecnico=datos["tecnico"],
                recibida_por=request.user,
                falla_reportada=datos["falla_reportada"],
                prioridad=datos["prioridad"],
                otros_accesorios=datos["otros_accesorios"],
                fecha_entrega_estimada=timezone.localdate() + timedelta(days=dias),
            )
            orden.accesorios.set(datos["accesorios"])

            for imagen in request.FILES.getlist("fotos"):
                EvidenciaFoto.objects.create(
                    orden=orden, imagen=imagen, momento=EvidenciaFoto.Momento.RECEPCION
                )

            # La orden nace en "Recibido": queda el primer registro en la bitácora.
            HistorialEstado.objects.create(
                orden=orden,
                estado_anterior="",
                estado_nuevo=Estado.RECIBIDO,
                usuario=request.user,
                comentario="Recepción del equipo",
            )

            messages.success(request, f"Se creó la orden {orden.folio}.")
            return redirect("ticket", folio=orden.folio)
    else:
        form = NuevaOrdenForm(tecnicos=tecnicos)

    return render(request, "recepcion/nueva_orden.html", {"form": form})


@solo_recepcion
def equipo_form(request, pk=None):
    """Alta y edición de un equipo, con su historial de órdenes."""
    equipo = get_object_or_404(Equipo, pk=pk) if pk else None
    if request.method == "POST":
        form = EquipoForm(request.POST, instance=equipo)
        if form.is_valid():
            guardado = form.save()
            messages.success(request, f"Se guardó el equipo {guardado}.")
            return redirect("equipo_editar", pk=guardado.pk)
    else:
        form = EquipoForm(instance=equipo)

    historial = (
        equipo.ordenes.select_related("equipo").order_by("-fecha_recepcion")
        if equipo
        else []
    )
    return render(
        request,
        "recepcion/equipo_form.html",
        {"form": form, "equipo": equipo, "historial": historial},
    )


@recepcion_o_admin
def ticket(request, folio):
    """Ticket de recepción, pensado para imprimirse o guardarse en PDF."""
    orden = get_object_or_404(
        OrdenServicio.objects.select_related("equipo__cliente", "tecnico"), folio=folio
    )
    return render(request, "recepcion/ticket.html", {"orden": orden})


# --- Técnico --------------------------------------------------------------


@solo_tecnico
def tecnico_panel(request):
    """Panel del técnico: solo sus órdenes asignadas."""
    ordenes = (
        OrdenServicio.objects.filter(tecnico=request.user)
        .select_related("equipo__cliente")
        .order_by("fecha_recepcion")
    )
    return render(request, "tecnico/panel.html", {"ordenes": ordenes})


# --- Cliente --------------------------------------------------------------


def _cliente_de(usuario):
    return getattr(usuario, "cliente", None)


@solo_cliente
def mis_ordenes(request):
    """Lista de las órdenes del cliente que inició sesión."""
    cliente = _cliente_de(request.user)
    ordenes = (
        OrdenServicio.objects.filter(equipo__cliente=cliente)
        .select_related("equipo")
        .order_by("-fecha_recepcion")
        if cliente
        else OrdenServicio.objects.none()
    )
    return render(request, "cliente/mis_ordenes.html", {"ordenes": ordenes})


@solo_cliente
def cliente_orden(request, folio):
    """Seguimiento de una orden: estado, datos y evidencia."""
    cliente = _cliente_de(request.user)
    orden = (
        OrdenServicio.objects.select_related("equipo__cliente")
        .filter(folio=folio, equipo__cliente=cliente)
        .first()
        if cliente
        else None
    )
    if orden is None:
        messages.error(request, "No encontramos esa orden entre tus equipos.")
        return redirect("mis_ordenes")

    # Barra de seguimiento: hasta dónde llegó la orden.
    if orden.estado == Estado.RECHAZADO:
        pasos = [Estado.RECIBIDO, Estado.DIAGNOSTICO, Estado.REVISION, Estado.RECHAZADO]
        actual = len(pasos) - 1
    else:
        pasos = PASOS_FLUJO
        actual = pasos.index(Estado(orden.estado))

    seguimiento = [
        {
            "etiqueta": Estado(paso).label,
            "completado": indice <= actual,
            "actual": indice == actual,
        }
        for indice, paso in enumerate(pasos)
    ]

    return render(
        request,
        "cliente/orden.html",
        {"orden": orden, "seguimiento": seguimiento},
    )


# --- Administración -------------------------------------------------------


@solo_admin
def admin_auditoria(request):
    """Bitácora: quién cambió el estado de cada orden."""
    registros = HistorialEstado.objects.select_related(
        "orden", "usuario"
    ).order_by("-fecha")[:200]

    # El rol de cada usuario, para mostrarlo bajo su nombre.
    roles = {
        grupo.name: set(grupo.user_set.values_list("id", flat=True))
        for grupo in Group.objects.all()
    }

    filas = []
    for registro in registros:
        rol = ""
        if registro.usuario_id:
            for nombre, ids in roles.items():
                if registro.usuario_id in ids:
                    rol = ROL_DISPLAY.get(nombre, nombre)
                    break
        filas.append({"registro": registro, "rol": rol})

    return render(request, "administracion/auditoria.html", {"filas": filas})
