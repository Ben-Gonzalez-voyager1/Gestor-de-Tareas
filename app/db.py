import os
import sqlite3

from flask import current_app, g

ESQUEMA = """
CREATE TABLE IF NOT EXISTS tareas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT NOT NULL,
    descripcion TEXT NOT NULL DEFAULT '',
    prioridad TEXT NOT NULL DEFAULT 'media' CHECK (prioridad IN ('baja', 'media', 'alta')),
    fecha_limite TEXT,
    completada INTEGER NOT NULL DEFAULT 0,
    creada_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DB_PATH"])
        g.db.row_factory = sqlite3.Row
    return g.db


def cerrar_db(error=None):
    conexion = g.pop("db", None)
    if conexion is not None:
        conexion.close()


def crear_tablas(ruta):
    carpeta = os.path.dirname(ruta)
    if carpeta:
        os.makedirs(carpeta, exist_ok=True)
    conexion = sqlite3.connect(ruta)
    conexion.executescript(ESQUEMA)
    conexion.commit()
    conexion.close()


def init_app(app):
    app.teardown_appcontext(cerrar_db)
    crear_tablas(app.config["DB_PATH"])
