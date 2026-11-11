# backend/servicios/urls_bryan.py
from django.urls import path
from . import views_bryan

urlpatterns = [
    path('ordenes/<str:folio>/aprobar/', views_bryan.aprobar_cotizacion, name='aprobar_cotizacion'),
    # --- PANTALLAS DE TÉCNICO ---
    path('tecnico/clientes/', views_bryan.lista_clientes, name='lista_clientes'),
]

