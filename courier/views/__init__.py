"""Vistas del sistema, separadas por responsabilidad.

- ``publico``:  página de inicio y política de privacidad, sin sesión.
- ``cuentas``:  login con bloqueo, logout, contraseñas, recuperación y acuerdo de datos.
- ``panel``:    dashboard, seguimiento, perfil y endpoints JSON.
- ``gestion``:  mantenedores (CRUD) de las entidades del caso.
- ``usuarios``: mantenedor de usuarios y bitácora de auditoría (solo administradores).
- ``reportes``: reportes construidos con el ORM de Django.
"""
from .cuentas import (  # noqa: F401
    CambiarPasswordView, CerrarSesionView, IniciarSesionView, RecuperarPasswordConfirmarView,
    RecuperarPasswordEnviadoView, RecuperarPasswordListoView, RecuperarPasswordView, acuerdo_datos,
)
from .gestion import *  # noqa: F401,F403
from .panel import api_envios, api_kpis, api_sucursales, dashboard, perfil, seguimiento  # noqa: F401
from .publico import inicio, privacidad  # noqa: F401
from .reportes import reporte_detalle, reportes_indice  # noqa: F401
from .usuarios import (  # noqa: F401
    auditoria_lista, usuario_cambiar_estado, usuario_crear, usuario_desbloquear, usuario_editar,
    usuario_eliminar, usuario_lista, usuario_password,
)
