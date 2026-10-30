"""Pruebas del flujo de estados y de los permisos por rol.

Son las dos reglas que sostienen el sistema: que una orden no se pueda saltar
pasos y que cada rol solo vea y haga lo que le corresponde.
"""

from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (
    ROL_ADMINISTRADOR,
    ROL_CLIENTE,
    ROL_RECEPCIONISTA,
    ROL_TECNICO,
    ROLES,
    Cliente,
    Cotizacion,
    Equipo,
    Estado,
    HistorialEstado,
    OrdenServicio,
    TransicionInvalida,
)

PASSWORD = "prueba1234"


class BaseTecnoFix(TestCase):
    """Datos mínimos que comparten todas las pruebas."""

    def setUp(self):
        self.grupos = {rol: Group.objects.get_or_create(name=rol)[0] for rol in ROLES}

        self.ana = self._usuario("ana", ROL_RECEPCIONISTA)
        self.luis = self._usuario("luis", ROL_TECNICO)
        self.jorge = self._usuario("jorge", ROL_TECNICO)
        self.roberto = self._usuario("roberto", ROL_ADMINISTRADOR)
        self.usuario_cliente = self._usuario("maria", ROL_CLIENTE)

        self.cliente = Cliente.objects.create(
            nombre_completo="María Fernanda Ruiz Soto",
            telefono="418 555 0142",
            usuario=self.usuario_cliente,
        )
        self.equipo = Equipo.objects.create(
            cliente=self.cliente,
            tipo=Equipo.Tipo.CELULAR,
            marca="Samsung",
            modelo="Galaxy A54",
            numero_serie="356938110123456",
        )
        self.orden = OrdenServicio.objects.create(
            equipo=self.equipo,
            tecnico=self.luis,
            recibida_por=self.ana,
            falla_reportada="La pantalla se ve con rayas verdes.",
        )

    def _usuario(self, username, rol):
        usuario = User.objects.create_user(username=username, password=PASSWORD)
        usuario.groups.add(self.grupos[rol])
        return usuario

    def _hasta_revision(self):
        """Lleva la orden hasta En revisión, con su cotización."""
        self.orden.cambiar_estado(Estado.DIAGNOSTICO, self.luis)
        Cotizacion.objects.create(
            orden=self.orden,
            costo_refaccion=Decimal("1400.00"),
            costo_mano_obra=Decimal("450.00"),
        )
        self.orden.cambiar_estado(Estado.REVISION, self.luis)


class FlujoDeEstadosTests(BaseTecnoFix):
    """El flujo no se puede saltar ni recorrer al revés."""

    def test_la_orden_nace_en_recibido(self):
        self.assertEqual(self.orden.estado, Estado.RECIBIDO)

    def test_el_folio_se_asigna_solo_y_es_consecutivo(self):
        otra = OrdenServicio.objects.create(
            equipo=self.equipo, tecnico=self.luis, falla_reportada="Otra falla."
        )
        self.assertEqual(self.orden.folio, "1001")
        self.assertEqual(otra.folio, "1002")

    def test_recorrido_completo_hasta_entregado(self):
        self._hasta_revision()
        self.orden.cambiar_estado(Estado.ARREGLANDO, self.usuario_cliente)
        self.orden.cambiar_estado(Estado.TERMINADO, self.luis)
        self.orden.cambiar_estado(Estado.ENTREGADO, self.ana)

        self.orden.refresh_from_db()
        self.assertEqual(self.orden.estado, Estado.ENTREGADO)
        self.assertIsNotNone(self.orden.fecha_entrega)

    def test_no_se_puede_saltar_pasos(self):
        # De Recibido no se puede ir directo a Entregado.
        with self.assertRaises(TransicionInvalida):
            self.orden.cambiar_estado(Estado.ENTREGADO, self.ana)
        self.orden.refresh_from_db()
        self.assertEqual(self.orden.estado, Estado.RECIBIDO)

    def test_no_se_puede_retroceder(self):
        self.orden.cambiar_estado(Estado.DIAGNOSTICO, self.luis)
        with self.assertRaises(TransicionInvalida):
            self.orden.cambiar_estado(Estado.RECIBIDO, self.luis)

    def test_una_orden_rechazada_ya_no_avanza(self):
        self._hasta_revision()
        self.orden.cambiar_estado(Estado.RECHAZADO, self.usuario_cliente)
        with self.assertRaises(TransicionInvalida):
            self.orden.cambiar_estado(Estado.ARREGLANDO, self.usuario_cliente)

    def test_una_orden_entregada_ya_no_avanza(self):
        self._hasta_revision()
        self.orden.cambiar_estado(Estado.ARREGLANDO, self.usuario_cliente)
        self.orden.cambiar_estado(Estado.TERMINADO, self.luis)
        self.orden.cambiar_estado(Estado.ENTREGADO, self.ana)
        with self.assertRaises(TransicionInvalida):
            self.orden.cambiar_estado(Estado.TERMINADO, self.luis)


