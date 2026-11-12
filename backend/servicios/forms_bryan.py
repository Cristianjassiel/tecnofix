# backend/servicios/forms_bryan.py
from django import forms
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from .forms import EstiloTailwindMixin

class RecuperarPasswordForm(EstiloTailwindMixin, PasswordResetForm):
    """Formulario para ingresar el correo con clases de Tailwind."""
    pass

class NuevaPasswordForm(EstiloTailwindMixin, SetPasswordForm):
    """Formulario para escribir la nueva contraseña con clases de Tailwind."""
    pass

class EntregaCobroForm(EstiloTailwindMixin, forms.Form):
    OPCIONES_PAGO = [
        ('efectivo', 'Efectivo'),
        ('tarjeta', 'Tarjeta'),
        ('transferencia', 'Transferencia')
    ]
    metodo_pago = forms.ChoiceField(
        choices=OPCIONES_PAGO, 
        label="Método de Pago",
        widget=forms.Select(attrs={'class': 'w-full rounded border-stone-300'})
    )
    
    
class CalificarServicioForm(EstiloTailwindMixin, forms.Form):
    calificacion = forms.IntegerField(
        min_value=1, max_value=5,
        label="Calificación (1 a 5 estrellas)",
        widget=forms.NumberInput(attrs={'class': 'w-full rounded border-stone-300', 'placeholder': '5'})
    )
    comentario = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'w-full rounded border-stone-300', 'rows': 3, 'placeholder': '¿Cómo te pareció el servicio?'}),
        required=False,
        label="Comentarios (opcional)"
    )