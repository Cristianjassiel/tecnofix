# backend/servicios/views_bryan.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.views import PasswordResetView
from django.contrib.auth.models import User
from django.urls import reverse_lazy

from .models import OrdenServicio, Estado, TransicionInvalida, Cliente, Calificacion, Servicio
from .permisos import solo_cliente, solo_recepcion, solo_admin
from .forms_bryan import RecuperarPasswordForm, EntregaCobroForm

@solo_cliente
def aprobar_cotizacion(request, folio):
    orden = get_object_or_404(OrdenServicio, folio=folio, equipo__cliente__usuario=request.user)
    if orden.estado != Estado.REVISION:
        messages.error(request, "Esta cotización no está pendiente de revisión.")
        return redirect('cliente_orden', folio=orden.folio)
    if request.method == 'POST':
        decision = request.POST.get('decision')
        if decision == 'aprobar':
            nuevo_estado = Estado.ARREGLANDO
            mensaje_bitacora = "El cliente aprobó la cotización"
            aprobada = True
        elif decision == 'rechazar':
            nuevo_estado = Estado.RECHAZADO
            mensaje_bitacora = "El cliente rechazó la cotización"
            aprobada = False
        else:
            messages.error(request, "Decisión no válida.")
            return redirect('aprobar_cotizacion', folio=folio)
        try:
            orden.cambiar_estado(nuevo_estado, request.user, mensaje_bitacora)
            orden.cotizacion.aprobada = aprobada
            orden.cotizacion.fecha_respuesta = timezone.now()
            orden.cotizacion.save()
            messages.success(request, f"Has {'aprobado' if aprobada else 'rechazado'} la cotización correctamente.")
            return redirect('cliente_orden', folio=orden.folio)
        except TransicionInvalida as error:
            messages.error(request, str(error))
    return render(request, 'cliente/aprobar_cotizacion.html', {'orden': orden})

class CustomPasswordResetView(PasswordResetView):
    template_name = 'auth/password_reset.html'
    form_class = RecuperarPasswordForm
    success_url = reverse_lazy('password_reset_done')

@solo_recepcion
def lista_clientes(request):
    clientes = Cliente.objects.all().order_by('nombre_completo')
    return render(request, 'recepcion/lista_clientes.html', {'clientes': clientes})

@solo_recepcion
def entrega_cobro(request, folio):
    orden = get_object_or_404(OrdenServicio, folio=folio)
    if orden.estado != Estado.TERMINADO:
        messages.error(request, 'Esta orden no está lista para entrega o ya fue entregada.')
        return redirect('clientes')
    if request.method == 'POST':
        form = EntregaCobroForm(request.POST)
        if form.is_valid():
            try:
                orden.metodo_pago = form.cleaned_data['metodo_pago']
                orden.cambiar_estado(Estado.ENTREGADO, request.user, "Se recibió el pago y el equipo fue entregado al cliente.")
                messages.success(request, f"La orden {folio} ha sido cobrada y entregada exitosamente.")
                return redirect('ticket', folio=folio)
            except TransicionInvalida as error:
                messages.error(request, str(error))
    else:
        form = EntregaCobroForm()
    return render(request, 'recepcion/entrega_cobro.html', {'orden': orden, 'form': form})

@solo_cliente
def calificar_servicio(request, folio):
    orden = get_object_or_404(OrdenServicio, folio=folio, equipo__cliente__usuario=request.user)
    if orden.estado != Estado.ENTREGADO:
        messages.error(request, "Solo puedes calificar servicios que ya te han sido entregados.")
        return redirect('cliente_orden', folio=orden.folio)
    if Calificacion.objects.filter(orden=orden).exists():
        messages.info(request, 'Ya calificaste este servicio. ¡Gracias!')
        return redirect('cliente_orden', folio=orden.folio)
    if request.method == 'POST':
        from .forms_bryan import CalificarServicioForm
        form = CalificarServicioForm(request.POST)
        if form.is_valid():
            Calificacion.objects.create(
                orden=orden,
                puntuacion=form.cleaned_data['calificacion'],
                comentario=form.cleaned_data['comentario'],
            )
            messages.success(request, "¡Gracias por tus comentarios! Tu calificación ha sido guardada.")
            return redirect('cliente_orden', folio=orden.folio)
    else:
        from .forms_bryan import CalificarServicioForm
        form = CalificarServicioForm()
    return render(request, 'cliente/calificar.html', {'orden': orden, 'form': form})

@solo_admin
def admin_usuarios(request):
    if request.method == 'POST':
        usuario = get_object_or_404(User, pk=request.POST.get('usuario_id'))
        if usuario == request.user:
            messages.error(request, 'No puedes desactivar tu propia cuenta.')
        else:
            usuario.is_active = not usuario.is_active
            usuario.save(update_fields=['is_active'])
            estado = 'activado' if usuario.is_active else 'desactivado'
            messages.success(request, f'Usuario {usuario.username} {estado}.')
        return redirect('admin_usuarios')
    usuarios = User.objects.prefetch_related('groups').order_by('username')
    return render(request, 'administracion/admin_usuarios.html', {'usuarios': usuarios})

@solo_admin
def admin_catalogo(request):
    """Pantalla para consultar y gestionar el catálogo de servicios y refacciones."""
    if request.method == 'POST':
        servicio = get_object_or_404(Servicio, pk=request.POST.get('servicio_id'))
        servicio.activo = not servicio.activo
        servicio.save(update_fields=['activo'])
        estado_txt = 'activado' if servicio.activo else 'desactivado'
        messages.success(request, f'Servicio {servicio.nombre} {estado_txt}.')
        return redirect('admin_catalogo')
        
    servicios = Servicio.objects.all().order_by('nombre')
    return render(request, 'administracion/admin_catalogo.html', {'servicios': servicios})