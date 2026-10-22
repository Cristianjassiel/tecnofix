"""Crea los cuatro grupos de usuarios del sistema."""

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from servicios.models import ROLES


class Command(BaseCommand):
    help = "Crea los grupos Cliente, Recepcionista, Tecnico y Administrador."

    def handle(self, *args, **options):
        for rol in ROLES:
            grupo, creado = Group.objects.get_or_create(name=rol)
            estado = "creado" if creado else "ya existía"
            self.stdout.write(f"  {grupo.name}: {estado}")
        self.stdout.write(self.style.SUCCESS("Roles listos."))
