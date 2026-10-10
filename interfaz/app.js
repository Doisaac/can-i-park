const API_ACCESO = "/api/acceso";
const API_DISPONIBILIDAD = "/api/disponibilidad";
const API_NOTIFICACIONES = "/api/notificaciones";
const PAUSA_VISUAL = 320;

const form = document.querySelector("#movimiento-form");
const placaInput = document.querySelector("#placa");
const mensaje = document.querySelector("#mensaje");
const botones = [...form.querySelectorAll("button[data-tipo]")];
const eventoBadge = document.querySelector("#evento-badge");

document.querySelector("#actualizar").addEventListener("click", actualizarPanelCompleto);

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const placa = placaInput.value.trim();
  if (!placa) return;

  const tipoSeleccionado = event.submitter?.dataset.tipo ?? "ENTRADA";

  bloquearFormulario(true);
  reiniciarRecorrido();

  let estadoAnterior = null;
  let alertaAnterior = null;

  try {
    [estadoAnterior, alertaAnterior] = await Promise.all([
      obtenerDisponibilidad(),
      obtenerUltimaAlerta(),
    ]);

    actualizarPaso(
      "acceso",
      "procesando",
      "Enviando placa y tipo al endpoint POST /movimientos...",
    );
    mostrarMensaje("Control de Acceso está recibiendo el movimiento...", "neutro");

    const respuesta = await fetch(`${API_ACCESO}/movimientos`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ placa, tipo: tipoSeleccionado }),
    });

    const cuerpo = await respuesta.json();

    if (!respuesta.ok) {
      actualizarPaso("acceso", "error", obtenerDetalleError(cuerpo));
      throw new Error(obtenerDetalleError(cuerpo));
    }

    actualizarPaso(
      "acceso",
      "completado",
      `${cuerpo.placa} · ${cuerpo.tipo}. Validación superada y solicitud aceptada con HTTP 202.`,
    );
    await esperar(PAUSA_VISUAL);

    eventoBadge.textContent = cuerpo.evento_id;
    eventoBadge.title = cuerpo.evento_id;

    actualizarPaso(
      "evento",
      "completado",
      `UUID: ${cuerpo.evento_id}. Este identificador permite rastrear el mismo movimiento.`,
    );
    await esperar(PAUSA_VISUAL);

    actualizarPaso(
      "kafka-movimiento",
      "completado",
      "Publicación confirmada por Acceso en el topic can-i-park.movimientos.",
    );
    await esperar(PAUSA_VISUAL);

    actualizarPaso(
      "disponibilidad",
      "procesando",
      "El consumidor está esperando o procesando el evento de Kafka...",
    );
    mostrarMensaje(
      `Evento ${cuerpo.evento_id.slice(0, 8)} publicado. Esperando a Disponibilidad...`,
      "neutro",
    );

    const resultado = await esperarResultado(cuerpo.evento_id);

    actualizarPaso(
      "disponibilidad",
      resultado.aceptado ? "completado" : "rechazado",
      `${resultado.motivo}. Ocupados: ${resultado.ocupados}; disponibles: ${resultado.disponibles}; estado: ${resultado.estado}.`,
    );
    await esperar(PAUSA_VISUAL);

    await resolverPasoNotificaciones({
      estadoAnterior,
      resultado,
      alertaAnterior,
    });

    mostrarMensaje(
      `${resultado.aceptado ? "Procesado" : "Rechazado"}: ${resultado.motivo}`,
      resultado.aceptado ? "exito" : "error",
    );

    placaInput.value = "";
    await actualizarPanelCompleto();
  } catch (error) {
    if (eventoBadge.textContent === "Procesando...") {
      eventoBadge.textContent = "Sin evento";
      eventoBadge.title = "";
    }

    marcarPasoActivoComoError(error.message || "No se pudo completar el flujo.");
    mostrarMensaje(error.message || "No se pudo completar el movimiento.", "error");
  } finally {
    bloquearFormulario(false);
  }
});

async function resolverPasoNotificaciones({ estadoAnterior, resultado, alertaAnterior }) {
  const cambioEstado =
    resultado.aceptado &&
    estadoAnterior &&
    estadoAnterior.estado !== resultado.estado;

  if (!cambioEstado) {
    actualizarPaso(
      "notificaciones",
      "omitido",
      "Sin cambio de estado: no se publica un evento en can-i-park.estados y Notificaciones no necesita intervenir.",
    );
    return;
  }

  if (resultado.estado === "DISPONIBLE") {
    actualizarPaso(
      "notificaciones",
      "completado",
      "El estado cambió a DISPONIBLE. El evento llega al servicio, pero por diseño no genera una alerta.",
    );
    return;
  }

  actualizarPaso(
    "notificaciones",
    "procesando",
    `Disponibilidad publicó el cambio ${estadoAnterior.estado} → ${resultado.estado} en can-i-park.estados.`,
  );

  const alertaNueva = await esperarNuevaAlerta(alertaAnterior, resultado.estado);

  if (alertaNueva) {
    actualizarPaso(
      "notificaciones",
      "alerta",
      `${alertaNueva.mensaje} Evento consumido desde can-i-park.estados.`,
    );
  } else {
    actualizarPaso(
      "notificaciones",
      "alerta",
      `El estado cambió a ${resultado.estado}; la alerta todavía no apareció dentro del tiempo de espera de la interfaz.`,
    );
  }
}

