"""Decoradores para restringir cada vista a los roles que le corresponden."""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .models import (
    ROL_ADMINISTRADOR,
    ROL_CLIENTE,
    ROL_RECEPCIONISTA,
    ROL_TECNICO,
    usuario_tiene_rol,
)


def rol_requerido(*roles):
    """Permite el acceso solo a los usuarios que tengan alguno de esos roles.

    El administrador pasa siempre, porque tiene acceso completo al sistema.
    """

    def decorador(vista):
        @wraps(vista)
        @login_required
        def envoltura(request, *args, **kwargs):
            if not any(usuario_tiene_rol(request.user, rol) for rol in roles):
                raise PermissionDenied(
                    "Tu cuenta no tiene permiso para entrar a esta pantalla."
                )
            return vista(request, *args, **kwargs)

        return envoltura

    return decorador


solo_recepcion = rol_requerido(ROL_RECEPCIONISTA)
solo_tecnico = rol_requerido(ROL_TECNICO)
solo_cliente = rol_requerido(ROL_CLIENTE)
solo_admin = rol_requerido(ROL_ADMINISTRADOR)
recepcion_o_admin = rol_requerido(ROL_RECEPCIONISTA, ROL_ADMINISTRADOR)
