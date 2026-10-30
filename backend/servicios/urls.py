"""Rutas de las pantallas de Cristian.

Los nombres de las rutas (`name=`) son un acuerdo del equipo: las plantillas
enlazan a pantallas de Daniel y Bryan usando estos mismos nombres, y esos
enlaces aparecen solos cuando ellos agreguen sus rutas. Ver el README.
"""

from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    # Autenticación
    path("entrar/", views.LoginConBloqueo.as_view(), name="login"),
    path("salir/", auth_views.LogoutView.as_view(), name="logout"),
    path("", views.inicio, name="inicio"),

    # Recepción
    path("recepcion/nueva-orden/", views.nueva_orden, name="nueva_orden"),
    path("recepcion/equipos/nuevo/", views.equipo_form, name="equipo_nuevo"),
    path("recepcion/equipos/<int:pk>/", views.equipo_form, name="equipo_editar"),
    path("recepcion/ticket/<str:folio>/", views.ticket, name="ticket"),

    # Técnico
    path("tecnico/", views.tecnico_panel, name="tecnico_panel"),

    # Cliente
    path("mis-ordenes/", views.mis_ordenes, name="mis_ordenes"),
    path("mis-ordenes/<str:folio>/", views.cliente_orden, name="cliente_orden"),

    # Administración
    path("administracion/auditoria/", views.admin_auditoria, name="admin_auditoria"),
]
