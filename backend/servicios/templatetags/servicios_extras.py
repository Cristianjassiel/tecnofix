"""Etiquetas y filtros propios para las plantillas."""

from django import template
from django.urls import NoReverseMatch, resolve, reverse
from django.utils.html import format_html

from servicios.models import Estado

register = template.Library()


# Colores de cada estado, tomados de la paleta del proyecto.
COLORES_ESTADO = {
    Estado.RECIBIDO: "bg-slate-100 text-slate-700",
    Estado.DIAGNOSTICO: "bg-amber-100 text-amber-800",
    Estado.REVISION: "bg-blue-100 text-blue-800",
    Estado.RECHAZADO: "bg-red-100 text-red-800",
    Estado.ARREGLANDO: "bg-indigo-100 text-indigo-800",
    Estado.TERMINADO: "bg-teal-100 text-teal-800",
    Estado.ENTREGADO: "bg-emerald-100 text-emerald-800",
}


@register.simple_tag
def badge_estado(estado):
    """Dibuja el estado como una etiqueta de color."""
    if not estado:
        return format_html('<span class="text-stone-500">—</span>')
    clases = COLORES_ESTADO.get(estado, "bg-stone-100 text-stone-700")
    return format_html(
        '<span class="whitespace-nowrap rounded-full px-3 py-1 text-xs font-medium {}">{}</span>',
        clases,
        Estado(estado).label,
    )


@register.simple_tag
def navlink(nombre_url, etiqueta, request):
    """Enlace del navbar, resaltado cuando es la pantalla actual."""
    try:
        destino = reverse(nombre_url)
    except NoReverseMatch:
        # Pantalla de otro compañero que todavía no existe: no se dibuja.
        return ""
    try:
        actual = resolve(request.path_info).url_name == nombre_url
    except Exception:
        actual = False
    clases = (
        "font-medium text-indigo-700" if actual else "hover:text-indigo-600"
    )
    return format_html('<li><a href="{}" class="{}">{}</a></li>', destino, clases, etiqueta)


@register.filter
def campo_clase(campo, clases):
    """Agrega clases de CSS a un campo del formulario desde la plantilla."""
    return campo.as_widget(attrs={"class": clases})
