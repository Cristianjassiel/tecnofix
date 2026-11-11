"""Integración de formularios, permisos, cálculos y navegación del equipo."""
from decimal import Decimal
from django.contrib.auth.models import User
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from .tests import BaseTecnoFix
from .models import Cliente, Cotizacion, Estado, HistorialEstado


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class PantallasDanielTests(BaseTecnoFix):
    def entrar(self, usuario):
        self.client.force_login(usuario)

    def test_paginas_y_roles(self):
        rutas = ['clientes', 'cliente_nuevo', 'equipos', 'buscar_ordenes', 'admin_dashboard', 'reportes']
        self.entrar(self.roberto)
        for nombre in rutas:
            with self.subTest(nombre=nombre):
                self.assertEqual(self.client.get(reverse(nombre)).status_code, 200)
        self.entrar(self.usuario_cliente)
        for nombre in rutas:
            self.assertEqual(self.client.get(reverse(nombre)).status_code, 403)
        self.entrar(self.ana)
        self.assertEqual(self.client.get(reverse('reportes')).status_code, 403)

    def test_alta_edicion_cliente_y_validacion(self):
        self.entrar(self.ana)
        url = reverse('cliente_nuevo')
        datos = {'nombre_completo': 'Daniel', 'telefono': '4181234567', 'correo': 'mal'}
        self.assertEqual(self.client.post(url, datos).status_code, 200)
        self.assertFalse(Cliente.objects.filter(nombre_completo='Daniel').exists())
        datos['correo'] = 'daniel@example.com'
        self.assertEqual(self.client.post(url, datos).status_code, 302)
        cliente = Cliente.objects.get(nombre_completo='Daniel')
        datos['nombre_completo'] = 'Daniel Moya'
        self.assertEqual(self.client.post(reverse('cliente_editar', args=[cliente.pk]), datos).status_code, 302)
        cliente.refresh_from_db()
        self.assertEqual(cliente.nombre_completo, 'Daniel Moya')

    def test_busqueda_combinada_y_fechas_invalidas(self):
        self.entrar(self.ana)
        url = reverse('buscar_ordenes')
        r = self.client.get(url, {'folio': self.orden.folio, 'cliente': 'María', 'serie': self.equipo.numero_serie, 'estado': 'recibido'})
        self.assertEqual(r.context['page_obj'].paginator.count, 1)
        self.assertEqual(self.client.get(url, {'estado': 'entregado'}).context['page_obj'].paginator.count, 0)
        r = self.client.get(url, {'fecha_inicio': '2026-12-31', 'fecha_fin': '2026-01-01'})
        self.assertTrue(r.context['form'].errors)
        self.assertEqual(r.context['page_obj'].paginator.count, 0)
        self.assertTrue(self.client.get(url, {'fecha_inicio': 'no-fecha'}).context['form'].errors)

    def test_tecnico_no_puede_leer_ni_modificar_orden_ajena(self):
        self.entrar(self.jorge)
        for ruta in ['tecnico_orden', 'generar_cotizacion']:
            url = reverse(ruta, args=[self.orden.folio])
            self.assertEqual(self.client.get(url).status_code, 404)
            self.assertEqual(self.client.post(url, {'nuevo_estado': Estado.DIAGNOSTICO}).status_code, 404)
        self.orden.refresh_from_db()
        self.assertEqual(self.orden.estado, Estado.RECIBIDO)

    def test_flujo_cotizacion_aprobacion_terminado(self):
        self.entrar(self.luis)
        detalle = reverse('tecnico_orden', args=[self.orden.folio])
        cotizar = reverse('generar_cotizacion', args=[self.orden.folio])
        self.assertEqual(self.client.get(detalle).status_code, 200)
        self.client.post(detalle, {'nuevo_estado': Estado.ENTREGADO})
        self.orden.refresh_from_db()
        self.assertEqual(self.orden.estado, Estado.RECIBIDO)
        self.client.post(detalle, {'nuevo_estado': Estado.DIAGNOSTICO})
        self.assertEqual(self.client.get(cotizar).status_code, 200)
        datos = {'diagnostico_tecnico': 'Puerto dañado', 'costo_refaccion': '350.10', 'costo_mano_obra': '250.20', 'cargo_diagnostico': '50.00'}
        r = self.client.post(cotizar, {**datos, 'costo_refaccion': '-1'})
        self.assertTrue(r.context['form'].errors)
        self.assertFalse(Cotizacion.objects.filter(orden=self.orden).exists())
        self.assertEqual(self.client.post(cotizar, datos).status_code, 302)
        self.orden.refresh_from_db()
        self.assertEqual(self.orden.estado, Estado.REVISION)
        self.assertEqual(self.orden.cotizacion.total, Decimal('600.30'))
        self.client.post(cotizar, datos)
        self.assertEqual(Cotizacion.objects.filter(orden=self.orden).count(), 1)
        self.client.post(detalle, {'nuevo_estado': Estado.TERMINADO, 'costo_final': '600.30'})
        self.orden.refresh_from_db()
        self.assertEqual(self.orden.estado, Estado.REVISION)
        # La pantalla de aprobación corresponde a otro integrante. Simulamos
        # su contrato mediante el método común, sin importar su implementación.
        self.orden.cambiar_estado(Estado.ARREGLANDO, self.usuario_cliente)
        cotizacion = self.orden.cotizacion
        cotizacion.aprobada = True
        cotizacion.fecha_respuesta = timezone.now()
        cotizacion.save()
        self.entrar(self.luis)
        r = self.client.post(detalle, {'nuevo_estado': Estado.TERMINADO})
        self.assertTrue(r.context['form'].errors)
        self.client.post(detalle, {'nuevo_estado': Estado.TERMINADO, 'costo_final': '600.30'})
        self.orden.refresh_from_db()
        self.assertEqual(self.orden.estado, Estado.TERMINADO)
        self.assertEqual(self.orden.costo_final, Decimal('600.30'))
        self.assertEqual(self.orden.historial.filter(estado_nuevo=Estado.REVISION).count(), 1)

    def test_dashboard_y_reportes_usan_datos_reales(self):
        self.entrar(self.roberto)
        r = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(r.context['en_curso'], 1)
        self.assertEqual(r.context['por_entregar'], 0)
        self.orden.estado = Estado.ENTREGADO
        self.orden.fecha_entrega = timezone.now()
        self.orden.costo_final = Decimal('600.30')
        self.orden.save()
        r = self.client.get(reverse('reportes'))
        self.assertEqual(r.context['total'], Decimal('600.30'))
        self.assertEqual(r.context['cantidad'], 1)
        self.assertEqual(r.context['graficas']['ordenes'], [1])
        self.assertEqual(self.client.get(reverse('admin_dashboard')).context['garantias'], 1)
        r = self.client.get(reverse('reportes'), {'fecha_fin': '2000-01-01'})
        self.assertEqual(r.context['cantidad'], 0)

    def test_reset_enlace_token_y_nueva_password(self):
        from django.core import mail
        import re
        self.ana.email = 'ana@example.com'
        self.ana.save()
        self.client.post(reverse('password_reset'), {'email': self.ana.email})
        self.assertEqual(len(mail.outbox), 1)
        link = re.search(r'http://testserver(/\S+)', mail.outbox[0].body).group(1)
        r = self.client.get(link)
        self.assertEqual(r.status_code, 302)
        formulario = r.url
        self.assertEqual(self.client.get(formulario).status_code, 200)
        r = self.client.post(formulario, {'new_password1': 'ClaveSegura!2030', 'new_password2': 'ClaveSegura!2030'})
        self.assertRedirects(r, reverse('password_reset_complete'))
        self.ana.refresh_from_db()
        self.assertTrue(self.ana.check_password('ClaveSegura!2030'))
        self.assertContains(self.client.get(link), 'no es válido')

    def test_evidencia_requiere_dueno_o_personal_autorizado(self):
        import tempfile
        from io import BytesIO
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile
        from .models import EvidenciaFoto
        with tempfile.TemporaryDirectory() as folder, override_settings(MEDIA_ROOT=folder):
            b = BytesIO()
            Image.new('RGB', (2, 2)).save(b, format='PNG')
            foto = EvidenciaFoto.objects.create(orden=self.orden, imagen=SimpleUploadedFile('foto.png', b.getvalue(), content_type='image/png'))
            url = reverse('evidencia', args=[foto.pk])
            self.assertEqual(self.client.get(url).status_code, 302)
            self.entrar(self.jorge)
            self.assertEqual(self.client.get(url).status_code, 404)
            self.entrar(self.usuario_cliente)
            r = self.client.get(url)
            self.assertEqual(r.status_code, 200)
            r.close()
            self.assertEqual(self.client.get(foto.imagen.url).status_code, 404)
