# Guía para la defensa: Evaluación 3

La pauta advierte que, si no puedes explicar el código, la nota es 1,0. Esta guía resume **cómo funciona cada parte**, **dónde está** y **qué preguntas pueden hacerte**. Léela con el código abierto al lado.

---

## 1. Guion sugerido de la demostración (10 minutos)

1. **Arrancar el sistema:** `python manage.py runserver` y mostrar en `musicpro/settings.py` que `DATABASES` usa `django.db.backends.mysql`.
2. **Probar la protección:** en una ventana privada, abrir `http://127.0.0.1:8000/vehiculos/`. Django redirige a `/cuentas/login/?next=/vehiculos/` y muestra "Debe iniciar sesión".
3. **Iniciar sesión** como administrador. Vuelves a `/vehiculos/` gracias a `next`.
4. **CRUD:** crear un vehículo, editarlo y eliminarlo. Mostrar en MySQL Workbench (`SELECT * FROM courier_vehiculo;`) que el cambio quedó guardado.
5. **Validaciones:** intentar un RUT con dígito verificador incorrecto, o un viaje que llega antes de salir.
6. **Integridad:** intentar eliminar un conductor con viajes. El sistema lo impide (`PROTECT`).
7. **Usuarios:** crear un usuario operador, desactivarlo y volver a activarlo.
8. **Roles:** cerrar sesión, entrar como operador y abrir `/usuarios/`. Responde **403 Acceso denegado**.
9. **Sesión:** abrir **Mi perfil** (usuario, inicio de sesión, expiración).
10. **Cerrar sesión** y presionar "Atrás": no se muestran datos y pide login.
11. **Reportes:** abrir `/reportes/`, ejecutar los reportes que pidió el docente y mostrar el código ORM y el SQL generado.

---

## 2. Base de datos MySQL

- **Archivo:** `musicpro/settings.py`, bloque `DATABASES`.
- `ENGINE = 'django.db.backends.mysql'`. Los datos de conexión salen de variables de entorno, que se cargan desde `.env` con la función `_cargar_archivo_env`.
- **Driver:** `PyMySQL`. En `musicpro/__init__.py`, `pymysql.install_as_MySQLdb()` lo hace pasar por `mysqlclient`, que es el driver que Django espera.
- `charset utf8mb4` permite guardar tildes, ñ y emojis.
- **Migraciones:** `python manage.py makemigrations` crea los archivos en `courier/migrations/` y `python manage.py migrate` crea las tablas en MySQL.

**Pregunta probable:** _¿Por qué no está la contraseña en settings.py?_
Porque el proyecto está en GitHub. Las credenciales van en `.env`, que está en `.gitignore`.

---

## 3. Autenticación (login / logout)

| Pieza | Archivo | Qué hace |
|---|---|---|
| `IniciarSesionView` | `courier/views/cuentas.py` | Hereda de `LoginView`. Valida usuario y clave con `authenticate()` y llama a `login()` |
| `CerrarSesionView` | `courier/views/cuentas.py` | Hereda de `LogoutView`. Llama a `logout()`, que borra la sesión |
| URLs | `musicpro/urls.py` | `/cuentas/login/`, `/cuentas/logout/`, `/cuentas/password/` |
| `LOGIN_URL`, `LOGIN_REDIRECT_URL`, `LOGOUT_REDIRECT_URL` | `settings.py` | A dónde redirigir en cada caso |

**¿Qué pasa al iniciar sesión?**

1. El formulario `AuthenticationForm` revisa la clave contra el hash guardado en `auth_user.password`.
2. `login(request, user)` crea una sesión **nueva** (cambia el id, contra la fijación de sesión) y guarda el id del usuario en ella (`_auth_user_id`).
3. El navegador recibe la cookie `sessionid`. La sesión queda en la tabla `django_session`.
4. En cada petición, `AuthenticationMiddleware` lee la cookie y deja disponible `request.user`.

**¿Por qué el logout es un formulario POST?** Un enlace GET se podría disparar desde otro sitio (por ejemplo, con una imagen). Con POST + token CSRF, solo nuestro formulario puede cerrar la sesión. Desde Django 5, `LogoutView` ya no acepta GET.

---

## 4. Decoradores y protección de vistas

```python
@login_required
def vehiculo_lista(request):
    ...
```

