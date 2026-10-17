const estado = { filtro: "todas", prioridad: "", busqueda: "" };

const el = {
  lista: document.getElementById("lista"),
  vacio: document.getElementById("vacio"),
  mensaje: document.getElementById("mensaje"),
  formNueva: document.getElementById("form-nueva"),
  pestanas: document.getElementById("pestanas"),
  filtroPrioridad: document.getElementById("f-prioridad"),
  busqueda: document.getElementById("f-busqueda"),
  dialogo: document.getElementById("dialogo"),
  formEditar: document.getElementById("form-editar"),
  cancelar: document.getElementById("cancelar"),
};

let editandoId = null;
let temporizadorMensaje = null;
let temporizadorBusqueda = null;

async function peticion(url, opciones = {}) {
  const respuesta = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...opciones,
  });
  if (respuesta.status === 204) return null;

  const datos = await respuesta.json().catch(() => ({}));
  if (!respuesta.ok) {
    const detalles = datos.detalles ? Object.values(datos.detalles).join(". ") : "";
    throw new Error(detalles || datos.error || "Ocurrió un error inesperado");
  }
  return datos;
}

function mostrarMensaje(texto) {
  clearTimeout(temporizadorMensaje);
  el.mensaje.textContent = texto;
  el.mensaje.hidden = !texto;
  if (texto) {
    temporizadorMensaje = setTimeout(() => mostrarMensaje(""), 5000);
  }
}

function hoyISO() {
  const ahora = new Date();
  const local = new Date(ahora.getTime() - ahora.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 10);
}

function formatearFecha(iso) {
  const [anio, mes, dia] = iso.split("-");
  return `${dia}/${mes}/${anio}`;
}

function crearElemento(etiqueta, clase, texto) {
  const nodo = document.createElement(etiqueta);
  if (clase) nodo.className = clase;
  if (texto !== undefined) nodo.textContent = texto;
  return nodo;
}

function crearBoton(texto, clase, accion) {
  const boton = crearElemento("button", clase, texto);
  boton.type = "button";
  boton.addEventListener("click", accion);
  return boton;
}

function crearItem(tarea) {
  const vencida = !tarea.completada && tarea.fecha_limite && tarea.fecha_limite < hoyISO();

  const item = crearElemento("li", `tarea prioridad-${tarea.prioridad}`);
  if (tarea.completada) item.classList.add("completada");
  if (vencida) item.classList.add("vencida");

  const casilla = document.createElement("input");
  casilla.type = "checkbox";
  casilla.checked = tarea.completada;
  casilla.setAttribute("aria-label", `Marcar "${tarea.titulo}" como completada`);
  casilla.addEventListener("change", () => actualizar(tarea.id, { completada: casilla.checked }));

  const cuerpo = crearElemento("div");
  cuerpo.appendChild(crearElemento("div", "titulo", tarea.titulo));
  if (tarea.descripcion) {
    cuerpo.appendChild(crearElemento("p", "descripcion", tarea.descripcion));
  }
  const meta = crearElemento("div", "meta");
  meta.appendChild(crearElemento("span", "", `Prioridad ${tarea.prioridad}`));
  if (tarea.fecha_limite) {
    const etiqueta = vencida ? "Venció el " : "Hasta el ";
    meta.appendChild(crearElemento("span", "fecha", etiqueta + formatearFecha(tarea.fecha_limite)));
  }
  cuerpo.appendChild(meta);

  const acciones = crearElemento("div", "acciones");
  acciones.appendChild(crearBoton("Editar", "", () => abrirEdicion(tarea)));
  acciones.appendChild(crearBoton("Eliminar", "eliminar", () => eliminar(tarea)));

  item.append(casilla, cuerpo, acciones);
  return item;
}

function pintarLista(tareas) {
  el.lista.replaceChildren(...tareas.map(crearItem));
  el.vacio.hidden = tareas.length > 0;
}

function pintarResumen(resumen) {
  document.getElementById("r-total").textContent = resumen.total;
  document.getElementById("r-pendientes").textContent = resumen.pendientes;
  document.getElementById("r-completadas").textContent = resumen.completadas;
  document.getElementById("r-vencidas").textContent = resumen.vencidas;
}

async function cargar() {
  const parametros = new URLSearchParams({ estado: estado.filtro });
  if (estado.prioridad) parametros.set("prioridad", estado.prioridad);
  if (estado.busqueda) parametros.set("q", estado.busqueda);

  try {
    const [tareas, resumen] = await Promise.all([
      peticion(`/api/tareas?${parametros}`),
      peticion("/api/tareas/resumen"),
    ]);
    pintarResumen(resumen);
    pintarLista(tareas);
  } catch (error) {
    mostrarMensaje(error.message);
  }
}

async function actualizar(id, cambios) {
  try {
    await peticion(`/api/tareas/${id}`, { method: "PATCH", body: JSON.stringify(cambios) });
    mostrarMensaje("");
  } catch (error) {
    mostrarMensaje(error.message);
  }
  await cargar();
}

async function eliminar(tarea) {
  if (!confirm(`¿Eliminar la tarea "${tarea.titulo}"?`)) return;
  try {
    await peticion(`/api/tareas/${tarea.id}`, { method: "DELETE" });
    mostrarMensaje("");
  } catch (error) {
    mostrarMensaje(error.message);
  }
  await cargar();
}

function abrirEdicion(tarea) {
  editandoId = tarea.id;
  document.getElementById("e-titulo").value = tarea.titulo;
  document.getElementById("e-descripcion").value = tarea.descripcion;
  document.getElementById("e-prioridad").value = tarea.prioridad;
  document.getElementById("e-fecha").value = tarea.fecha_limite || "";
  el.dialogo.showModal();
}

el.formNueva.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const datos = new FormData(el.formNueva);
  const cuerpo = {
    titulo: datos.get("titulo"),
    descripcion: datos.get("descripcion"),
    prioridad: datos.get("prioridad"),
    fecha_limite: datos.get("fecha_limite") || null,
  };
  try {
    await peticion("/api/tareas", { method: "POST", body: JSON.stringify(cuerpo) });
    el.formNueva.reset();
    mostrarMensaje("");
  } catch (error) {
    mostrarMensaje(error.message);
  }
  await cargar();
});

el.formEditar.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const cambios = {
    titulo: document.getElementById("e-titulo").value,
    descripcion: document.getElementById("e-descripcion").value,
    prioridad: document.getElementById("e-prioridad").value,
    fecha_limite: document.getElementById("e-fecha").value || null,
  };
  el.dialogo.close();
  await actualizar(editandoId, cambios);
});

el.cancelar.addEventListener("click", () => el.dialogo.close());

el.pestanas.addEventListener("click", (evento) => {
  const boton = evento.target.closest("button[data-estado]");
  if (!boton) return;
  estado.filtro = boton.dataset.estado;
  el.pestanas.querySelectorAll("button").forEach((b) => {
    b.setAttribute("aria-pressed", String(b === boton));
  });
  cargar();
});

el.filtroPrioridad.addEventListener("change", () => {
  estado.prioridad = el.filtroPrioridad.value;
  cargar();
});

el.busqueda.addEventListener("input", () => {
  clearTimeout(temporizadorBusqueda);
  temporizadorBusqueda = setTimeout(() => {
    estado.busqueda = el.busqueda.value.trim();
    cargar();
  }, 250);
});

cargar();
