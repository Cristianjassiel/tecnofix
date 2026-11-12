"""Enlace del ticket a la pantalla de Entrega y cobro, y datos de entrega en el ticket."""

from django.urls import reverse
from django.utils import timezone

from .models import Estado
from .tests import PASSWORD, BaseTecnoFix


class TicketEntregaTests(BaseTecnoFix):
    def setUp(self):
        super().setUp()
        self.client.login(username="ana", password=PASSWORD)
        self.url_ticket = reverse("ticket", args=[self.orden.folio])
        self.url_entrega = reverse("entrega_cobro", args=[self.orden.folio])

    def test_ticket_de_orden_terminada_enlaza_a_entrega_y_cobro(self):
        self.orden.estado = Estado.TERMINADO
        self.orden.save()
        respuesta = self.client.get(self.url_ticket)
        self.assertContains(respuesta, self.url_entrega)
        self.assertContains(respuesta, "Registrar entrega")

    def test_ticket_de_orden_no_terminada_no_enlaza_a_entrega(self):
        respuesta = self.client.get(self.url_ticket)
        self.assertNotContains(respuesta, self.url_entrega)

    def test_ticket_de_orden_entregada_muestra_el_pago_y_no_el_enlace(self):
        self.orden.estado = Estado.ENTREGADO
        self.orden.metodo_pago = "tarjeta"
        self.orden.fecha_entrega = timezone.now()
        self.orden.save()
        respuesta = self.client.get(self.url_ticket)
        self.assertContains(respuesta, "Tarjeta")
        self.assertContains(respuesta, "Equipo entregado")
        self.assertNotContains(respuesta, self.url_entrega)