- `login_required` (de `django.contrib.auth.decorators`) revisa `request.user.is_authenticated`.
- Si el usuario no inició sesión, responde con una **redirección 302** a `LOGIN_URL?next=<url pedida>` y **la vista no se ejecuta**. Por eso un POST sin sesión no modifica la base de datos.
- **Decorador propio:** `@administrador_requerido`, en `courier/decorators.py`. Combina `login_required` con una revisión de rol. Sin sesión, va al login. Con sesión pero sin rol, levanta `PermissionDenied` (**403**).
- `@require_http_methods(['GET', 'POST'])` y `@require_POST` limitan los métodos HTTP. Por ejemplo, desactivar un usuario solo funciona por POST.

**Pregunta probable:** _¿Qué hace `@wraps` en tu decorador?_
Conserva el nombre y la documentación de la vista original. Sin él, todas las vistas decoradas se llamarían `_vista_protegida`.

**Pregunta probable:** _Si escribo la URL directamente, ¿qué pasa?_
La petición llega igual a la vista, pero el decorador se ejecuta antes y redirige al login. Lo prueba el test `test_vistas_protegidas_redirigen_al_login_sin_sesion`, que recorre **todas** las URLs privadas.

---

## 5. Uso de la sesión

- `request.user` es el usuario identificado por la sesión. Se usa para:
  - guardar quién creó un envío (`envio.creado_por = request.user`, en `courier/views/gestion.py`),
  - guardar quién reportó una incidencia (`incidencia.reportada_por = request.user`),
  - mostrar el nombre y el rol en la barra superior,
  - impedir que un administrador se desactive o se elimine a sí mismo.
- `request.session` guarda datos propios: al iniciar sesión se graban `inicio_sesion` y `acceso_anterior`, que se ven en **Mi perfil**.
- **Expiración** (en `settings.py`): `SESSION_COOKIE_AGE = 3600` (una hora de inactividad), `SESSION_EXPIRE_AT_BROWSER_CLOSE = True` y `SESSION_SAVE_EVERY_REQUEST = True`, que renueva la hora con cada clic.
- El **middleware** `courier/middleware.py` añade `Cache-Control: no-store` a las respuestas de usuarios autenticados. Así, tras cerrar sesión, el botón "Atrás" no muestra la página guardada.

---

## 6. CRUD de entidades

Cada entidad tiene 4 vistas en `courier/views/gestion.py`: **lista**, **crear**, **editar** y **eliminar**. Crear, editar y eliminar comparten dos funciones de `courier/views/utils.py`:

- `formulario_crud(...)`
  - GET: muestra el formulario vacío (crear) o con los datos actuales (editar, `instance=objeto`).
  - POST válido: `form.save()` hace el `INSERT` o el `UPDATE` con el ORM y redirige con un mensaje.
  - POST inválido: vuelve a mostrar el formulario con los errores.
- `eliminar_crud(...)`
  - GET: pide confirmación.
  - POST: `objeto.delete()`. Si hay registros asociados con `PROTECT`, Django lanza `ProtectedError`. La vista lo captura y muestra un mensaje sin borrar nada.

Los **formularios** (`courier/forms.py`) son `ModelForm`, con validaciones en `clean_<campo>()` y `clean()`:

- RUT con dígito verificador (`courier/validators.py`, algoritmo módulo 11),
- patente chilena normalizada (`bcdf12` se guarda como `BCDF-12`),
- origen distinto del destino, llegada posterior a la salida, conductor activo, etc.

Los **listados** usan el ORM para buscar (`Q(nombre__icontains=q) | Q(rut__icontains=q)`), filtrar, contar relacionados (`annotate(total_viajes=Count('viajes'))`) y paginar (`Paginator`).

---

## 7. Mantención de usuarios

En `courier/views/usuarios.py`, todas las vistas usan `@administrador_requerido`.

| Acción | Cómo |
|---|---|
| Crear | `UsuarioCrearForm` (hereda de `UserCreationForm`). La clave se guarda con hash, nunca en texto plano |
| Consultar | Listado con búsqueda y filtros por rol y estado |
| Modificar | `UsuarioEditarForm`. En la propia cuenta, los campos de rol y estado quedan bloqueados |
| Cambiar clave | `SetPasswordForm` |
| Desactivar | `is_active = False`: el usuario ya no puede entrar, pero se conserva su historial |
| Eliminar | Con confirmación. No se puede eliminar la propia cuenta |

