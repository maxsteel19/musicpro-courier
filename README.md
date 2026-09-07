# Music Pro Tour - Courier Management System

Sistema de gestión de envíos y logística desarrollado con Django para controlar paquetes, sucursales, entregas, incidencias y seguimiento operativo.

## Descripción del proyecto

Music Pro Tour es una aplicación web orientada a la gestión de courier/logística. Permite visualizar el estado de los paquetes, gestionar sucursales, registrar incidencias, supervisar entregas y analizar indicadores clave de rendimiento.

## Tecnologías utilizadas

- Python
- Django
- SQLite
- Bootstrap
- HTML / CSS / JavaScript

## Funcionalidades principales

- Dashboard con KPIs
- Gestión de envíos
- Seguimiento de paquetes
- Registro de sucursales
- Control de incidencias
- Visualización de estados y prioridades
- Interfaz responsiva

## Requisitos

- Python 3.10 o superior
- Django 5.x o superior
- pip

## Instalación

1. Clona el repositorio:

```bash
git clone https://github.com/maxsteel19/musicpro-courier.git
```

2. Ingresa a la carpeta del proyecto:

```bash
cd musicpro-courier
```

3. Crea un entorno virtual:

```bash
python -m venv venv
```

4. Activa el entorno virtual:

- Windows:

```bash
venv\Scripts\activate
```

- Linux/macOS:

```bash
source venv/bin/activate
```

5. Instala dependencias:

```bash
pip install -r requirements.txt
```

6. Ejecuta migraciones:

```bash
python manage.py migrate
```

7. Inicia el servidor:

```bash
python manage.py runserver
```

8. Abre la app en el navegador:

```text
http://localhost:8000/
```

## Uso

La aplicación incluye:

- Dashboard general
- Vista de envíos
- Visualización de paquetes
- Administración de sucursales
- Registro de incidencias
- Reportes y métricas

## Estado del proyecto

Proyecto funcional con estructura Django implementada, conectada a la base de datos y con datos de ejemplo para demostración.

## Autor

Proyecto desarrollado para evaluación académica / entregable de programación backend.

## Licencia

Uso académico.
