# backend/servicios/tests_bryan.py
from django.urls import reverse
from django.core import mail
from django.contrib.auth.models import User, Group
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
        otro_user.groups.add(Group.objects.get(name="Cliente"))
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
        
        usuario = User.objects.get(username='ana')
        usuario.email = 'ana@tecnofix.com'
        usuario.save()
        
        response = self.client.post(url, {'email': 'ana@tecnofix.com'})
        
        self.assertRedirects(response, reverse('password_reset_done'))
        
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Restablecimiento', mail.outbox[0].subject)
        
        
class ListaClientesTests(BaseTecnoFix):
    def test_recepcion_puede_ver_lista_clientes(self):
        self.client.login(username='ana', password='prueba1234')
        response = self.client.get(reverse('clientes'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recepcion/lista_clientes.html')
        self.assertIn('clientes', response.context)

    def test_cliente_no_tiene_acceso_a_lista(self):
        self.client.login(username='maria', password='prueba1234')
        response = self.client.get(reverse('clientes'))
        
        self.assertEqual(response.status_code, 403)


class EntregaCobroTests(BaseTecnoFix):
    def setUp(self):
        super().setUp()
        self.orden.estado = Estado.TERMINADO
        self.orden.save()
        
        Cotizacion.objects.create(
            orden=self.orden,
            costo_refaccion=100.00,
            costo_mano_obra=200.00,
            aprobada=True
        )
        self.url = reverse('entrega_cobro', kwargs={'folio': self.orden.folio})

    def test_recepcion_puede_ver_pantalla_cobro(self):
        self.client.login(username='ana', password='prueba1234')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'recepcion/entrega_cobro.html')

    def test_cliente_no_tiene_acceso_a_cobro(self):
        self.client.login(username='maria', password='prueba1234')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)
        
    def test_tecnico_no_tiene_acceso_a_cobro(self):
        self.client.login(username='luis', password='prueba1234')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_post_exitoso_cambia_estado_y_metodo_pago(self):
        self.client.login(username='ana', password='prueba1234')
        response = self.client.post(self.url, {'metodo_pago': 'efectivo'})
        
        self.orden.refresh_from_db()
        self.assertEqual(self.orden.estado, Estado.ENTREGADO)
        self.assertEqual(self.orden.metodo_pago, 'efectivo')
        self.assertRedirects(response, reverse('ticket', kwargs={'folio': self.orden.folio}))

    def test_no_terminada_redirige(self):
        self.orden.estado = Estado.ARREGLANDO
        self.orden.save()
        
        self.client.login(username='ana', password='prueba1234')
        response = self.client.get(self.url)
        
        self.assertRedirects(response, reverse('clientes'))
        self.orden.refresh_from_db()
        self.assertEqual(self.orden.estado, Estado.ARREGLANDO)
        
        
class CalificarServicioTests(BaseTecnoFix):
    def setUp(self):
        super().setUp()
        self.orden.estado = Estado.ENTREGADO
        self.orden.save()
        self.url = reverse('calificar', kwargs={'folio': self.orden.folio})

    def test_cliente_puede_ver_pantalla_calificar(self):
        self.client.login(username='maria', password='prueba1234') # Maria es la dueña
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'cliente/calificar.html')

    def test_recepcion_no_tiene_acceso(self):
        self.client.login(username='ana', password='prueba1234')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)
        
    def test_cliente_no_ve_ordenes_ajenas(self):
        otro_user = User.objects.create_user(username='pedro2', password='prueba1234')
        otro_user.groups.add(Group.objects.get(name="Cliente"))
        Cliente.objects.create(usuario=otro_user, nombre_completo="Pedro 2", telefono="123", correo="p@p.com", direccion="X")
        self.client.login(username='pedro2', password='prueba1234')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    def test_no_entregada_redirige(self):
        self.orden.estado = Estado.ARREGLANDO
        self.orden.save()
        
        self.client.login(username='maria', password='prueba1234')
        response = self.client.get(self.url)
        
        self.assertRedirects(response, reverse('cliente_orden', kwargs={'folio': self.orden.folio}))
        
    def test_post_exitoso_guarda_calificacion(self):
        self.client.login(username='maria', password='prueba1234')
        response = self.client.post(self.url, {
            'calificacion': 5,
            'comentario': 'Excelente servicio, muy rápido.'
        })
        
        self.orden.refresh_from_db()
        self.assertEqual(self.orden.calificacion, 5)
        self.assertEqual(self.orden.comentario_cliente, 'Excelente servicio, muy rápido.')
        self.assertRedirects(response, reverse('cliente_orden', kwargs={'folio': self.orden.folio}))