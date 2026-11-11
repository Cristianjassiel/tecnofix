# backend/servicios/tests_bryan.py
from django.urls import reverse
from django.contrib.auth.models import User
from .tests import BaseTecnoFix
from .models import Estado, Cliente, Cotizacion

class AprobarCotizacionTests(BaseTecnoFix):
    def setUp(self):
        super().setUp()
        # Preparamos la orden de prueba de BaseTecnoFix (le pertenece a 'maria')
        self.orden.estado = Estado.REVISION
        self.orden.save()
        
        # Generamos su cotización pendiente
        Cotizacion.objects.create(
            orden=self.orden,
            costo_refaccion=850.00,
            costo_mano_obra=450.00
        )
        self.url = reverse('aprobar_cotizacion', kwargs={'folio': self.orden.folio})

    def test_cliente_puede_ver_pantalla(self):
        self.client.login(username='maria', password='prueba1234')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'cliente/aprobar_cotizacion.html')
        self.assertContains(response, 'Aprobar cotización')

    def test_tecnico_no_tiene_acceso(self):
        # Un técnico tratando de entrar debe recibir HTTP 403 Forbidden
        self.client.login(username='luis', password='prueba1234')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_cliente_no_ve_ordenes_ajenas(self):
        # Creamos otro usuario cliente
        otro_user = User.objects.create_user(username='pedro', password='prueba1234')
        Cliente.objects.create(usuario=otro_user, nombre_completo="Pedro", telefono="123", correo="p@p.com", direccion="X")
        self.client.login(username='pedro', password='prueba1234')
        
        # Debe recibir un 404 porque el get_object_or_404 filtra por el request.user
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    def test_aprobar_cotizacion_cambia_estado(self):
        self.client.login(username='maria', password='prueba1234')
        response = self.client.post(self.url, {'decision': 'aprobar'})
        
        self.orden.refresh_from_db()
        self.assertEqual(self.orden.estado, Estado.ARREGLANDO)
        self.assertTrue(self.orden.cotizacion.aprobada)
        self.assertIsNotNone(self.orden.cotizacion.fecha_respuesta)
        self.assertRedirects(response, reverse('cliente_orden', kwargs={'folio': self.orden.folio}))

    def test_rechazar_cotizacion_cambia_estado(self):
        self.client.login(username='maria', password='prueba1234')
        response = self.client.post(self.url, {'decision': 'rechazar'})
        
        self.orden.refresh_from_db()
        self.assertEqual(self.orden.estado, Estado.RECHAZADO)
        self.assertFalse(self.orden.cotizacion.aprobada)
        self.assertIsNotNone(self.orden.cotizacion.fecha_respuesta)