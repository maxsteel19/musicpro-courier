# Evaluación 2 - Aplicación web con Django Admin

## Descripción

Este proyecto fue desarrollado como parte de la Evaluación 2, donde se construye una aplicación web con Django, configurando la base de datos, gestionando su estructura mediante migraciones, representando el modelo de datos y usando Django Admin para administrar la información.

La aplicación corresponde a un sistema de gestión logística para Music Pro Tour, enfocado en sucursales, paquetes, envíos, incidencias y notificaciones.

## Objetivo general

Desarrollar una aplicación web con Django que permita:

- configurar la conexión a una base de datos,
- modelar correctamente las entidades y relaciones,
- generar migraciones y aplicarlas,
- administrar registros desde Django Admin,
- realizar operaciones CRUD,
- aplicar filtros y búsquedas,
- cargar datos de prueba con Faker.

## Requisitos evaluados

### 1. Configuración de la base de datos
- La aplicación está conectada a SQLite mediante Django.
- La configuración se encuentra en `musicpro/settings.py`.
- La base de datos utilizada es SQLite (`db.sqlite3`).

### 2. Modelamiento de datos
Se definieron los modelos principales:

- `Sucursal`
- `Paquete`
- `Envio`
- `Incidencia`
- `Notificacion`

Cada modelo contiene atributos relevantes, tipos de datos y relaciones entre entidades.

### 3. Diagrama de base de datos
El proyecto incluye un diagrama de base de datos que representa las tablas, sus atributos y relaciones de manera visual.

### 4. Migraciones
- Las migraciones se generan con Django.
- El historial se mantiene en la carpeta `courier/migrations`.
- Se aplican con `python manage.py migrate`.

### 5. Django Admin
El administrador se configura en `courier/admin.py` y permite:

- ver registros,
- crear nuevos datos,
- editar información,
- eliminar registros,
- aplicar filtros,
- buscar por texto,
- personalizar la vista de administración.

### 6. CRUD
La aplicación permite realizar operaciones básicas sobre los modelos:

- Crear
- Leer
- Actualizar
- Eliminar

Esto se valida principalmente desde el panel administrativo de Django y desde las vistas del proyecto.

### 7. Generación de datos de prueba
Se incorporó una carga de datos ficticios usando Faker para probar la aplicación con información realista.

## Estructura del proyecto

```text
musicpro/
    settings.py
    urls.py
    wsgi.py

courier/
    admin.py
    models.py
    views.py
    urls.py
    migrations/
    management/
        commands/
            seed_courier.py

templates/
    courier/

static/
    css/

manage.py
README.md
```

## Tecnologías utilizadas

- Python
- Django
- SQLite
- HTML/CSS
- JavaScript
- Bootstrap
- Faker

## Instalación

1. Clonar el repositorio:

```bash
git clone https://github.com/maxsteel19/musicpro-courier.git
cd musicpro-courier
```

2. Crear entorno virtual:

```bash
python -m venv env
```

3. Activar entorno virtual:

Windows:

```bash
env\Scripts\activate
```

4. Instalar dependencias:

```bash
pip install django faker
```

5. Ejecutar migraciones:

```bash
python manage.py migrate
```

6. Ejecutar servidor:

```bash
python manage.py runserver
```

7. Acceder a la aplicación:

```text
http://127.0.0.1:8000/
```

## Administrador de Django

Para acceder al panel administrativo:

```bash
python manage.py createsuperuser
```

Luego entrar a:

```text
http://127.0.0.1:8000/admin/
```

## Datos de prueba

Se puede cargar información inicial con:

```bash
python manage.py seed_courier
```

También se puede generar datos con Faker para probar la carga masiva y validar la persistencia de datos.

## Verificación

Se ejecutan pruebas para comprobar funcionamiento del proyecto y del administrador:

```bash
python manage.py test
```

## Estado del proyecto

El proyecto cumple con los aspectos principales de la evaluación:

- conexión a base de datos,
- modelado de datos,
- migraciones,
- Django Admin,
- CRUD,
- filtros y búsquedas,
- generación de datos ficticios para pruebas.

## Autor

Pablo Martínez

## Nota

Este README fue redactado con enfoque exclusivo en la Evaluación 2: Aplicación web con Django Admin.