**Pregunta probable:** _¿Por qué desactivar en vez de eliminar?_
Porque eliminar borra la relación con los envíos e incidencias que registró. Desactivar bloquea el acceso y mantiene el historial.

---

## 8. Reportes con Django ORM (Parte 2)

- **Archivo:** `courier/reportes.py`. Cada consulta es una función decorada con `@reporte(numero, nivel, pregunta)`, que la registra en el diccionario `REPORTES`.
- La vista `courier/views/reportes.py` ejecuta la función, captura el SQL con `CaptureQueriesContext` y muestra el resultado, el código (`inspect.getsource`) y el SQL.

**Conceptos ORM que debes saber explicar:**

| Concepto | Ejemplo en el proyecto | SQL equivalente |
|---|---|---|
| `filter()` | `Vehiculo.objects.filter(disponible=True)` | `WHERE disponible = 1` |
| Relaciones con `__` | `filter(vehiculos__viajes__isnull=True)` | `LEFT JOIN` + `IS NULL` |
| `select_related()` | `Viaje.objects.select_related('vehiculo', 'conductor')` | Trae las FK con un `JOIN` y evita el problema N+1 |
| `annotate()` | `Conductor.objects.annotate(total=Count('viajes'))` | `COUNT(...) GROUP BY conductor.id` |
| `aggregate()` | `Viaje.objects.aggregate(total=Count('id'))` | Un solo valor para toda la tabla |
| `values().annotate()` | `values('destino').annotate(total=Count('id'))` | `GROUP BY destino` |
| Agregación condicional | `Count('id', filter=Q(estado='finalizado'))` | `COUNT(CASE WHEN estado='finalizado' THEN id END)` |
| `F()` | `Avg(F('fecha_llegada') - F('fecha_salida'))` | Operar entre columnas de la misma fila |
| `Q()` | `Q(nombre__icontains=q) \| Q(rut__icontains=q)` | `OR` en el `WHERE` |
| Subconsulta | `exclude(id__in=Viaje.objects.filter(...).values('conductor_id'))` | `WHERE id NOT IN (SELECT ...)` |
| `Case/When` | Orden por prioridad en el panel | `ORDER BY CASE WHEN ... END` |

**Pregunta probable:** _¿Por qué no usaste `__date` o `TruncMonth`?_
Con `USE_TZ = True`, Django convierte las fechas con `CONVERT_TZ` de MySQL. Si MySQL no tiene cargadas las tablas de zonas horarias (lo normal en Windows), esa función devuelve `NULL` y el reporte sale vacío. Por eso calculamos los límites de cada día o mes en Python, con la zona de Chile, y filtramos con `__gte` / `__lt`.

**Pregunta probable:** _¿Qué es el problema N+1?_
Si listas 100 viajes y en la plantilla muestras `viaje.conductor.nombre`, Django haría 1 consulta para los viajes y 100 más para los conductores. `select_related('conductor')` lo resuelve con un `JOIN` en una sola consulta.

---

## 9. Pruebas

`python manage.py test courier` ejecuta 52 pruebas (carpeta `courier/tests/`). Si te preguntan cómo sabes que la protección funciona, muestra `test_autenticacion.py`.

---

## 10. Preguntas rápidas

- **¿Dónde se guardan las contraseñas?** En `auth_user.password`, como hash PBKDF2 con sal (formato `pbkdf2_sha256$iteraciones$sal$hash`).
- **¿Qué es CSRF?** Un ataque en el que otro sitio envía formularios en tu nombre. `{% csrf_token %}` agrega un token secreto que Django verifica en cada POST.
- **¿Qué diferencia hay entre 302 y 403?** 302: no iniciaste sesión, te mando al login. 403: iniciaste sesión, pero no tienes permiso.
- **¿Qué hace `on_delete=PROTECT`?** Impide borrar un registro mientras otros lo referencian.
- **¿Para qué sirve `get_object_or_404`?** Si el id no existe, responde 404 en vez de un error 500.
- **¿Por qué hay un `.env.example` y no un `.env` en GitHub?** El ejemplo muestra qué variables hacen falta, sin exponer las claves reales.
