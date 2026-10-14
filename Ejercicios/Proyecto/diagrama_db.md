# Diagrama de base de datos - Proyecto Django

## Modelo conceptual

Cliente 1 --- * Pedido
Pedido 1 --- * DetallePedido
Producto 1 --- * DetallePedido

## Diagrama Mermaid

```mermaid
erDiagram
    CLIENTE ||--o{ PEDIDO : realiza
    PEDIDO ||--o{ DETALLE_PEDIDO : contiene
    PRODUCTO ||--o{ DETALLE_PEDIDO : incluye

    CLIENTE {
        int id PK
        string nombre
        string apellido
        string email UK
        string telefono
        string direccion
        boolean activo
        datetime created_at
        datetime updated_at
    }

    PRODUCTO {
        int id PK
        string codigo UK
        string nombre
        string categoria
        decimal precio
        int stock
        boolean activo
        datetime created_at
        datetime updated_at
    }

    PEDIDO {
        int id PK
        int cliente_id FK
        datetime fecha
        string estado
        string metodo_pago
        decimal total
    }

    DETALLE_PEDIDO {
        int id PK
        int pedido_id FK
        int producto_id FK
        int cantidad
        decimal precio_unitario
    }
```

## Relación entre tablas

- Un Cliente puede tener muchos Pedidos.
- Un Pedido pertenece a un Cliente.
- Un Pedido puede tener muchos Detalles de Pedido.
- Un Producto puede estar en muchos Detalles de Pedido.
- Un DetallePedido pertenece a un Pedido y a un Producto.

## Claves y atributos principales

- Cliente: id, nombre, apellido, email, telefono, direccion, activo.
- Producto: id, codigo, nombre, categoria, precio, stock, activo.
- Pedido: id, cliente_id, fecha, estado, metodo_pago, total.
- DetallePedido: id, pedido_id, producto_id, cantidad, precio_unitario.

## Correspondencia con Django

Este diagrama corresponde directamente a los modelos:
- Cliente
- Producto
- Pedido
- DetallePedido
