"""Clientes, equipos, búsqueda, seguimiento técnico y estadísticas reales."""
from decimal import Decimal
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import get_object_or_404, redirect, render
from .forms_daniel import ActualizarOrdenForm, BuscarOrdenesForm, ClienteForm, CotizacionForm
from .models import Cliente, Cotizacion, Equipo, Estado, OrdenServicio, ROL_ADMINISTRADOR, rol_de
from .permisos import solo_admin, solo_recepcion, solo_tecnico


def _pagina(request, queryset):
    return Paginator(queryset, 20).get_page(request.GET.get('page'))


def _ordenes():
    return OrdenServicio.objects.select_related('equipo__cliente', 'tecnico')


@solo_recepcion
def cliente_form(request, pk=None):
    cliente = get_object_or_404(Cliente, pk=pk) if pk else None
    form = ClienteForm(request.POST if request.method == 'POST' else None, instance=cliente)
    if request.method == 'POST' and form.is_valid():
        cliente = form.save()
        messages.success(request, 'Cliente guardado correctamente.')
        return redirect('cliente_editar', pk=cliente.pk)
    historial = _ordenes().filter(equipo__cliente=cliente) if cliente else []
    return render(request, 'recepcion/AltaCliente.html', {'form': form, 'cliente': cliente, 'ordenes': historial})


@solo_recepcion
def equipos(request):
    q = request.GET.get('q', '').strip()
    objetos = Equipo.objects.select_related('cliente')
    if q:
        objetos = objetos.filter(Q(marca__icontains=q) | Q(modelo__icontains=q) | Q(numero_serie__icontains=q) | Q(cliente__nombre_completo__icontains=q))
    return render(request, 'recepcion/ListaEquipos.html', {'page_obj': _pagina(request, objetos), 'q': q})


@solo_recepcion
def buscar_ordenes(request):
    form = BuscarOrdenesForm(request.GET)
    ordenes = _ordenes()
    if form.is_valid():
        campos = {'folio': 'folio__icontains', 'cliente': 'equipo__cliente__nombre_completo__icontains', 'serie': 'equipo__numero_serie__icontains', 'estado': 'estado', 'fecha_inicio': 'fecha_recepcion__date__gte', 'fecha_fin': 'fecha_recepcion__date__lte'}
        for campo, lookup in campos.items():
            if form.cleaned_data.get(campo):
                ordenes = ordenes.filter(**{lookup: form.cleaned_data[campo]})
    else:
        ordenes = ordenes.none()
    query = request.GET.copy()
    query.pop('page', None)
    return render(request, 'recepcion/AvanzadaOrdenes.html', {'form': form, 'page_obj': _pagina(request, ordenes), 'filtros': query.urlencode()})


def _orden_tecnico(request, folio, bloquear=False):
    # Bloquear solo la fila de la orden; tecnico es una FK nullable.
    qs = OrdenServicio.objects.all()
    if bloquear:
        qs = qs.select_for_update()
    if rol_de(request.user) != ROL_ADMINISTRADOR:
        qs = qs.filter(tecnico=request.user)
    return get_object_or_404(qs, folio=folio)


@solo_tecnico
@transaction.atomic
def tecnico_orden(request, folio):
    orden = _orden_tecnico(request, folio, request.method == 'POST')
    editable = orden.estado in (Estado.RECIBIDO, Estado.DIAGNOSTICO, Estado.ARREGLANDO)
    form = ActualizarOrdenForm(request.POST if request.method == 'POST' else None, orden=orden, initial={'diagnostico_tecnico': orden.diagnostico_tecnico, 'notas_reparacion': orden.notas_reparacion, 'costo_final': orden.costo_final})
    if request.method == 'POST':
        if not editable:
            messages.error(request, 'La orden no permite cambios técnicos en este estado.')
            return redirect('tecnico_orden', folio=folio)
        if form.is_valid():
            data = form.cleaned_data
            orden.diagnostico_tecnico = data['diagnostico_tecnico']
            orden.notas_reparacion = data['notas_reparacion']
            if data['nuevo_estado'] == Estado.TERMINADO:
                orden.costo_final = data['costo_final']
            if data['nuevo_estado']:
                orden.cambiar_estado(data['nuevo_estado'], request.user, 'Actualización del técnico')
            else:
                orden.save(update_fields=['diagnostico_tecnico', 'notas_reparacion'])
            messages.success(request, 'Orden actualizada.')
            return redirect('tecnico_orden', folio=folio)
    return render(request, 'tecnico/DetalleOrden.html', {'orden': orden, 'form': form, 'editable': editable})