async function esperarResultado(eventoId) {
  for (let intento = 0; intento < 40; intento += 1) {
    const respuesta = await fetch(`${API_DISPONIBILIDAD}/movimientos/${eventoId}`);

    if (respuesta.ok) {
      return respuesta.json();
    }

    if (respuesta.status !== 404) {
      throw new Error("No fue posible consultar el resultado del evento.");
    }

    await esperar(250);
  }

  throw new Error("El evento fue recibido, pero tardó demasiado en procesarse.");
}

async function esperarNuevaAlerta(alertaAnterior, estadoEsperado) {
  const marcaAnterior = alertaAnterior?.ocurrido_en ?? null;

  for (let intento = 0; intento < 30; intento += 1) {
    const alerta = await obtenerUltimaAlerta();

    if (
      alerta &&
      alerta.estado === estadoEsperado &&
      alerta.ocurrido_en !== marcaAnterior
    ) {
      return alerta;
    }

    await esperar(250);
  }

  return null;
}

async function actualizarPanelCompleto() {
  try {
    const [estado, vehiculos, alertas] = await Promise.all([
      obtenerDisponibilidad(),
      obtenerVehiculos(),
      obtenerAlertas(),
    ]);

    pintarEstado(estado);
    pintarVehiculos(vehiculos);
    pintarAlertas(alertas, estado);
  } catch (error) {
    mostrarMensaje(error.message || "No se pudo actualizar el panel.", "error");
  }
}

async function obtenerDisponibilidad() {
  const respuesta = await fetch(`${API_DISPONIBILIDAD}/disponibilidad`);
  if (!respuesta.ok) {
    throw new Error("El servicio de Disponibilidad no respondió correctamente.");
  }
  return respuesta.json();
}

async function obtenerVehiculos() {
  const respuesta = await fetch(`${API_DISPONIBILIDAD}/vehiculos`);
  if (!respuesta.ok) {
    throw new Error("No fue posible consultar los vehículos.");
  }
  const cuerpo = await respuesta.json();
  return cuerpo.vehiculos;
}

async function obtenerAlertas() {
  const respuesta = await fetch(`${API_NOTIFICACIONES}/alertas`);
  if (!respuesta.ok) {
    throw new Error("El servicio de Notificaciones no respondió correctamente.");
  }
  const cuerpo = await respuesta.json();
  return cuerpo.alertas;
}

async function obtenerUltimaAlerta() {
  try {
    const alertas = await obtenerAlertas();
    return alertas[0] ?? null;
  } catch {
    return null;
  }
}

function pintarEstado(datos) {
  document.querySelector("#capacidad").textContent = datos.capacidad;
  document.querySelector("#ocupados").textContent = datos.ocupados;
  document.querySelector("#disponibles").textContent = datos.disponibles;

  const estado = document.querySelector("#estado");
  estado.textContent = datos.estado;
  estado.className = "estado";
  if (datos.estado === "POCOS_ESPACIOS") estado.classList.add("pocos");
  if (datos.estado === "LLENO") estado.classList.add("lleno");

  const porcentaje = datos.capacidad ? (datos.ocupados / datos.capacidad) * 100 : 0;
  const progreso = document.querySelector("#progreso");
  progreso.style.width = `${Math.min(porcentaje, 100)}%`;
  progreso.className = "progreso";
  if (datos.estado === "POCOS_ESPACIOS") progreso.classList.add("pocos");
  if (datos.estado === "LLENO") progreso.classList.add("lleno");
}

function pintarVehiculos(vehiculos) {
  const contenedor = document.querySelector("#vehiculos");
  document.querySelector("#total-vehiculos").textContent = vehiculos.length;

  if (!vehiculos.length) {
    contenedor.className = "vehiculos-vacio";
    contenedor.textContent = "No hay vehículos registrados.";
    return;
  }

  contenedor.className = "vehiculos-lista";
  contenedor.replaceChildren(...vehiculos.map((placa) => {
    const elemento = document.createElement("span");
    elemento.className = "placa";
    elemento.textContent = placa;
    return elemento;
  }));
}

