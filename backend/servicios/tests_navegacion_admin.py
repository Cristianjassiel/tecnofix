"""El navbar del administrador enlaza a la gestión de usuarios."""

from django.urls import reverse

from .tests import PASSWORD, BaseTecnoFix


class NavbarAdminTests(BaseTecnoFix):
    def test_admin_ve_el_enlace_a_usuarios(self):
        self.client.login(username="roberto", password=PASSWORD)
        respuesta = self.client.get(reverse("admin_auditoria"))
        self.assertContains(respuesta, reverse("admin_usuarios"))

    def test_recepcion_no_ve_el_enlace_a_usuarios(self):
        self.client.login(username="ana", password=PASSWORD)
        respuesta = self.client.get(reverse("clientes"))
        self.assertNotContains(respuesta, reverse("admin_usuarios"))
