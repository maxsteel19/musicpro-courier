"""Paquete del proyecto Django.

Si el driver oficial ``mysqlclient`` no está instalado, se usa PyMySQL
(driver 100 % Python, fácil de instalar en Windows) como reemplazo.
"""
try:
    import MySQLdb  # noqa: F401  (mysqlclient)
except ImportError:
    try:
        import pymysql

        pymysql.install_as_MySQLdb()
    except ImportError:
        pass