class RolDeCadaTransicionTests(BaseTecnoFix):
    """Cada paso del flujo lo mueve el rol que le corresponde."""

    def test_el_cliente_no_inicia_el_diagnostico(self):
        with self.assertRaises(TransicionInvalida):
            self.orden.cambiar_estado(Estado.DIAGNOSTICO, self.usuario_cliente)

    def test_el_tecnico_no_aprueba_la_cotizacion_por_el_cliente(self):
        self._hasta_revision()
        with self.assertRaises(TransicionInvalida):
            self.orden.cambiar_estado(Estado.ARREGLANDO, self.luis)

    def test_el_tecnico_no_entrega_el_equipo(self):
        self._hasta_revision()
        self.orden.cambiar_estado(Estado.ARREGLANDO, self.usuario_cliente)
        self.orden.cambiar_estado(Estado.TERMINADO, self.luis)
        with self.assertRaises(TransicionInvalida):
            self.orden.cambiar_estado(Estado.ENTREGADO, self.luis)

    def test_la_recepcionista_no_hace_el_diagnostico(self):
        with self.assertRaises(TransicionInvalida):
            self.orden.cambiar_estado(Estado.DIAGNOSTICO, self.ana)

    def test_el_administrador_puede_hacer_cualquier_cambio(self):
        # Roberto tiene acceso completo al sistema.
        self.orden.cambiar_estado(Estado.DIAGNOSTICO, self.roberto)
        self.assertEqual(self.orden.estado, Estado.DIAGNOSTICO)


class BitacoraTests(BaseTecnoFix):
    """Cada cambio de estado queda registrado con su autor."""

    def test_cada_cambio_deja_un_registro(self):
        self.orden.cambiar_estado(Estado.DIAGNOSTICO, self.luis, "Inicia el diagnóstico")

        registro = HistorialEstado.objects.get(orden=self.orden)
        self.assertEqual(registro.estado_anterior, Estado.RECIBIDO)
        self.assertEqual(registro.estado_nuevo, Estado.DIAGNOSTICO)
        self.assertEqual(registro.usuario, self.luis)
        self.assertEqual(registro.comentario, "Inicia el diagnóstico")

    def test_una_transicion_invalida_no_deja_registro(self):
        with self.assertRaises(TransicionInvalida):
            self.orden.cambiar_estado(Estado.ENTREGADO, self.ana)
        self.assertEqual(HistorialEstado.objects.count(), 0)

    def test_la_bitacora_guarda_quien_aprobo_la_cotizacion(self):
        self._hasta_revision()
        self.orden.cambiar_estado(
            Estado.ARREGLANDO, self.usuario_cliente, "El cliente aprobó la cotización"
        )
        registro = HistorialEstado.objects.filter(
            estado_nuevo=Estado.ARREGLANDO
        ).first()
        self.assertEqual(registro.usuario, self.usuario_cliente)