@solo_tecnico
@transaction.atomic
def generar_cotizacion(request, folio):
    orden = _orden_tecnico(request, folio, request.method == 'POST')
    if orden.estado != Estado.DIAGNOSTICO:
        messages.error(request, 'Solo se puede cotizar una orden en diagnóstico.')
        return redirect('tecnico_orden', folio=folio)
    form = CotizacionForm(request.POST if request.method == 'POST' else None, initial={'diagnostico_tecnico': orden.diagnostico_tecnico})
    if request.method == 'POST' and form.is_valid():
        if orden.es_de_garantia and any(form.cleaned_data[n] != Decimal('0') for n in form.Meta.fields):
            form.add_error(None, 'Una orden por garantía debe tener todos los importes en cero.')
        elif Cotizacion.objects.filter(orden=orden).exists():
            form.add_error(None, 'Esta orden ya tiene una cotización; revisa su estado.')
        else:
            cotizacion = form.save(commit=False)
            cotizacion.orden = orden
            cotizacion.save()
            orden.diagnostico_tecnico = form.cleaned_data['diagnostico_tecnico']
            orden.cambiar_estado(Estado.REVISION, request.user, 'Cotización enviada a revisión del cliente')
            messages.success(request, 'Cotización disponible en el portal del cliente.')
            return redirect('tecnico_orden', folio=folio)
    return render(request, 'tecnico/GenerarCotizacion.html', {'form': form, 'orden': orden})


@solo_admin
def admin_dashboard(request):
    ordenes = _ordenes()
    # La regla de garantía del modelo es la fuente común del equipo.
    garantias = sum(o.en_garantia for o in ordenes.filter(estado=Estado.ENTREGADO))
    return render(request, 'administracion/DashboardPrincipalAdmin.html', {'en_curso': ordenes.exclude(estado__in=[Estado.ENTREGADO, Estado.RECHAZADO, Estado.TERMINADO]).count(), 'por_entregar': ordenes.filter(estado=Estado.TERMINADO).count(), 'garantias': garantias, 'ordenes': ordenes[:10]})


@solo_admin
def reportes(request):
    form = BuscarOrdenesForm(request.GET)
    cerradas = _ordenes().filter(estado=Estado.ENTREGADO)
    if form.is_valid():
        if form.cleaned_data.get('fecha_inicio'):
            cerradas = cerradas.filter(fecha_entrega__date__gte=form.cleaned_data['fecha_inicio'])
        if form.cleaned_data.get('fecha_fin'):
            cerradas = cerradas.filter(fecha_entrega__date__lte=form.cleaned_data['fecha_fin'])
    else:
        cerradas = cerradas.none()
    meses = list(cerradas.order_by().annotate(mes=TruncMonth('fecha_entrega')).values('mes').annotate(total=Sum('costo_final')).order_by('mes'))
    tecnicos = list(cerradas.order_by().values('tecnico__username').annotate(total=Count('pk')).order_by('tecnico__username'))
    graficas = {'meses': [m['mes'].strftime('%Y-%m') for m in meses], 'ingresos': [float(m['total'] or 0) for m in meses], 'tecnicos': [t['tecnico__username'] or 'Sin técnico' for t in tecnicos], 'ordenes': [t['total'] for t in tecnicos]}
    return render(request, 'administracion/GraficaAdmin.html', {'form': form, 'graficas': graficas, 'total': cerradas.aggregate(total=Sum('costo_final'))['total'] or 0, 'cantidad': cerradas.count(), 'meses': meses, 'tecnicos': tecnicos})


from django.contrib.auth.decorators import login_required
from django.http import FileResponse
from .models import EvidenciaFoto, ROL_CLIENTE, ROL_RECEPCIONISTA, ROL_TECNICO


@login_required
def evidencia(request, pk):
    qs = EvidenciaFoto.objects.select_related('orden__equipo__cliente')
    rol = rol_de(request.user)
    if rol == ROL_TECNICO:
        qs = qs.filter(orden__tecnico=request.user)
    elif rol == ROL_CLIENTE:
        qs = qs.filter(orden__equipo__cliente__usuario=request.user)
    elif rol not in (ROL_ADMINISTRADOR, ROL_RECEPCIONISTA):
        qs = qs.none()
    foto = get_object_or_404(qs, pk=pk)
    return FileResponse(foto.imagen.open('rb'))