function pintarAlertas(alertas, estadoActual) {
  const contenedor = document.querySelector("#alertas");
  const contador = document.querySelector("#total-alertas");

  if (estadoActual.estado === "DISPONIBLE") {
    contador.textContent = "0";
    contenedor.className = "alertas-vacio";
    contenedor.textContent = "Sin alertas activas.";
    return;
  }

  const visibles = alertas.slice(0, 2);
  contador.textContent = visibles.length;

  if (!visibles.length) {
    contenedor.className = "alertas-vacio";
    contenedor.textContent = "Esperando la alerta del microservicio...";
    return;
  }

  contenedor.className = "alertas-lista";
  contenedor.replaceChildren(...visibles.map((alerta) => {
    const item = document.createElement("div");
    item.className = `alerta-item ${alerta.estado === "LLENO" ? "lleno" : "pocos"}`;

    const titulo = document.createElement("strong");
    titulo.textContent = alerta.estado;

    const texto = document.createElement("p");
    texto.textContent = alerta.mensaje;

    const tiempo = document.createElement("time");
    tiempo.textContent = formatearFecha(alerta.ocurrido_en);

    item.append(titulo, texto, tiempo);
    return item;
  }));
}

function reiniciarRecorrido() {
  eventoBadge.textContent = "Procesando...";
  eventoBadge.title = "";

  const detallesIniciales = {
    acceso: "Esperando que el usuario registre un movimiento.",
    evento: "Se mostrará el UUID generado para rastrear el movimiento.",
    "kafka-movimiento": "Topic: can-i-park.movimientos",
    disponibilidad: "Esperando que el consumidor procese las reglas del dominio.",
    notificaciones: "Solo recibe un segundo evento si cambia el estado general.",
  };

  document.querySelectorAll(".paso").forEach((paso, indice) => {
    paso.className = "paso";
    paso.querySelector(".paso-icono").textContent = String(indice + 1);
    paso.querySelector(".paso-estado").textContent = "Pendiente";

    const nombre = paso.dataset.paso;
    const detalle = paso.querySelector(".paso-detalle");
    if (detalle && detallesIniciales[nombre]) {
      detalle.textContent = detallesIniciales[nombre];
    }
  });

  actualizarPaso("acceso", "procesando", "Preparando solicitud HTTP...");
}

function actualizarPaso(nombre, estado, detalle) {
  const paso = document.querySelector(`[data-paso="${nombre}"]`);
  if (!paso) return;

  paso.className = `paso ${estado}`;
  paso.querySelector(".paso-estado").textContent = nombreEstado(estado);
  paso.querySelector(".paso-detalle").textContent = detalle;
}

function marcarPasoActivoComoError(detalle) {
  const activo = document.querySelector(".paso.procesando");
  if (!activo) return;

  activo.className = "paso error";
  activo.querySelector(".paso-estado").textContent = "Error";
  activo.querySelector(".paso-detalle").textContent = detalle;
}

function nombreEstado(estado) {
  const nombres = {
    procesando: "Procesando",
    completado: "Confirmado",
    alerta: "Alerta",
    error: "Error",
    rechazado: "Rechazado",
    omitido: "Sin evento",
  };
  return nombres[estado] ?? "Pendiente";
}

function bloquearFormulario(bloqueado) {
  placaInput.disabled = bloqueado;
  botones.forEach((boton) => {
    boton.disabled = bloqueado;
  });
}

function mostrarMensaje(texto, tipo) {
  mensaje.textContent = texto;
  mensaje.className = `mensaje ${tipo}`;
}

function obtenerDetalleError(cuerpo) {
  if (typeof cuerpo?.detail === "string") return cuerpo.detail;

  if (Array.isArray(cuerpo?.detail) && cuerpo.detail[0]) {
    const error = cuerpo.detail[0];

    if (error.type === "string_too_short") {
      const minimo = error.ctx?.min_length ?? 3;
      return `La placa debe tener al menos ${minimo} caracteres.`;
    }

    if (error.type === "string_too_long") {
      const maximo = error.ctx?.max_length ?? 12;
      return `La placa no puede superar ${maximo} caracteres.`;
    }

    if (error.type === "missing") {
      return "La placa y el tipo de movimiento son obligatorios.";
    }

    if (typeof error.msg === "string") {
      return error.msg
        .replace("String should have at least", "La placa debe tener al menos")
        .replace("characters", "caracteres");
    }
  }

  return "La solicitud fue rechazada por el servicio.";
}

function formatearFecha(valor) {
  const fecha = new Date(valor);
  if (Number.isNaN(fecha.getTime())) return valor;
  return fecha.toLocaleString();
}

function esperar(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

actualizarPanelCompleto();
