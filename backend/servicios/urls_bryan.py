from django.urls import path
from django.contrib.auth import views as auth_views
from . import views_bryan
from . import forms_bryan

urlpatterns = [
    # --- PANTALLAS DE CLIENTE ---
    path('ordenes/<str:folio>/aprobar/', views_bryan.aprobar_cotizacion, name='aprobar_cotizacion'),
    path('mis-ordenes/<str:folio>/calificar/', views_bryan.calificar_servicio, name='calificar'),
    
    # --- PANTALLAS DE RECEPCIÓN ---
    path('recepcion/clientes/', views_bryan.lista_clientes, name='clientes'),
    path('recepcion/entrega-cobro/<str:folio>/', views_bryan.entrega_cobro, name='entrega_cobro'),
    
    # --- PANTALLAS DE ADMINISTRACIÓN ---
    path('administracion/usuarios/', views_bryan.admin_usuarios, name='admin_usuarios'),
    path('administracion/catalogo/', views_bryan.admin_catalogo, name='admin_catalogo'),
    
    # --- FLUJO DE RECUPERAR CONTRASEÑA ---
    path('recuperar-password/', views_bryan.CustomPasswordResetView.as_view(), name='password_reset'),
    
    path('recuperar-password/enviado/', auth_views.PasswordResetDoneView.as_view(
        template_name='auth/password_reset_done.html'
    ), name='password_reset_done'),
    
    path('recuperar-password/confirmar/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='auth/password_reset_confirm.html',
        form_class=forms_bryan.NuevaPasswordForm
    ), name='password_reset_confirm'),
    
    path('recuperar-password/completo/', auth_views.PasswordResetCompleteView.as_view(
        template_name='auth/password_reset_complete.html'
    ), name='password_reset_complete'),
]