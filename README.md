# Backend · API de control de asistencia

Django + Django REST Framework + PostgreSQL. Expone una API JSON en `/api/...` que consume el
[frontend](../frontend/README.md). Autenticación con tokens JWT.

## Puesta en marcha

Necesitas Python y PostgreSQL con una base de datos vacía `asistencia_db`.

```powershell
# desde la raíz del proyecto
python -m venv venv
venv\Scripts\activate
cd backend
pip install -r requirements.txt
copy .env.example .env          # edita .env y pon tu contraseña de PostgreSQL
python manage.py migrate
python manage.py crear_demo     # admin / admin1234 + módulo de demostración
python manage.py runserver      # http://127.0.0.1:8000
```

- Admin técnico de Django: http://127.0.0.1:8000/django-admin/
- Pruebas automáticas: `python manage.py test`
- Excel de ejemplo: `python manage.py generar_ejemplos` los crea en `ejemplos/` (la primera fecha de clase es **hoy**).

## Variables de entorno (`.env`)
| Variable | Para qué |
|---|---|
| `SECRET_KEY` | Firma de los tokens. En producción, una nueva y secreta |
| `DEBUG` | `True` en local, `False` en producción |
| `ALLOWED_HOSTS` | Dominio del backend, ej. `mi-api.onrender.com` |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | Conexión a PostgreSQL |
| `CORS_ALLOWED_ORIGINS` | Dominio(s) del frontend que pueden llamar a la API |
| `JWT_HORAS` | Duración de la sesión (por defecto 8) |

El archivo `.env` **no se sube a git**. `.env.example` sirve de plantilla.

## Estructura
| Archivo | Qué contiene |
|---|---|
| `asistencia/models.py` | Modelo de datos y restricciones únicas (RN-01, RN-02, RN-03) |
| `asistencia/services.py` | Reglas de negocio: marcar, calcular faltas, modificar con auditoría, activar módulo |
| `asistencia/importers.py` | Lectura y validación de los Excel |
| `asistencia/views.py` | API JSON para estudiante y administrador |
| `asistencia/auth.py` | Login con JWT: roles estudiante y administrador |
| `asistencia/urls.py` | Rutas de la API |
| `asistencia/tests.py` | Pruebas de las reglas clave y de la API |
| `config/settings.py` | Configuración (lee `.env`) |

## API
| Método | Ruta | Quién |
|---|---|---|
| GET | `/api/modulo-activo/` | público |
| POST | `/api/estudiante/login/` | público → devuelve token |
| GET | `/api/estudiante/mi-asistencia/` | estudiante |
| POST | `/api/estudiante/marcar/` | estudiante |
| POST | `/api/panel/login/` | público → devuelve token |
| GET | `/api/panel/resumen/`, `estudiantes/`, `asistencias/`, `actividades/`, `modulos/` | admin |
| POST | `/api/panel/asistencias/modificar/` | admin |
| POST | `/api/panel/modulos/<id>/habilitar/`, `deshabilitar/`, `eliminar/` | admin |
| POST | `/api/panel/modulos/importar/validar/`, `confirmar/` | admin |
| GET | `/api/panel/exportar/` | admin (Excel) |

El token va en la cabecera `Authorization: Bearer <token>`.

## Despliegue
En Render, Railway o similar, con PostgreSQL. Carpeta raíz: `backend/`. Define las variables
de la tabla de arriba con `DEBUG=False` y `CORS_ALLOWED_ORIGINS=https://<dominio del frontend>`.

## Decisiones de diseño
- La **falta se calcula**: no se guarda un registro por cada ausencia.
- Zona horaria `America/La_Paz`.
- El reinicio de módulo **nunca borra**: marca el anterior como inactivo (transacción atómica).
- Se valida en el servidor que solo se marque el día de clase.
- Los correos también deben ser únicos por módulo, para que el acceso por correo no sea ambiguo.
- **JWT en lugar de sesiones**: las cookies de sesión no funcionan bien entre dos dominios distintos.
  El token del estudiante deja de valer si cambia el módulo activo.
- La importación no guarda nada hasta confirmar: el frontend reenvía los mismos archivos y se validan otra vez.
- Limitación conocida: el estudiante entra sin contraseña (como pide el documento).
