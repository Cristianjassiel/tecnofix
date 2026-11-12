from django.urls import path
from . import views_daniel as views

urlpatterns = [
    path('evidencias/<int:pk>/', views.evidencia, name='evidencia'),
    path('recepcion/clientes/nuevo/', views.cliente_form, name='cliente_nuevo'),
    path('recepcion/clientes/<int:pk>/', views.cliente_form, name='cliente_editar'),
    path('recepcion/equipos/', views.equipos, name='equipos'),
    path('ordenes/buscar/', views.buscar_ordenes, name='buscar_ordenes'),
    path('tecnico/orden/<str:folio>/', views.tecnico_orden, name='tecnico_orden'),
    path('tecnico/orden/<str:folio>/cotizar/', views.generar_cotizacion, name='generar_cotizacion'),
    path('administracion/', views.admin_dashboard, name='admin_dashboard'),
    path('administracion/reportes/', views.reportes, name='reportes'),
]
