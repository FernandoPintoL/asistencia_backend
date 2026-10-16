from datetime import timedelta
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from openpyxl import Workbook
from rest_framework.test import APIClient

from .importers import parse_estudiantes, parse_fechas
from .models import Actividad, Asistencia, Estudiante, Modulo
from .services import activar_modulo, marcar_asistencia, modificar_asistencia


def _xlsx(cabecera, filas):
    wb = Workbook()
    wb.active.append(cabecera)
    for f in filas:
        wb.active.append(f)
    b = BytesIO()
    wb.save(b)
    b.seek(0)
    return b


class BaseConDatos(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = get_user_model().objects.create_user("admin", password="x", is_staff=True)
        hoy = timezone.localdate()
        self.modulo = activar_modulo(
            self.admin, "M1",
            [{"nro_registro": "1001", "nombre": "Juan", "correo": "juan@gmail.com"}],
            [{"fecha": (hoy - timedelta(days=2)).isoformat(), "inicio": "18:00", "fin": "21:00"},
             {"fecha": hoy.isoformat(), "inicio": "18:00", "fin": "21:00"},
             {"fecha": (hoy + timedelta(days=2)).isoformat(), "inicio": "18:00", "fin": "21:00"}],
        )
        self.est = Estudiante.objects.get(nro_registro="1001")

    def _entrar(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def _admin(self):
        r = self.client.post(reverse("login_admin"), {"username": "admin", "password": "x"}, format="json")
        self._entrar(r.json()["token"])

    def _estudiante(self, dato="1001"):
        r = self.client.post(reverse("login_estudiante"), {"identificador": dato}, format="json")
        self._entrar(r.json()["token"])


class AsistenciaTests(BaseConDatos):
    def test_marca_una_sola_vez(self):
        ok, _ = marcar_asistencia(self.est)
        ok2, _ = marcar_asistencia(self.est)
        self.assertTrue(ok)
        self.assertFalse(ok2)
        self.assertEqual(Asistencia.objects.count(), 1)

    def test_no_marca_sin_clase_hoy(self):
        self.modulo.fechas.filter(fecha=timezone.localdate()).delete()
        ok, _ = marcar_asistencia(self.est)
        self.assertFalse(ok)

    def test_admin_corrige_falta_pasada_con_auditoria(self):
        pasada = self.modulo.fechas.first()
        ok, _ = modificar_asistencia(self.admin, self.est, pasada, "PRESENTE")
        self.assertTrue(ok)
        log = Actividad.objects.filter(accion="Modificó asistencia").first()
        self.assertEqual((log.valor_anterior, log.valor_nuevo), ("Falta", "Presente"))

    def test_nuevo_modulo_conserva_el_anterior(self):
        activar_modulo(self.admin, "M2", [{"nro_registro": "1", "nombre": "A", "correo": "a@a.com"}],
                       [{"fecha": timezone.localdate().isoformat(), "inicio": "18:00", "fin": "21:00"}])
        self.assertEqual(Modulo.objects.filter(activo=True).count(), 1)
        self.assertTrue(Estudiante.objects.filter(modulo=self.modulo).exists())

    def test_login_estudiante_por_correo_y_registro(self):
        for dato in ("juan@gmail.com", "1001"):
            r = self.client.post(reverse("login_estudiante"), {"identificador": dato}, format="json")
            self.assertEqual(r.status_code, 200)
            self.assertIn("token", r.json())
        r = self.client.post(reverse("login_estudiante"), {"identificador": "9999"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_estudiante_no_accede_al_panel(self):
        self._estudiante()
        self.assertEqual(self.client.get(reverse("actividades")).status_code, 403)

    def test_sin_token_no_hay_acceso(self):
        self.assertEqual(self.client.get(reverse("mi_asistencia")).status_code, 401)
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 401)

    def test_estudiante_marca_por_api(self):
        self._estudiante()
        self.assertTrue(self.client.get(reverse("mi_asistencia")).json()["puede_marcar"])
        self.assertEqual(self.client.post(reverse("marcar")).status_code, 200)
        self.assertEqual(self.client.post(reverse("marcar")).status_code, 400)
        datos = self.client.get(reverse("mi_asistencia")).json()
        self.assertFalse(datos["puede_marcar"])
        self.assertEqual(datos["presentes"], 1)

    def test_token_de_estudiante_caduca_al_cambiar_modulo(self):
        self._estudiante()
        activar_modulo(self.admin, "M2", [{"nro_registro": "1", "nombre": "A", "correo": "a@a.com"}],
                       [{"fecha": timezone.localdate().isoformat(), "inicio": "18:00", "fin": "21:00"}])
        self.assertEqual(self.client.get(reverse("mi_asistencia")).status_code, 401)

    def test_admin_modifica_por_api(self):
        self._admin()
        pasada = self.modulo.fechas.first()
        r = self.client.post(reverse("modificar"), {"estudiante": self.est.id, "fecha": pasada.id,
                                                    "estado": "PRESENTE"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(Asistencia.objects.filter(estudiante=self.est, fecha_clase=pasada,
                                                  modificado_por_admin=True).exists())

    def test_importador_reporta_errores(self):
        f = _xlsx(["a", "b", "c"], [[1001, "Ana", "ana@x.com"], [1001, "Beto", "malo"], [1003, "", "c@x.com"]])
        datos, errores = parse_estudiantes(f)
        self.assertEqual(len(datos), 1)
        self.assertEqual(len(errores), 2)

    def test_importador_fechas(self):
        f = _xlsx(["Fecha", "i", "f"], [["05/10/2026", "18:00", "21:00"], ["xx", "18:00", "21:00"]])
        datos, errores = parse_fechas(f)
        self.assertEqual(datos[0]["fecha"], "2026-10-05")
        self.assertEqual(len(errores), 1)


class ModulosTests(BaseConDatos):
    def test_habilitar_otro_modulo_deja_uno_solo_activo(self):
        m2 = activar_modulo(self.admin, "M2", [{"nro_registro": "1", "nombre": "A", "correo": "a@a.com"}],
                            [{"fecha": timezone.localdate().isoformat(), "inicio": "18:00", "fin": "21:00"}])
        self._admin()
        self.client.post(reverse("modulo_habilitar", args=[self.modulo.id]))
        self.assertEqual(list(Modulo.objects.filter(activo=True)), [self.modulo])
        m2.refresh_from_db()
        self.assertFalse(m2.activo)

    def test_deshabilitar_deja_sin_modulo_activo_y_sin_borrar(self):
        self._admin()
        self.client.post(reverse("modulo_deshabilitar", args=[self.modulo.id]))
        self.assertEqual(Modulo.objects.filter(activo=True).count(), 0)
        self.assertTrue(Estudiante.objects.filter(modulo=self.modulo).exists())
        self.client.credentials()
        r = self.client.post(reverse("login_estudiante"), {"identificador": "1001"}, format="json")
        self.assertEqual(r.status_code, 400)  # no puede ingresar

    def test_pantalla_modulos_y_paneles_sin_modulo(self):
        self._admin()
        self.client.post(reverse("modulo_deshabilitar", args=[self.modulo.id]))
        self.assertEqual(self.client.get(reverse("modulos")).status_code, 200)
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 200)
        self.assertEqual(self.client.get(reverse("asistencias")).status_code, 409)

    def test_estudiante_no_puede_cambiar_modulos(self):
        self._estudiante()
        r = self.client.post(reverse("modulo_deshabilitar", args=[self.modulo.id]))
        self.assertEqual(r.status_code, 403)
        self.assertTrue(Modulo.objects.get(pk=self.modulo.pk).activo)

    def _archivos(self):
        hoy = timezone.localdate()
        tipo = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        est = _xlsx(["Registro", "Nombre", "Correo"], [[2001, "Ana", "ana@x.com"], [2002, "Beto", "beto@x.com"]])
        fec = _xlsx(["Fecha", "Inicio", "Fin"], [[hoy.strftime("%d/%m/%Y"), "18:00", "21:00"]])
        return {"nombre": "M2",
                "estudiantes": SimpleUploadedFile("e.xlsx", est.read(), content_type=tipo),
                "fechas": SimpleUploadedFile("f.xlsx", fec.read(), content_type=tipo)}

    def test_importar_valida_sin_guardar_y_confirma(self):
        self._admin()
        r = self.client.post(reverse("modulo_validar"), self._archivos(), format="multipart")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["estudiantes"]), 2)
        self.assertFalse(Modulo.objects.filter(nombre="M2").exists())
        r = self.client.post(reverse("modulo_confirmar"), self._archivos(), format="multipart")
        self.assertEqual(r.status_code, 201)
        self.assertTrue(Modulo.objects.filter(nombre="M2", activo=True).exists())

    def test_importar_sin_archivos_devuelve_errores(self):
        self._admin()
        r = self.client.post(reverse("modulo_validar"), {"nombre": ""}, format="multipart")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(len(r.json()["errores"]), 3)

    def test_exportar_excel(self):
        self._admin()
        r = self.client.get(reverse("exportar"))
        self.assertEqual(r.status_code, 200)
        self.assertIn("attachment", r["Content-Disposition"])


class EliminarModuloTests(BaseConDatos):
    def setUp(self):
        super().setUp()
        self.m2 = activar_modulo(self.admin, "M2", [{"nro_registro": "1", "nombre": "A", "correo": "a@a.com"}],
                                 [{"fecha": timezone.localdate().isoformat(), "inicio": "18:00", "fin": "21:00"}])
        self._admin()

    def test_no_elimina_modulo_activo(self):
        self.client.post(reverse("modulo_eliminar", args=[self.m2.id]), {"confirmacion": "M2"}, format="json")
        self.assertTrue(Modulo.objects.filter(pk=self.m2.pk).exists())

    def test_no_elimina_con_nombre_incorrecto(self):
        self.client.post(reverse("modulo_eliminar", args=[self.modulo.id]), {"confirmacion": "otro"}, format="json")
        self.assertTrue(Modulo.objects.filter(pk=self.modulo.pk).exists())

    def test_elimina_inactivo_con_nombre_correcto_y_en_cascada(self):
        self.client.post(reverse("modulo_eliminar", args=[self.modulo.id]), {"confirmacion": "M1"}, format="json")
        self.assertFalse(Modulo.objects.filter(pk=self.modulo.pk).exists())
        self.assertFalse(Estudiante.objects.filter(nro_registro="1001").exists())
        self.assertTrue(Modulo.objects.filter(pk=self.m2.pk, activo=True).exists())
        self.assertTrue(Actividad.objects.filter(accion="Eliminó módulo").exists())
