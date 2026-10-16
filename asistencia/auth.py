"""
Autenticación por JWT. Reemplaza a las sesiones (cookies) porque el frontend
vive en otro dominio.

- Administrador: usuario de Django con is_staff. Token con "user_id".
- Estudiante: no es usuario de Django. Token con "estudiante_id".
"""
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import AccessToken

from .models import Estudiante


class EstudianteAutenticado:
    """Lo que queda en request.user cuando entra un estudiante."""

    is_authenticated = True
    is_staff = False

    def __init__(self, estudiante):
        self.estudiante = estudiante


def token_admin(user):
    token = AccessToken.for_user(user)
    token["rol"] = "admin"
    return str(token)


def token_estudiante(estudiante):
    token = AccessToken()
    token["rol"] = "estudiante"
    token["estudiante_id"] = estudiante.pk
    return str(token)


class JWTEstudianteOAdmin(JWTAuthentication):
    def get_user(self, validated_token):
        eid = validated_token.get("estudiante_id")
        if eid is None:
            return super().get_user(validated_token)
        est = Estudiante.objects.select_related("modulo").filter(pk=eid, modulo__activo=True).first()
        if est is None:  # el módulo cambió: el token ya no es válido
            raise AuthenticationFailed("Tu sesión ya no es válida. Ingresa nuevamente.")
        return EstudianteAutenticado(est)


class EsEstudiante(BasePermission):
    message = "Debes ingresar como estudiante."

    def has_permission(self, request, view):
        return isinstance(request.user, EstudianteAutenticado)


class EsAdmin(BasePermission):
    """RF-02: funciones administrativas restringidas al rol administrador."""

    message = "Necesitas ingresar como administrador."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)
