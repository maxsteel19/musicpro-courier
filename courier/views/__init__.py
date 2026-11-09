"""Vistas del sistema, separadas por responsabilidad.

- ``publico``:  página de inicio sin sesión.
- ``cuentas``:  inicio/cierre de sesión y cambio de contraseña.
- ``panel``:    dashboard, seguimiento, perfil y endpoints JSON.
- ``gestion``:  mantenedores (CRUD) de las entidades del caso.
- ``usuarios``: mantenedor de usuarios (solo administradores).
- ``reportes``: reportes construidos con el ORM de Django.
"""
from .cuentas import CambiarPasswordView, CerrarSesionView, IniciarSesionView  # noqa: F401
from .gestion import *  # noqa: F401,F403
from .panel import api_envios, api_kpis, api_sucursales, dashboard, perfil, seguimiento  # noqa: F401
from .publico import inicio  # noqa: F401
from .reportes import reporte_detalle, reportes_indice  # noqa: F401
from .usuarios import (  # noqa: F401
    usuario_cambiar_estado, usuario_crear, usuario_editar, usuario_eliminar,
    usuario_lista, usuario_password,
)