class PermisosDeVistasTests(BaseTecnoFix):
    """Cada rol entra solo a las pantallas que le tocan."""

    def test_sin_sesion_redirige_al_login(self):
        respuesta = self.client.get(reverse("nueva_orden"))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse("login"), respuesta.url)

    def test_el_cliente_no_entra_a_recepcion(self):
        self.client.login(username="maria", password=PASSWORD)
        respuesta = self.client.get(reverse("nueva_orden"))
        self.assertEqual(respuesta.status_code, 403)

    def test_el_tecnico_no_entra_a_la_bitacora(self):
        self.client.login(username="luis", password=PASSWORD)
        respuesta = self.client.get(reverse("admin_auditoria"))
        self.assertEqual(respuesta.status_code, 403)

    def test_el_tecnico_no_entra_a_recepcion(self):
        self.client.login(username="luis", password=PASSWORD)
        respuesta = self.client.get(reverse("nueva_orden"))
        self.assertEqual(respuesta.status_code, 403)

    def test_el_cliente_no_entra_al_panel_del_tecnico(self):
        self.client.login(username="maria", password=PASSWORD)
        respuesta = self.client.get(reverse("tecnico_panel"))
        self.assertEqual(respuesta.status_code, 403)

    def test_la_recepcionista_no_entra_a_la_bitacora(self):
        self.client.login(username="ana", password=PASSWORD)
        respuesta = self.client.get(reverse("admin_auditoria"))
        self.assertEqual(respuesta.status_code, 403)

    def test_la_recepcionista_si_entra_a_nueva_orden(self):
        self.client.login(username="ana", password=PASSWORD)
        respuesta = self.client.get(reverse("nueva_orden"))
        self.assertEqual(respuesta.status_code, 200)

    def test_cada_rol_llega_a_su_pantalla_de_inicio(self):
        casos = [
            ("ana", reverse("nueva_orden")),
            ("luis", reverse("tecnico_panel")),
            ("maria", reverse("mis_ordenes")),
            ("roberto", reverse("admin_auditoria")),
        ]
        for username, destino in casos:
            with self.subTest(usuario=username):
                self.client.login(username=username, password=PASSWORD)
                respuesta = self.client.get(reverse("inicio"))
                self.assertRedirects(respuesta, destino)
                self.client.logout()


class AislamientoDeDatosTests(BaseTecnoFix):
    """Un usuario solo ve lo suyo."""

    def setUp(self):
        super().setUp()
        # Una orden de otro cliente, atendida por el otro técnico.
        otro_usuario = self._usuario("joseluis", ROL_CLIENTE)
        otro_cliente = Cliente.objects.create(
            nombre_completo="José Luis Pérez Ramírez",
            telefono="418 555 0177",
            usuario=otro_usuario,
        )
        otro_equipo = Equipo.objects.create(
            cliente=otro_cliente,
            tipo=Equipo.Tipo.LAPTOP,
            marca="HP",
            modelo="Pavilion 15",
        )
        self.orden_ajena = OrdenServicio.objects.create(
            equipo=otro_equipo,
            tecnico=self.jorge,
            falla_reportada="Se calienta mucho.",
        )

    def test_el_cliente_solo_ve_sus_ordenes(self):
        self.client.login(username="maria", password=PASSWORD)
        respuesta = self.client.get(reverse("mis_ordenes"))
        ordenes = respuesta.context["ordenes"]
        self.assertIn(self.orden, ordenes)
        self.assertNotIn(self.orden_ajena, ordenes)

    def test_el_cliente_no_abre_la_orden_de_otro(self):
        self.client.login(username="maria", password=PASSWORD)
        respuesta = self.client.get(
            reverse("cliente_orden", args=[self.orden_ajena.folio])
        )
        self.assertRedirects(respuesta, reverse("mis_ordenes"))

    def test_el_tecnico_solo_ve_sus_ordenes_asignadas(self):
        self.client.login(username="luis", password=PASSWORD)
        respuesta = self.client.get(reverse("tecnico_panel"))
        ordenes = respuesta.context["ordenes"]
        self.assertIn(self.orden, ordenes)
        self.assertNotIn(self.orden_ajena, ordenes)


def _datos_nueva_orden(**extra):
    datos = {
        "nuevo_nombre": "Carlos Mendoza Rojas",
        "nuevo_telefono": "418 555 0190",
        "nuevo_correo": "carlos@example.com",
        "tipo": "laptop",
        "marca": "Lenovo",
        "modelo": "IdeaPad 3",
        "numero_serie": "PF3K9921",
        "falla_reportada": "No enciende, ya probé otro cargador.",
        "prioridad": "normal",
    }
    datos.update(extra)
    return datos


