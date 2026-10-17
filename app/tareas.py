from datetime import date

from flask import Blueprint, jsonify, request

from .db import get_db
from .validacion import PRIORIDADES, validar

bp = Blueprint("tareas", __name__, url_prefix="/api/tareas")

COLUMNAS = "id, titulo, descripcion, prioridad, fecha_limite, completada, creada_en"

ORDENES = {
    "prioridad": (
        "completada ASC, "
        "CASE prioridad WHEN 'alta' THEN 0 WHEN 'media' THEN 1 ELSE 2 END, "
        "fecha_limite IS NULL, fecha_limite ASC, id DESC"
    ),
    "fecha": "completada ASC, fecha_limite IS NULL, fecha_limite ASC, id DESC",
    "recientes": "id DESC",
}


def a_dict(fila):
    return {
        "id": fila["id"],
        "titulo": fila["titulo"],
        "descripcion": fila["descripcion"],
        "prioridad": fila["prioridad"],
        "fecha_limite": fila["fecha_limite"],
        "completada": bool(fila["completada"]),
        "creada_en": fila["creada_en"],
    }


def error(mensaje, codigo, detalles=None):
    cuerpo = {"error": mensaje}
    if detalles:
        cuerpo["detalles"] = detalles
    return jsonify(cuerpo), codigo


def buscar(tarea_id):
    return get_db().execute(
        f"SELECT {COLUMNAS} FROM tareas WHERE id = ?", (tarea_id,)
    ).fetchone()


@bp.get("")
def listar():
    condiciones = []
    parametros = []

    estado = request.args.get("estado", "todas")
    if estado == "pendientes":
        condiciones.append("completada = 0")
    elif estado == "completadas":
        condiciones.append("completada = 1")
    elif estado != "todas":
        return error("Estado no válido", 400)

    prioridad = request.args.get("prioridad")
    if prioridad:
        if prioridad not in PRIORIDADES:
            return error("Prioridad no válida", 400)
        condiciones.append("prioridad = ?")
        parametros.append(prioridad)

    texto = request.args.get("q", "").strip()
    if texto:
        escapado = texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        patron = f"%{escapado}%"
        condiciones.append("(titulo LIKE ? ESCAPE '\\' OR descripcion LIKE ? ESCAPE '\\')")
        parametros.extend([patron, patron])

    orden = ORDENES.get(request.args.get("orden", "prioridad"))
    if orden is None:
        return error("Orden no válido", 400)

    consulta = f"SELECT {COLUMNAS} FROM tareas"
    if condiciones:
        consulta += " WHERE " + " AND ".join(condiciones)
    consulta += " ORDER BY " + orden

    filas = get_db().execute(consulta, parametros).fetchall()
    return jsonify([a_dict(f) for f in filas])


@bp.get("/resumen")
def resumen():
    db = get_db()
    total = db.execute("SELECT COUNT(*) FROM tareas").fetchone()[0]
    completadas = db.execute("SELECT COUNT(*) FROM tareas WHERE completada = 1").fetchone()[0]
    vencidas = db.execute(
        "SELECT COUNT(*) FROM tareas "
        "WHERE completada = 0 AND fecha_limite IS NOT NULL AND fecha_limite < ?",
        (date.today().isoformat(),),
    ).fetchone()[0]

    por_prioridad = {p: 0 for p in PRIORIDADES}
    for fila in db.execute(
        "SELECT prioridad, COUNT(*) FROM tareas WHERE completada = 0 GROUP BY prioridad"
    ):
        por_prioridad[fila[0]] = fila[1]

    return jsonify(
        {
            "total": total,
            "pendientes": total - completadas,
            "completadas": completadas,
            "vencidas": vencidas,
            "pendientes_por_prioridad": por_prioridad,
        }
    )


@bp.get("/<int:tarea_id>")
def obtener(tarea_id):
    fila = buscar(tarea_id)
    if fila is None:
        return error("Tarea no encontrada", 404)
    return jsonify(a_dict(fila))


@bp.post("")
def crear():
    datos, errores = validar(request.get_json(silent=True))
    if errores:
        return error("Datos no válidos", 400, errores)

    db = get_db()
    cursor = db.execute(
        "INSERT INTO tareas (titulo, descripcion, prioridad, fecha_limite) VALUES (?, ?, ?, ?)",
        (
            datos["titulo"],
            datos.get("descripcion", ""),
            datos.get("prioridad", "media"),
            datos.get("fecha_limite"),
        ),
    )
    db.commit()
    return jsonify(a_dict(buscar(cursor.lastrowid))), 201


@bp.patch("/<int:tarea_id>")
def actualizar(tarea_id):
    if buscar(tarea_id) is None:
        return error("Tarea no encontrada", 404)

    datos, errores = validar(request.get_json(silent=True), parcial=True)
    if errores:
        return error("Datos no válidos", 400, errores)
    if not datos:
        return error("No hay cambios que aplicar", 400)

    asignaciones = ", ".join(f"{columna} = ?" for columna in datos)
    db = get_db()
    db.execute(
        f"UPDATE tareas SET {asignaciones} WHERE id = ?",
        (*datos.values(), tarea_id),
    )
    db.commit()
    return jsonify(a_dict(buscar(tarea_id)))


@bp.delete("/<int:tarea_id>")
def eliminar(tarea_id):
    db = get_db()
    cursor = db.execute("DELETE FROM tareas WHERE id = ?", (tarea_id,))
    db.commit()
    if cursor.rowcount == 0:
        return error("Tarea no encontrada", 404)
    return "", 204
