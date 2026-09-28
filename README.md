# Music Pro Tour - Courier (Proveedor - Cliente)

Sistema informático integral de transporte y despachos punto a punto para Music Pro Tour, desarrollado con Django y HTML/CSS/JavaScript.

## Descripción del proyecto

Music Pro Tour implementa un sistema de courier para gestionar envíos desde la bodega principal hacia sucursales y franquicias, con seguimiento, incidencias, notificaciones, KPIs y reportes.

## Funcionalidades principales

- Dashboard con métricas y KPIs
- Seguimiento en tiempo real de envíos
- Gestión de envíos por estado
- Gestión de paquetes
- Registro y seguimiento de incidencias
- Sucursales y red de distribución
- Reportes y analítica
- Notificaciones multicanal

## Tecnologías utilizadas

- Python
- Django
- SQLite
- Bootstrap 5
- HTML5 / CSS3 / JavaScript
- Chart.js
- Font Awesome

## Requisitos

- Python 3.x
- Django 4.x o superior
- SQLite

## Instalación

```bash
git clone https://github.com/maxsteel19/musicpro-courier.git
cd musicpro-courier
python -m venv venv
venv\Scripts\activate
pip install django
python manage.py migrate
python manage.py runserver
```

Accede en el navegador a:

```text
http://127.0.0.1:8000/
```

## Estado del proyecto

Prototipo funcional de la Fase 3 del sistema Courier para Music Pro Tour, integrado con Django y datos mock.

## Autor

Pablo Martínez

## Nota

Este proyecto mantiene el enfoque de Courier (Proveedor - Cliente) indicado en la corrección del informe, sin cambiarlo por un sistema de pago.