class RecepcionTests(BaseTecnoFix):
    """Nueva orden, equipo y ticket."""

    def setUp(self):
        super().setUp()
        self.client.login(username="ana", password=PASSWORD)

    def test_nueva_orden_con_cliente_nuevo(self):
        respuesta = self.client.post(
            reverse("nueva_orden"), _datos_nueva_orden(tecnico=self.jorge.pk)
        )
        orden = OrdenServicio.objects.get(equipo__numero_serie="PF3K9921")
        self.assertRedirects(respuesta, reverse("ticket", args=[orden.folio]))
        self.assertEqual(orden.estado, Estado.RECIBIDO)
        self.assertEqual(orden.tecnico, self.jorge)
        self.assertEqual(orden.recibida_por, self.ana)
        self.assertEqual(orden.equipo.cliente.nombre_completo, "Carlos Mendoza Rojas")
        self.assertIsNotNone(orden.fecha_entrega_estimada)

    def test_nueva_orden_deja_el_primer_registro_en_la_bitacora(self):
        self.client.post(
            reverse("nueva_orden"), _datos_nueva_orden(tecnico=self.jorge.pk)
        )
        orden = OrdenServicio.objects.get(equipo__numero_serie="PF3K9921")
        registro = HistorialEstado.objects.get(orden=orden)
        self.assertEqual(registro.estado_nuevo, Estado.RECIBIDO)
        self.assertEqual(registro.usuario, self.ana)

    def test_nueva_orden_con_cliente_existente_no_duplica_al_cliente(self):
        datos = _datos_nueva_orden(
            tecnico=self.luis.pk, cliente_existente=self.cliente.pk
        )
        for campo in ("nuevo_nombre", "nuevo_telefono", "nuevo_correo"):
            datos.pop(campo)
        self.client.post(reverse("nueva_orden"), datos)
        self.assertEqual(Cliente.objects.count(), 1)
        self.assertEqual(self.cliente.equipos.count(), 2)

    def test_la_urgente_se_entrega_antes_que_la_normal(self):
        self.client.post(
            reverse("nueva_orden"),
            _datos_nueva_orden(tecnico=self.luis.pk, prioridad="urgente"),
        )
        urgente = OrdenServicio.objects.get(equipo__numero_serie="PF3K9921")
        recepcion = timezone.localtime(urgente.fecha_recepcion).date()
        self.assertEqual((urgente.fecha_entrega_estimada - recepcion).days, 3)

    def test_sin_cliente_ni_datos_nuevos_no_crea_la_orden(self):
        datos = _datos_nueva_orden(tecnico=self.luis.pk)
        for campo in ("nuevo_nombre", "nuevo_telefono", "nuevo_correo"):
            datos.pop(campo)
        respuesta = self.client.post(reverse("nueva_orden"), datos)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(OrdenServicio.objects.count(), 1)

    def test_cliente_nuevo_sin_telefono_es_invalido(self):
        respuesta = self.client.post(
            reverse("nueva_orden"),
            _datos_nueva_orden(tecnico=self.luis.pk, nuevo_telefono=""),
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(OrdenServicio.objects.count(), 1)

    def test_el_ticket_muestra_los_datos_de_la_orden(self):
        respuesta = self.client.get(reverse("ticket", args=[self.orden.folio]))
        self.assertContains(respuesta, self.orden.folio)
        self.assertContains(respuesta, "María Fernanda Ruiz Soto")
        self.assertContains(respuesta, "Galaxy A54")

    def test_el_ticket_muestra_el_costo_final_cuando_ya_existe(self):
        self.orden.costo_final = Decimal("1850.00")
        self.orden.save()
        respuesta = self.client.get(reverse("ticket", args=[self.orden.folio]))
        self.assertContains(respuesta, "1,850.00")

    def test_el_ticket_de_un_folio_inexistente_da_404(self):
        respuesta = self.client.get(reverse("ticket", args=["9999"]))
        self.assertEqual(respuesta.status_code, 404)

    def test_alta_de_equipo(self):
        respuesta = self.client.post(
            reverse("equipo_nuevo"),
            {
                "cliente": self.cliente.pk,
                "tipo": "tablet",
                "marca": "Apple",
                "modelo": "iPad 9",
                "numero_serie": "DMPXYZ",
                "color": "Gris",
            },
        )
        equipo = Equipo.objects.get(numero_serie="DMPXYZ")
        self.assertRedirects(respuesta, reverse("equipo_editar", args=[equipo.pk]))

    def test_editar_equipo_y_ver_su_historial(self):
        respuesta = self.client.get(reverse("equipo_editar", args=[self.equipo.pk]))
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn(self.orden, respuesta.context["historial"])

        self.client.post(
            reverse("equipo_editar", args=[self.equipo.pk]),
            {
                "cliente": self.cliente.pk,
                "tipo": "celular",
                "marca": "Samsung",
                "modelo": "Galaxy A54 5G",
                "numero_serie": self.equipo.numero_serie,
                "color": "Negro",
            },
        )
        self.equipo.refresh_from_db()
        self.assertEqual(self.equipo.modelo, "Galaxy A54 5G")


class SeguimientoDelClienteTests(BaseTecnoFix):
    """Pantallas del cliente: lista y detalle con barra de seguimiento."""

    def setUp(self):
        super().setUp()
        self.client.login(username="maria", password=PASSWORD)

    def test_el_detalle_marca_el_paso_actual(self):
        self.orden.cambiar_estado(Estado.DIAGNOSTICO, self.luis)
        respuesta = self.client.get(reverse("cliente_orden", args=[self.orden.folio]))
        pasos = respuesta.context["seguimiento"]
        self.assertEqual(len(pasos), 6)
        self.assertEqual([p["completado"] for p in pasos], [True, True, False, False, False, False])
        self.assertEqual([p["etiqueta"] for p in pasos if p["actual"]], ["En diagnóstico"])

    def test_una_orden_rechazada_muestra_cuatro_pasos(self):
        self._hasta_revision()
        self.orden.cambiar_estado(Estado.RECHAZADO, self.usuario_cliente)
        respuesta = self.client.get(reverse("cliente_orden", args=[self.orden.folio]))
        pasos = respuesta.context["seguimiento"]
        self.assertEqual(len(pasos), 4)
        self.assertEqual(pasos[-1]["etiqueta"], "Rechazado")

    def test_un_usuario_cliente_sin_ficha_ve_la_lista_vacia(self):
        sin_ficha = self._usuario("nuevo", ROL_CLIENTE)
        self.client.login(username="nuevo", password=PASSWORD)
        respuesta = self.client.get(reverse("mis_ordenes"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.context["ordenes"]), 0)


class BitacoraDeAuditoriaTests(BaseTecnoFix):
    """La pantalla de auditoría muestra quién hizo cada cambio."""

    def test_muestra_cada_cambio_con_su_autor_y_rol(self):
        self._hasta_revision()
        self.orden.cambiar_estado(Estado.ARREGLANDO, self.usuario_cliente)
        self.client.login(username="roberto", password=PASSWORD)

        respuesta = self.client.get(reverse("admin_auditoria"))

        filas = respuesta.context["filas"]
        self.assertEqual(len(filas), 3)
        # El más reciente va primero.
        self.assertEqual(filas[0]["registro"].estado_nuevo, Estado.ARREGLANDO)
        self.assertEqual(filas[0]["rol"], "Cliente")
        self.assertEqual(filas[-1]["rol"], "Técnico")

    def test_sin_cambios_la_pantalla_carga_vacia(self):
        self.client.login(username="roberto", password=PASSWORD)
        respuesta = self.client.get(reverse("admin_auditoria"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.context["filas"]), 0)


class LoginTests(BaseTecnoFix):
    """Inicio de sesión y bloqueo temporal."""

    def setUp(self):
        super().setUp()
        from django.core.cache import cache

        cache.clear()

    def _intentar(self, username, password):
        return self.client.post(
            reverse("login"), {"username": username, "password": password}
        )

    def test_login_correcto_lleva_a_la_pantalla_del_rol(self):
        respuesta = self._intentar("ana", PASSWORD)
        self.assertRedirects(
            respuesta, reverse("inicio"), fetch_redirect_response=False
        )

    def test_contrasena_incorrecta_muestra_el_error(self):
        respuesta = self._intentar("ana", "mal")
        self.assertContains(respuesta, "no son correctos")

    def test_cinco_fallos_bloquean_la_cuenta(self):
        from .views import MAX_INTENTOS

        for _ in range(MAX_INTENTOS):
            self._intentar("ana", "mal")
        # Ya bloqueada: ni con la contraseña buena deja entrar.
        respuesta = self._intentar("ana", PASSWORD)
        self.assertContains(respuesta, "bloqueada")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_cuatro_fallos_todavia_no_bloquean(self):
        for _ in range(4):
            self._intentar("ana", "mal")
        respuesta = self._intentar("ana", PASSWORD)
        self.assertEqual(respuesta.status_code, 302)

    def test_un_acceso_correcto_reinicia_el_conteo(self):
        for _ in range(4):
            self._intentar("ana", "mal")
        self._intentar("ana", PASSWORD)
        self.client.logout()
        for _ in range(4):
            self._intentar("ana", "mal")
        respuesta = self._intentar("ana", PASSWORD)
        self.assertEqual(respuesta.status_code, 302)

    def test_el_bloqueo_es_por_usuario(self):
        for _ in range(5):
            self._intentar("ana", "mal")
        respuesta = self._intentar("luis", PASSWORD)
        self.assertEqual(respuesta.status_code, 302)

    def test_cerrar_sesion(self):
        self.client.login(username="ana", password=PASSWORD)
        self.client.post(reverse("logout"))
        respuesta = self.client.get(reverse("nueva_orden"))
        self.assertEqual(respuesta.status_code, 302)
