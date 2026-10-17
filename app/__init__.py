import os

from flask import Flask, jsonify, request

from . import db
from .tareas import bp


def create_app(db_path=None):
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path or os.getenv("DB_PATH", "data/tareas.db")

    db.init_app(app)
    app.register_blueprint(bp)

    @app.get("/")
    def index():
        return app.send_static_file("index.html")

    @app.errorhandler(404)
    def no_encontrado(error):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Recurso no encontrado"}), 404
        return error

    @app.errorhandler(405)
    def metodo_no_permitido(error):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Método no permitido"}), 405
        return error

    return app
