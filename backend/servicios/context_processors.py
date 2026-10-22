"""Datos que todas las plantillas necesitan."""

from .models import rol_de


def rol_usuario(request):
    """Pone el rol del usuario en el contexto, para dibujar el navbar."""
    return {"rol_actual": rol_de(getattr(request, "user", None))}
