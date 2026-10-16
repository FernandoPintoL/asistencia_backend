from django.urls import path
from . import views

# Todas estas rutas cuelgan de /api/ (ver config/urls.py)
urlpatterns = [
    path("modulo-activo/", views.modulo_activo, name="modulo_activo"),
    # Estudiante
    path("estudiante/login/", views.login_estudiante, name="login_estudiante"),
    path("estudiante/mi-asistencia/", views.mi_asistencia, name="mi_asistencia"),
    path("estudiante/marcar/", views.marcar, name="marcar"),
    # Administrador
    path("panel/login/", views.login_admin, name="login_admin"),
    path("panel/resumen/", views.dashboard, name="dashboard"),
    path("panel/estudiantes/", views.estudiantes, name="estudiantes"),
    path("panel/asistencias/", views.asistencias, name="asistencias"),
    path("panel/asistencias/modificar/", views.modificar, name="modificar"),
    path("panel/actividades/", views.actividades, name="actividades"),
    path("panel/modulos/", views.modulos, name="modulos"),
    path("panel/modulos/<int:pk>/habilitar/", views.modulo_habilitar, name="modulo_habilitar"),
    path("panel/modulos/<int:pk>/deshabilitar/", views.modulo_deshabilitar, name="modulo_deshabilitar"),
    path("panel/modulos/<int:pk>/eliminar/", views.modulo_eliminar, name="modulo_eliminar"),
    path("panel/modulos/importar/validar/", views.modulo_validar, name="modulo_validar"),
    path("panel/modulos/importar/confirmar/", views.modulo_confirmar, name="modulo_confirmar"),
    path("panel/exportar/", views.exportar, name="exportar"),
]
