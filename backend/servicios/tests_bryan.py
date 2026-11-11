# backend/servicios/tests_bryan.py
from django.urls import reverse
from django.contrib.auth.models import User
from django.core import mail
from .tests import BaseTecnoFix
from .models import Estado, Cliente, Cotizacion

class AprobarCotizacionTests(BaseTecnoFix):
    def setUp(self):
        super().setUp()
        self.orden.estado = Estado.REVISION
        self.orden.save()
        
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

    def test_tecnico_no_tiene_acceso(self):
        self.client.login(username='luis', password='prueba1234')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_cliente_no_ve_ordenes_ajenas(self):
        otro_user = User.objects.create_user(username='pedro', password='prueba1234')
        Cliente.objects.create(usuario=otro_user, nombre_completo="Pedro", telefono="123", correo="p@p.com", direccion="X")
        self.client.login(username='pedro', password='prueba1234')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    def test_aprobar_cotizacion_cambia_estado(self):
        self.client.login(username='maria', password='prueba1234')
        response = self.client.post(self.url, {'decision': 'aprobar'})
        
        self.orden.refresh_from_db()
        self.assertEqual(self.orden.estado, Estado.ARREGLANDO)
        self.assertTrue(self.orden.cotizacion.aprobada)

    def test_rechazar_cotizacion_cambia_estado(self):
        self.client.login(username='maria', password='prueba1234')
        response = self.client.post(self.url, {'decision': 'rechazar'})
        
        self.orden.refresh_from_db()
        self.assertEqual(self.orden.estado, Estado.RECHAZADO)
        self.assertFalse(self.orden.cotizacion.aprobada)


class RecuperarPasswordTests(BaseTecnoFix):
    def test_acceso_publico_recuperar_password(self):
        url = reverse('password_reset')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'auth/password_reset.html')
        
    def test_envio_de_correo_exitoso(self):
        url = reverse('password_reset')
        
        # Asignamos un correo válido a la cuenta de prueba de 'ana'
        usuario = User.objects.get(username='ana')
        usuario.email = 'ana@tecnofix.com'
        usuario.save()
        
        # Simulamos que Ana ingresa su correo en el formulario
        response = self.client.post(url, {'email': 'ana@tecnofix.com'})
        
        # Verifica que avance a la pantalla de "Correo enviado"
        self.assertRedirects(response, reverse('password_reset_done'))
        
        # Verifica que Django generó y "envió" el correo con el enlace
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Restablecer', mail.outbox[0].subject)
        
        
class ListaClientesTests(BaseTecnoFix):
    def test_tecnico_puede_ver_lista_clientes(self):
        # luis es un usuario de prueba con rol de técnico
        self.client.login(username='luis', password='prueba1234')
        response = self.client.get(reverse('lista_clientes'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tecnico/lista_clientes.html')
        self.assertIn('clientes', response.context)

    def test_cliente_no_tiene_acceso_a_lista(self):
        # maria es una cliente, no debería poder ver el directorio
        self.client.login(username='maria', password='prueba1234')
        response = self.client.get(reverse('lista_clientes'))
        
        self.assertEqual(response.status_code, 403)