import os
import tempfile
import unittest
from datetime import date, timedelta

from app import create_app


class PruebasApi(unittest.TestCase):
    def setUp(self):
        self.carpeta = tempfile.TemporaryDirectory()
        ruta = os.path.join(self.carpeta.name, "prueba.db")
        self.cliente = create_app(db_path=ruta).test_client()

    def tearDown(self):
        self.carpeta.cleanup()

    def crear(self, **datos):
        datos.setdefault("titulo", "Tarea de prueba")
        return self.cliente.post("/api/tareas", json=datos)

    def test_crear_tarea_con_valores_por_defecto(self):
        respuesta = self.crear(titulo="  Comprar pan  ")
        self.assertEqual(respuesta.status_code, 201)
        tarea = respuesta.get_json()
        self.assertEqual(tarea["titulo"], "Comprar pan")
        self.assertEqual(tarea["prioridad"], "media")
        self.assertFalse(tarea["completada"])
        self.assertIsNone(tarea["fecha_limite"])

    def test_titulo_vacio_se_rechaza(self):
        respuesta = self.crear(titulo="   ")
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("titulo", respuesta.get_json()["detalles"])

    def test_prioridad_y_fecha_invalidas(self):
        self.assertEqual(self.crear(prioridad="urgente").status_code, 400)
        self.assertEqual(self.crear(fecha_limite="31/12/2026").status_code, 400)
        self.assertEqual(self.crear(fecha_limite=20261231).status_code, 400)

    def test_cuerpo_que_no_es_json(self):
        respuesta = self.cliente.post("/api/tareas", data="hola", content_type="text/plain")
        self.assertEqual(respuesta.status_code, 400)

    def test_obtener_y_404(self):
        id_tarea = self.crear().get_json()["id"]
        self.assertEqual(self.cliente.get(f"/api/tareas/{id_tarea}").status_code, 200)
        self.assertEqual(self.cliente.get("/api/tareas/999").status_code, 404)

    def test_actualizacion_parcial(self):
        id_tarea = self.crear(titulo="Original", prioridad="baja").get_json()["id"]
        respuesta = self.cliente.patch(f"/api/tareas/{id_tarea}", json={"completada": True})
        tarea = respuesta.get_json()
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(tarea["completada"])
        self.assertEqual(tarea["titulo"], "Original")
        self.assertEqual(tarea["prioridad"], "baja")

    def test_actualizar_con_datos_invalidos_o_vacios(self):
        id_tarea = self.crear().get_json()["id"]
        url = f"/api/tareas/{id_tarea}"
        self.assertEqual(self.cliente.patch(url, json={"titulo": ""}).status_code, 400)
        self.assertEqual(self.cliente.patch(url, json={"completada": "si"}).status_code, 400)
        self.assertEqual(self.cliente.patch(url, json={}).status_code, 400)
        self.assertEqual(self.cliente.patch("/api/tareas/999", json={"titulo": "x"}).status_code, 404)

    def test_quitar_fecha_limite(self):
        id_tarea = self.crear(fecha_limite="2030-01-15").get_json()["id"]
        respuesta = self.cliente.patch(f"/api/tareas/{id_tarea}", json={"fecha_limite": None})
        self.assertIsNone(respuesta.get_json()["fecha_limite"])

    def test_eliminar(self):
        id_tarea = self.crear().get_json()["id"]
        self.assertEqual(self.cliente.delete(f"/api/tareas/{id_tarea}").status_code, 204)
        self.assertEqual(self.cliente.delete(f"/api/tareas/{id_tarea}").status_code, 404)
        self.assertEqual(self.cliente.get("/api/tareas").get_json(), [])

    def test_filtrar_por_estado_y_prioridad(self):
        hecha = self.crear(titulo="Hecha", prioridad="alta").get_json()["id"]
        self.crear(titulo="Pendiente", prioridad="baja")
        self.cliente.patch(f"/api/tareas/{hecha}", json={"completada": True})

        pendientes = self.cliente.get("/api/tareas?estado=pendientes").get_json()
        completadas = self.cliente.get("/api/tareas?estado=completadas").get_json()
        altas = self.cliente.get("/api/tareas?prioridad=alta").get_json()

        self.assertEqual([t["titulo"] for t in pendientes], ["Pendiente"])
        self.assertEqual([t["titulo"] for t in completadas], ["Hecha"])
        self.assertEqual([t["titulo"] for t in altas], ["Hecha"])
        self.assertEqual(self.cliente.get("/api/tareas?estado=otro").status_code, 400)
        self.assertEqual(self.cliente.get("/api/tareas?prioridad=otra").status_code, 400)
        self.assertEqual(self.cliente.get("/api/tareas?orden=otro").status_code, 400)

    def test_busqueda_por_texto_y_caracteres_especiales(self):
        self.crear(titulo="Pagar la luz", descripcion="Recibo de febrero")
        self.crear(titulo="Descuento del 50%")
        self.crear(titulo="Otra cosa")

        luz = self.cliente.get("/api/tareas?q=luz").get_json()
        febrero = self.cliente.get("/api/tareas?q=febrero").get_json()
        porcentaje = self.cliente.get("/api/tareas?q=50%25").get_json()
        guion_bajo = self.cliente.get("/api/tareas?q=_").get_json()

        self.assertEqual(len(luz), 1)
        self.assertEqual(len(febrero), 1)
        self.assertEqual([t["titulo"] for t in porcentaje], ["Descuento del 50%"])
        self.assertEqual(guion_bajo, [])

    def test_orden_por_prioridad_y_pendientes_primero(self):
        self.crear(titulo="Baja", prioridad="baja")
        self.crear(titulo="Alta", prioridad="alta")
        self.crear(titulo="Media", prioridad="media")
        hecha = self.crear(titulo="Alta hecha", prioridad="alta").get_json()["id"]
        self.cliente.patch(f"/api/tareas/{hecha}", json={"completada": True})

        titulos = [t["titulo"] for t in self.cliente.get("/api/tareas").get_json()]
        self.assertEqual(titulos, ["Alta", "Media", "Baja", "Alta hecha"])

    def test_orden_por_fecha_deja_las_que_no_tienen_al_final(self):
        self.crear(titulo="Sin fecha")
        self.crear(titulo="Tarde", fecha_limite="2031-05-01")
        self.crear(titulo="Pronto", fecha_limite="2030-01-01")

        titulos = [t["titulo"] for t in self.cliente.get("/api/tareas?orden=fecha").get_json()]
        self.assertEqual(titulos, ["Pronto", "Tarde", "Sin fecha"])

    def test_resumen(self):
        ayer = (date.today() - timedelta(days=1)).isoformat()
        manana = (date.today() + timedelta(days=1)).isoformat()
        self.crear(titulo="Vencida", prioridad="alta", fecha_limite=ayer)
        self.crear(titulo="Futura", prioridad="baja", fecha_limite=manana)
        hecha = self.crear(titulo="Hecha", fecha_limite=ayer).get_json()["id"]
        self.cliente.patch(f"/api/tareas/{hecha}", json={"completada": True})

        resumen = self.cliente.get("/api/tareas/resumen").get_json()
        self.assertEqual(resumen["total"], 3)
        self.assertEqual(resumen["pendientes"], 2)
        self.assertEqual(resumen["completadas"], 1)
        self.assertEqual(resumen["vencidas"], 1)
        self.assertEqual(resumen["pendientes_por_prioridad"], {"baja": 1, "media": 0, "alta": 1})

    def test_rutas_de_la_api_inexistentes_devuelven_json(self):
        respuesta = self.cliente.get("/api/nada")
        self.assertEqual(respuesta.status_code, 404)
        self.assertIn("error", respuesta.get_json())

    def test_pagina_principal(self):
        respuesta = self.cliente.get("/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn(b"Gestor de tareas", respuesta.data)
        respuesta.close()


if __name__ == "__main__":
    unittest.main()
