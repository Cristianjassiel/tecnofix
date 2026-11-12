# backend/servicios/views_bryan.py
from .models import OrdenServicio, Estado, TransicionInvalida, Cliente
from .permisos import solo_cliente, solo_tecnico

from .permisos import solo_cliente, solo_recepcion

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.views import PasswordResetView
from django.urls import reverse_lazy

from .models import OrdenServicio, Estado, TransicionInvalida
from .permisos import solo_cliente
from .forms_bryan import RecuperarPasswordForm

@solo_cliente
def aprobar_cotizacion(request, folio):
    # El usuario logueado solo puede ver la orden si su equipo le pertenece
    orden = get_object_or_404(OrdenServicio, folio=folio, equipo__cliente__usuario=request.user)
    
    # Validar que estemos en el estado correcto donde el cliente tiene la batuta
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
            # La transición escribe sola en la bitácora y valida los permisos
            orden.cambiar_estado(nuevo_estado, request.user, mensaje_bitacora)
            
            # Guardamos la resolución de la cotización
            orden.cotizacion.aprobada = aprobada
            orden.cotizacion.fecha_respuesta = timezone.now()
            orden.cotizacion.save()
            
            messages.success(request, f"Has {'aprobado' if aprobada else 'rechazado'} la cotización correctamente.")
            return redirect('cliente_orden', folio=orden.folio)
            
        except TransicionInvalida as error:
            messages.error(request, str(error))
            
    return render(request, 'cliente/aprobar_cotizacion.html', {'orden': orden})


class CustomPasswordResetView(PasswordResetView):
    """Vista pública para solicitar restablecimiento de contraseña."""
    template_name = 'auth/password_reset.html'
    form_class = RecuperarPasswordForm
    success_url = reverse_lazy('password_reset_done')
    


@solo_recepcion
def lista_clientes(request):
    """Muestra un directorio de todos los clientes registrados a recepción."""
    clientes = Cliente.objects.all().order_by('nombre_completo')
    # Actualiza la ruta del render
    return render(request, 'recepcion/lista_clientes.html', {'clientes': clientes})