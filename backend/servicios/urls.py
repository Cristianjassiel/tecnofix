# backend/servicios/urls_bryan.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views_bryan
from . import forms_bryan

urlpatterns = [
    # --- PANTALLAS DE CLIENTE ---
    path('ordenes/<str:folio>/aprobar/', views_bryan.aprobar_cotizacion, name='aprobar_cotizacion'),
    
    # --- FLUJO DE RECUPERAR CONTRASEÑA ---
    # 1. Ingresar correo
    path('recuperar-password/', views_bryan.CustomPasswordResetView.as_view(), name='password_reset'),
    
    # 2. Mensaje de "Correo enviado"
    path('recuperar-password/enviado/', auth_views.PasswordResetDoneView.as_view(
        template_name='auth/password_reset_done.html'
    ), name='password_reset_done'),
    
    # 3. Pantalla del token para escribir nueva contraseña
    path('recuperar-password/confirmar/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='auth/password_reset_confirm.html',
        form_class=forms_bryan.NuevaPasswordForm
    ), name='password_reset_confirm'),
    
    # 4. Mensaje de éxito
    path('recuperar-password/completo/', auth_views.PasswordResetCompleteView.as_view(
        template_name='auth/password_reset_complete.html'
    ), name='password_reset_complete'),
]