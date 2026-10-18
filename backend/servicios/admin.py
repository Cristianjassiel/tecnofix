"""Panel de administración de Django.

Es una herramienta interna para dar de alta usuarios y catálogos durante el
desarrollo. Lo que usan Ana, los técnicos, Roberto y los clientes son las
pantallas propias del sistema.
"""

from django.contrib import admin

from .models import (
    Accesorio,
    Calificacion,
    Cliente,
    Cotizacion,
    Equipo,
    EvidenciaFoto,
    HistorialEstado,
    OrdenServicio,
    Servicio,
)


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nombre_completo", "telefono", "correo", "usuario")
    search_fields = ("nombre_completo", "telefono", "correo")


@admin.register(Equipo)
class EquipoAdmin(admin.ModelAdmin):
    list_display = ("marca", "modelo", "tipo", "numero_serie", "cliente")
    list_filter = ("tipo", "marca")
    search_fields = ("marca", "modelo", "numero_serie", "cliente__nombre_completo")


class HistorialInline(admin.TabularInline):
    model = HistorialEstado
    extra = 0
    readonly_fields = ("estado_anterior", "estado_nuevo", "usuario", "fecha", "comentario")
    can_delete = False


class EvidenciaInline(admin.TabularInline):
    model = EvidenciaFoto
    extra = 0


@admin.register(OrdenServicio)
class OrdenServicioAdmin(admin.ModelAdmin):
    list_display = ("folio", "equipo", "estado", "prioridad", "tecnico", "fecha_recepcion")
    list_filter = ("estado", "prioridad", "tecnico")
    search_fields = ("folio", "equipo__numero_serie", "equipo__cliente__nombre_completo")
    readonly_fields = ("folio", "fecha_recepcion")
    filter_horizontal = ("accesorios",)
    inlines = [HistorialInline, EvidenciaInline]


@admin.register(Cotizacion)
class CotizacionAdmin(admin.ModelAdmin):
    list_display = ("orden", "costo_refaccion", "costo_mano_obra", "total", "aprobada")
    list_filter = ("aprobada",)


@admin.register(HistorialEstado)
class HistorialEstadoAdmin(admin.ModelAdmin):
    list_display = ("fecha", "orden", "estado_anterior", "estado_nuevo", "usuario")
    list_filter = ("estado_nuevo",)
    readonly_fields = ("orden", "estado_anterior", "estado_nuevo", "usuario", "fecha", "comentario")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    list_display = ("nombre", "tipo_equipo", "precio_refaccion", "precio_mano_obra", "activo")
    list_filter = ("tipo_equipo", "activo")


@admin.register(Calificacion)
class CalificacionAdmin(admin.ModelAdmin):
    list_display = ("orden", "puntuacion", "fecha")
    list_filter = ("puntuacion",)


admin.site.register(Accesorio)

admin.site.site_header = "TecnoFix Dolores"
admin.site.site_title = "TecnoFix Dolores"
admin.site.index_title = "Administración del sistema"
