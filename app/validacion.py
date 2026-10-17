from datetime import date

PRIORIDADES = ("baja", "media", "alta")
MAX_TITULO = 120
MAX_DESCRIPCION = 1000


def validar(datos, parcial=False):
    if not isinstance(datos, dict):
        return None, {"cuerpo": "Se esperaba un objeto JSON"}

    limpio = {}
    errores = {}

    if "titulo" in datos or not parcial:
        titulo = datos.get("titulo")
        if not isinstance(titulo, str) or not titulo.strip():
            errores["titulo"] = "El título es obligatorio"
        elif len(titulo.strip()) > MAX_TITULO:
            errores["titulo"] = f"El título admite hasta {MAX_TITULO} caracteres"
        else:
            limpio["titulo"] = titulo.strip()

    if "descripcion" in datos:
        descripcion = datos["descripcion"]
        if descripcion is None:
            descripcion = ""
        if not isinstance(descripcion, str) or len(descripcion) > MAX_DESCRIPCION:
            errores["descripcion"] = f"La descripción admite hasta {MAX_DESCRIPCION} caracteres"
        else:
            limpio["descripcion"] = descripcion.strip()

    if "prioridad" in datos:
        if datos["prioridad"] not in PRIORIDADES:
            errores["prioridad"] = "La prioridad debe ser baja, media o alta"
        else:
            limpio["prioridad"] = datos["prioridad"]

    if "fecha_limite" in datos:
        valor = datos["fecha_limite"]
        if valor in (None, ""):
            limpio["fecha_limite"] = None
        else:
            try:
                limpio["fecha_limite"] = date.fromisoformat(valor).isoformat()
            except (TypeError, ValueError):
                errores["fecha_limite"] = "La fecha debe tener el formato AAAA-MM-DD"

    if "completada" in datos:
        if not isinstance(datos["completada"], bool):
            errores["completada"] = "El estado debe ser verdadero o falso"
        else:
            limpio["completada"] = int(datos["completada"])

    return limpio, errores
