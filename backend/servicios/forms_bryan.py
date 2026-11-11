# backend/servicios/forms_bryan.py
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from .forms import EstiloTailwindMixin

class RecuperarPasswordForm(EstiloTailwindMixin, PasswordResetForm):
    """Formulario para ingresar el correo con clases de Tailwind."""
    pass

class NuevaPasswordForm(EstiloTailwindMixin, SetPasswordForm):
    """Formulario para escribir la nueva contraseña con clases de Tailwind."""
    pass