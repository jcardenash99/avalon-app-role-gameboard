const socket = io();

let gameId = null;
let tuId = null;
let hostId = null;

function guardarSesion() {
    localStorage.setItem("avalon_game_id", gameId);
    localStorage.setItem("avalon_jugador_id", tuId);
}

function borrarSesion() {
    localStorage.removeItem("avalon_game_id");
    localStorage.removeItem("avalon_jugador_id");
}

// Al cargar la página, si veníamos de una partida en curso (recarga, red caída, etc.)
// intentamos reconectarnos automáticamente en vez de aparecer como jugador nuevo.
const sesionGuardada = {
    gameId: localStorage.getItem("avalon_game_id"),
    jugadorId: localStorage.getItem("avalon_jugador_id"),
};
if (sesionGuardada.gameId && sesionGuardada.jugadorId) {
    gameId = sesionGuardada.gameId;
    tuId = sesionGuardada.jugadorId;
    socket.emit("reconectar", { game_id: gameId, jugador_id: tuId });
}

const ROLES = {
    MERLIN: {
        titulo: "Merlín",
        descripcion: "El mago guarda el secreto del reino: conoces el rostro del mal, pero revelarlo con imprudencia puede costarte la vida."
    },
    PERCIVAL: {
        titulo: "Percival",
        descripcion: "Caballero leal que puede reconocer a Merlín entre las sombras, aunque la treta de Morgana puede confundir tu mirada."
    },
    LEAL: {
        titulo: "Leal a Arturo",
        descripcion: "Un servidor fiel del reino, sin dones especiales más que tu palabra y tu voto."
    },
    MORGANA: {
        titulo: "Morgana",
        descripcion: "Hechicera que se disfraza ante los ojos de Percival, sembrando la duda sobre quién es realmente Merlín."
    },
    MORDRED: {
        titulo: "Mordred",
        descripcion: "Tu presencia queda oculta incluso para Merlín: el mago no puede verte entre las sombras."
    },
    OBERON: {
        titulo: "Oberón",
        descripcion: "Actúas en solitario. Ni tus propios aliados saben quién eres, ni tú sabes quiénes son ellos."
    },
    SECUAZ: {
        titulo: "Secuaz de Mordred",
        descripcion: "Sirves a la oscuridad. Conoces a tus aliados y trabajas junto a ellos para sabotear el reino."
    },
    ASESINO: {
        titulo: "Asesino",
        descripcion: "Si el bien gana tres misiones, tendrás una última oportunidad: señala a Merlín y arrebátale la victoria."
    },
};

const INFO_TEXTO = {
    malo: "es del bando del mal",
    merlin_o_morgana: "es Merlín o Morgana (no puedes distinguir cuál)",
};

const MOTIVOS_FIN = {
    "3_exitos_asesino_falla": "El bien completó 3 misiones y el asesino no acertó su objetivo.",
    "asesino_acierta": "El asesino identificó correctamente a Merlín.",
    "3_fracasos": "El mal saboteó 3 misiones.",
    "5_rechazos": "Se rechazaron 5 propuestas de equipo seguidas.",
};

function renderizarCartaRol(estado) {
    const datosRol = ROLES[estado.tu_rol];
    if (!datosRol) return;

    document.getElementById("carta-bando").textContent = estado.tu_bando;
    document.getElementById("carta-bando").className = `carta-bando ${estado.tu_bando}`;
    document.getElementById("carta-titulo").textContent = datosRol.titulo;
    document.getElementById("carta-descripcion").textContent = datosRol.descripcion;

    const visibles = (estado.jugadores_visibles || []).filter(j => j.info);
    const infoDiv = document.getElementById("carta-info");
    const lista = document.getElementById("carta-info-lista");
    if (visibles.length > 0) {
        lista.innerHTML = visibles
            .map(j => `<li><strong>${j.nombre}</strong> ${INFO_TEXTO[j.info] || ""}</li>`)
            .join("");
        infoDiv.style.display = "block";
    } else {
        infoDiv.style.display = "none";
    }

    // Reset por si ya se había revelado antes (ej. al reconectar)
    document.getElementById("rol-reveal").classList.remove("revelado");
    document.getElementById("sello").classList.remove("activado");
}

document.getElementById("sello").addEventListener("click", function () {
    this.classList.add("activado");
    setTimeout(() => {
        document.getElementById("rol-reveal").classList.add("revelado");
    }, 450);
});

document.getElementById("btn-continuar-rol").addEventListener("click", function () {
    this.disabled = true;
    this.textContent = "Esperando a los demás...";
    socket.emit("listo_para_ronda", { game_id: gameId, jugador_id: tuId });
});

socket.on("roles:progreso", (data) => {
    const btn = document.getElementById("btn-continuar-rol");
    if (btn.disabled) {
        btn.textContent = `Esperando a los demás... (${data.confirmados}/${data.total})`;
    }
});

let ultimoEstado = null;
let seleccionActual = new Set();

function mostrarSubvista(id) {
    ["vista-rol", "vista-seleccion", "vista-asesinato", "vista-fin"].forEach(v => {
        document.getElementById(v).style.display = (v === id) ? "block" : "none";
    });
}

function renderizarRechazos(intentos) {
    const contenedor = document.getElementById("rechazos-tally");
    contenedor.innerHTML = "";
    for (let i = 0; i < 5; i++) {
        const punto = document.createElement("span");
        punto.className = "rechazo-punto" + (i < intentos ? " usado" : "");
        contenedor.appendChild(punto);
    }
}

function renderizarHistorialMisiones(historial) {
    const contenedor = document.getElementById("historial-misiones");
    contenedor.innerHTML = (historial || [])
        .map(resultado => `<span class="mision-marca ${resultado}"></span>`)
        .join("");
}

function iniciales(nombre) {
    return nombre.trim().slice(0, 2).toUpperCase();
}

function renderizarVistaSeleccion(estado) {
    ultimoEstado = estado;
    seleccionActual = new Set();

    document.getElementById("ronda-numero-actual").textContent = estado.ronda_actual;
    document.getElementById("ronda-requeridos").textContent = estado.jugadores_requeridos;
    document.getElementById("contador-requeridos").textContent = estado.jugadores_requeridos;
    document.getElementById("contador-elegidos").textContent = "0";
    renderizarRechazos(estado.intentos_fallidos_ronda);
    renderizarHistorialMisiones(estado.historial_resultados);

    document.getElementById("votacion-equipo").style.display = "none";
    document.getElementById("resultado-votacion").style.display = "none";
    document.getElementById("mision-espera-placeholder").style.display = "none";
    document.getElementById("votacion-mision").style.display = "none";
    document.getElementById("mision-espera").style.display = "none";
    document.getElementById("mision-resultado").style.display = "none";
    document.getElementById("mision-resultado").style.backgroundColor = "";
    document.getElementById("lider-seleccion").style.display = "none";
    document.getElementById("espera-lider").style.display = "none";

    const soyLider = (tuId === estado.lider_id);
    const lider = estado.jugadores.find(j => j.id === estado.lider_id);

    if (soyLider) {
        document.getElementById("lider-seleccion").style.display = "block";
        renderizarChips(estado.jugadores, estado.jugadores_requeridos);
    } else {
        document.getElementById("espera-lider").style.display = "block";
        document.getElementById("nombre-lider").textContent = lider ? lider.nombre : "";
    }

    mostrarSubvista("vista-seleccion");
}

function renderizarChips(jugadores, requeridos) {
    const contenedor = document.getElementById("lista-chips");
    contenedor.innerHTML = jugadores.map(j => `
        <div class="chip-jugador" data-id="${j.id}">
            <div class="avatar">${iniciales(j.nombre)}</div>
            <div class="nombre-chip">${j.nombre}</div>
        </div>
    `).join("");

    contenedor.querySelectorAll(".chip-jugador").forEach(chip => {
        chip.addEventListener("click", () => {
            const id = chip.dataset.id;
            if (seleccionActual.has(id)) {
                seleccionActual.delete(id);
                chip.classList.remove("seleccionado");
            } else if (seleccionActual.size < requeridos) {
                seleccionActual.add(id);
                chip.classList.add("seleccionado");
            }
            actualizarContadorSeleccion(requeridos);
        });
    });
}

function actualizarContadorSeleccion(requeridos) {
    document.getElementById("contador-elegidos").textContent = seleccionActual.size;
    document.getElementById("btn-proponer").disabled = (seleccionActual.size !== requeridos);

    const completo = seleccionActual.size >= requeridos;
    document.querySelectorAll(".chip-jugador").forEach(chip => {
        const yaElegido = chip.classList.contains("seleccionado");
        chip.classList.toggle("bloqueado", completo && !yaElegido);
    });
}

document.getElementById("btn-proponer").addEventListener("click", () => {
    socket.emit("proponer_equipo", {
        game_id: gameId,
        jugadores_ids: Array.from(seleccionActual),
    });
});

function log(mensaje) {
    const div = document.getElementById("mensajes");
    div.innerHTML = `<p>${mensaje}</p>` + div.innerHTML;
}

function mostrarPantalla(id) {
    ["pantalla-join", "pantalla-lobby", "pantalla-juego"].forEach(p => {
        document.getElementById(p).style.display = (p === id) ? "block" : "none";
    });
    if (id === "pantalla-juego") {
        document.getElementById("control-host").style.display =
            (tuId !== null && tuId === hostId) ? "block" : "none";
    }
}

document.getElementById("btn-forzar-lobby").addEventListener("click", () => {
    if (confirm("¿Forzar el regreso de todos los jugadores a la sala de espera? Esto interrumpe la ronda actual.")) {
        socket.emit("forzar_lobby", { game_id: gameId, jugador_id: tuId });
    }
});

document.getElementById("btn-unirse").addEventListener("click", () => {
    const nombre = document.getElementById("input-nombre").value;
    const game_id = document.getElementById("input-game-id").value.toUpperCase() || null;
    socket.emit("join_game", { game_id, nombre_jugador: nombre });
});

document.getElementById("input-game-id").addEventListener("input", function () {
    this.value = this.value.toUpperCase();
});

document.getElementById("btn-config").addEventListener("click", () => {
    const preset = document.getElementById("select-preset").value;
    socket.emit("set_config", { game_id: gameId, jugador_id: tuId, preset });
});

document.getElementById("btn-iniciar").addEventListener("click", () => {
    socket.emit("start_game", { game_id: gameId, jugador_id: tuId });
});

socket.on("lobby:bienvenida", (data) => {
    gameId = data.game_id;
    tuId = data.tu_id;
    guardarSesion();
    actualizarControlesHost();
});

function renderizarListaJugadores(jugadores) {
    const soyHost = (tuId !== null && tuId === hostId);
    document.getElementById("lista-jugadores").innerHTML = jugadores.map(j => {
        const etiquetaHost = j.id === hostId ? " (host)" : "";
        const botonExpulsar = (soyHost && j.id !== hostId)
            ? `<button class="btn-expulsar" data-id="${j.id}" data-nombre="${j.nombre}">Expulsar</button>`
            : "";
        return `<li><span>${j.nombre}${etiquetaHost}</span>${botonExpulsar}</li>`;
    }).join("");

    document.querySelectorAll(".btn-expulsar").forEach(btn => {
        btn.addEventListener("click", () => {
            if (confirm(`¿Expulsar a ${btn.dataset.nombre}?`)) {
                socket.emit("expulsar_jugador", {
                    game_id: gameId,
                    jugador_id: tuId,
                    objetivo_id: btn.dataset.id,
                });
            }
        });
    });
}

socket.on("lobby:jugador_unido", (data) => {
    gameId = data.game_id;
    hostId = data.host_id;
    document.getElementById("codigo-sala").textContent = gameId;
    renderizarListaJugadores(data.jugadores);
    mostrarPantalla("pantalla-lobby");
    actualizarControlesHost();
    if (data.jugador_nuevo) {
        log(`${data.jugador_nuevo} se unió a la sala ${gameId}`);
    }
});

function actualizarControlesHost() {
    const esHost = (tuId !== null && tuId === hostId);
    document.getElementById("select-preset").style.display = esHost ? "block" : "none";
    document.getElementById("btn-config").style.display = esHost ? "block" : "none";
    document.getElementById("btn-iniciar").style.display = esHost ? "block" : "none";
}

socket.on("lobby:config_actualizada", (data) => {
    log(`Configuración: ${data.preset} (${data.num_jugadores} jugadores)`);
});

socket.on("lobby:error", (data) => {
    log(`⚠️ ${data.mensaje}`);
});

socket.on("reconexion:exitosa", (data) => {
    gameId = data.game_id;
    hostId = data.host_id;
    guardarSesion();
    log("Te reconectaste a tu partida.");
    // Si ningún otro evento de fase llega después (ej. estamos en LOBBY), mostramos el lobby
    document.getElementById("codigo-sala").textContent = gameId;
    renderizarListaJugadores(data.jugadores);
    mostrarPantalla("pantalla-lobby");
    actualizarControlesHost();
});

socket.on("lobby:reconexion_fallida", (data) => {
    borrarSesion();
    log(`No se pudo reconectar: ${data.mensaje}`);
});

socket.on("jugador:reconectado", (data) => {
    log(`${data.nombre} se reconectó.`);
});

socket.on("jugador:desconectado", (data) => {
    log(`${data.nombre} se desconectó.`);
});

socket.on("lobby:fuiste_expulsado", () => {
    borrarSesion();
    alert("El host te expulsó de la sala.");
    location.reload();
});

socket.on("game:estado", (data) => {
    tuId = data.tu_id;
    mostrarPantalla("pantalla-juego");
    mostrarSubvista("vista-rol");
    document.getElementById("debug-estado").textContent = JSON.stringify(data, null, 2);
    renderizarCartaRol(data);
    const btn = document.getElementById("btn-continuar-rol");
    btn.disabled = false;
    btn.textContent = "Continuar a la ronda";
    log(`Tu rol: ${data.tu_rol} (${data.tu_bando})`);
});

socket.on("ronda:nueva", (data) => {
    mostrarPantalla("pantalla-juego");
    document.getElementById("debug-estado").textContent = JSON.stringify(data, null, 2);
    renderizarVistaSeleccion(data);
    log(`Ronda ${data.ronda_actual} - líder: ${data.lider_id}`);
});

socket.on("equipo:propuesto", (data) => {
    const nombres = (ultimoEstado ? ultimoEstado.jugadores : [])
        .filter(j => data.jugadores_ids.includes(j.id))
        .map(j => j.nombre);

    document.getElementById("lider-seleccion").style.display = "none";
    document.getElementById("espera-lider").style.display = "none";
    document.getElementById("resultado-votacion").style.display = "none";
    document.getElementById("mision-espera-placeholder").style.display = "none";

    document.getElementById("nombres-equipo-propuesto").textContent =
        nombres.length ? nombres.join(", ") : data.jugadores_ids.join(", ");

    const btnAprobar = document.getElementById("btn-aprobar");
    const btnRechazar = document.getElementById("btn-rechazar");
    btnAprobar.disabled = false;
    btnRechazar.disabled = false;
    document.getElementById("voto-estado").style.display = "none";
    document.getElementById("votacion-equipo").style.display = "block";

    log(`Equipo propuesto: ${nombres.length ? nombres.join(", ") : data.jugadores_ids.join(", ")}`);
});

function votarEquipo(aprueba) {
    document.getElementById("btn-aprobar").disabled = true;
    document.getElementById("btn-rechazar").disabled = true;
    const estado = document.getElementById("voto-estado");
    estado.style.display = "block";
    estado.textContent = "Voto registrado. Esperando a los demás...";
    socket.emit("votar_equipo", { game_id: gameId, jugador_id: tuId, aprueba });
}

document.getElementById("btn-aprobar").addEventListener("click", () => votarEquipo(true));
document.getElementById("btn-rechazar").addEventListener("click", () => votarEquipo(false));

socket.on("equipo:voto_registrado", (data) => {
    const estado = document.getElementById("voto-estado");
    if (estado.style.display === "block") {
        estado.textContent = `Voto registrado. Esperando a los demás... (${data.votos_registrados}/${data.total})`;
    }
});

socket.on("equipo:resultado", (data) => {
    document.getElementById("votacion-equipo").style.display = "none";

    const texto = document.getElementById("resultado-votacion-texto");
    const lista = document.getElementById("resultado-votacion-detalle");

    // Solo el titular, en suspenso — el detalle lo manda el servidor después (equipo:resultado_detalle)
    texto.textContent = data.aprobado ? "Equipo elegido" : "Equipo rechazado, cambio de líder";
    texto.style.color = data.aprobado ? "var(--steel)" : "var(--crimson)";
    lista.style.display = "none";
    lista.innerHTML = "";
    document.getElementById("resultado-votacion").style.display = "block";

    log(`Equipo ${data.aprobado ? "aprobado" : "rechazado"} (${data.votos_a_favor} a favor, ${data.votos_en_contra} en contra)`);
});

socket.on("equipo:resultado_detalle", (data) => {
    const nombresPorId = {};
    (ultimoEstado ? ultimoEstado.jugadores : []).forEach(j => { nombresPorId[j.id] = j.nombre; });

    const texto = document.getElementById("resultado-votacion-texto");
    const lista = document.getElementById("resultado-votacion-detalle");

    texto.textContent = data.aprobado
        ? `Equipo aprobado (${data.votos_a_favor} a favor, ${data.votos_en_contra} en contra)`
        : `Equipo rechazado (${data.votos_a_favor} a favor, ${data.votos_en_contra} en contra)`;

    lista.innerHTML = Object.entries(data.detalle_por_jugador).map(([id, aprueba]) => `
        <li>
            <span>${nombresPorId[id] || id}</span>
            <span class="${aprueba ? "voto-si" : "voto-no"}">${aprueba ? "Aprobó" : "Rechazó"}</span>
        </li>
    `).join("");
    lista.style.display = "block";
});

socket.on("mision:en_curso", (data) => {
    document.getElementById("resultado-votacion").style.display = "none";

    const soyDelEquipo = data.jugadores_en_mision.includes(tuId);

    if (soyDelEquipo) {
        document.getElementById("btn-mision-exito").disabled = false;
        document.getElementById("btn-mision-fracaso").disabled = false;
        document.getElementById("mision-voto-estado").style.display = "none";
        document.getElementById("votacion-mision").style.display = "block";
        document.getElementById("mision-espera").style.display = "none";
    } else {
        document.getElementById("votacion-mision").style.display = "none";
        document.getElementById("mision-espera").style.display = "block";
    }

    log(`Misión en curso con: ${data.jugadores_en_mision.join(", ")}`);
});

function votarMision(exito) {
    document.getElementById("btn-mision-exito").disabled = true;
    document.getElementById("btn-mision-fracaso").disabled = true;
    const estado = document.getElementById("mision-voto-estado");
    estado.style.display = "block";
    estado.textContent = "Voto registrado. Esperando a los demás...";
    socket.emit("votar_mision", { game_id: gameId, jugador_id: tuId, exito });
}

document.getElementById("btn-mision-exito").addEventListener("click", () => votarMision(true));
document.getElementById("btn-mision-fracaso").addEventListener("click", () => votarMision(false));

socket.on("mision:voto_registrado", (data) => {
    const estado = document.getElementById("mision-voto-estado");
    if (estado.style.display === "block") {
        estado.textContent = `Voto registrado. Esperando a los demás... (${data.votos_registrados}/${data.total})`;
    }
});

let ultimoTally = { bien: 0, mal: 0 };

socket.on("game:estado_general", (data) => {
    ultimoTally.bien = data.misiones_ganadas_bien;
    ultimoTally.mal = data.misiones_ganadas_mal;
});

socket.on("mision:resultado", (data) => {
    document.getElementById("votacion-mision").style.display = "none";
    document.getElementById("mision-espera").style.display = "none";

    const contenedor = document.getElementById("mision-resultado");
    const texto = document.getElementById("mision-resultado-texto");
    const detalle = document.getElementById("mision-resultado-detalle");
    const tally = document.getElementById("mision-resultado-tally");

    // Solo el suspenso — el detalle lo manda el servidor después (mision:resultado_detalle)
    contenedor.style.backgroundColor = "";
    texto.textContent = "La misión fue...";
    texto.style.color = "var(--gold)";
    detalle.textContent = "";
    tally.textContent = "";
    contenedor.style.display = "block";

    log(`Resultado de misión: ${data.resultado}` +
        (data.conteo_fracasos !== null ? ` (${data.conteo_fracasos} fracasos)` : ""));
});

socket.on("mision:resultado_detalle", (data) => {
    const contenedor = document.getElementById("mision-resultado");
    const texto = document.getElementById("mision-resultado-texto");
    const detalle = document.getElementById("mision-resultado-detalle");
    const tally = document.getElementById("mision-resultado-tally");

    const esExito = data.resultado === "EXITO";
    contenedor.style.backgroundColor = esExito ? "var(--steel)" : "var(--crimson)";
    texto.textContent = esExito ? "Un éxito" : "Un fracaso";
    texto.style.color = "#f2ede0";
    detalle.style.color = "#f2ede0";
    detalle.textContent = (data.conteo_fracasos !== null)
        ? `${data.conteo_fracasos} voto(s) de fracaso`
        : "";
    tally.style.color = "#f2ede0";
    tally.textContent = `Éxitos: ${ultimoTally.bien} — Fracasos: ${ultimoTally.mal}`;
});

let seleccionadoAsesinato = null;

socket.on("game:fase_asesinato", (data) => {
    mostrarPantalla("pantalla-juego");
    mostrarSubvista("vista-asesinato");
    seleccionadoAsesinato = null;

    const soyAsesino = (tuId === data.asesino_id);
    document.getElementById("asesino-seleccion").style.display = soyAsesino ? "block" : "none";
    document.getElementById("asesinato-espera").style.display = soyAsesino ? "none" : "block";

    if (soyAsesino) {
        renderizarChipsAsesinato(data.candidatos);
    }

    log(`Fase de asesinato. Asesino: ${data.asesino_id}`);
});

function renderizarChipsAsesinato(candidatoIds) {
    const nombresPorId = {};
    (ultimoEstado ? ultimoEstado.jugadores : []).forEach(j => { nombresPorId[j.id] = j.nombre; });

    const contenedor = document.getElementById("lista-chips-asesinato");
    contenedor.innerHTML = candidatoIds.map(id => `
        <div class="chip-jugador" data-id="${id}">
            <div class="avatar">${iniciales(nombresPorId[id] || "?")}</div>
            <div class="nombre-chip">${nombresPorId[id] || id}</div>
        </div>
    `).join("");

    contenedor.querySelectorAll(".chip-jugador").forEach(chip => {
        chip.addEventListener("click", () => {
            contenedor.querySelectorAll(".chip-jugador").forEach(c => c.classList.remove("seleccionado"));
            chip.classList.add("seleccionado");
            seleccionadoAsesinato = chip.dataset.id;
            document.getElementById("btn-asesinar").disabled = false;
        });
    });
}

document.getElementById("btn-asesinar").addEventListener("click", () => {
    if (!seleccionadoAsesinato) return;
    document.getElementById("btn-asesinar").disabled = true;
    socket.emit("asesinar", { game_id: gameId, objetivo_id: seleccionadoAsesinato });
});

socket.on("game:resultado_asesinato", (data) => {
    log(`Asesinato: ${data.era_merlin ? "¡Era Merlín!" : "No era Merlín"}`);
});

socket.on("game:fin", (data) => {
    mostrarPantalla("pantalla-juego");
    mostrarSubvista("vista-fin");

    const titulo = document.getElementById("fin-titulo");
    if (data.ganador === "MALO") {
        titulo.textContent = "Gana Mordred y sus secuaces";
        titulo.style.color = "var(--crimson)";
    } else {
        titulo.textContent = "Gana Arturo y sus caballeros";
        titulo.style.color = "var(--steel)";
    }
    document.getElementById("fin-motivo").textContent = MOTIVOS_FIN[data.motivo] || "";

    const lista = document.getElementById("fin-roles");
    lista.innerHTML = data.revelar_roles.map(j => {
        const datosRol = ROLES[j.rol];
        const nombreRol = datosRol ? datosRol.titulo : j.rol;
        return `<li><span>${j.nombre}</span><span class="${j.bando === "BUENO" ? "voto-si" : "voto-no"}">${nombreRol}</span></li>`;
    }).join("");

    log(`FIN DEL JUEGO. Ganador: ${data.ganador}`);
});

document.getElementById("btn-volver-lobby").addEventListener("click", () => {
    socket.emit("volver_a_lobby", { game_id: gameId });
});

socket.on("lobby:reiniciado", (data) => {
    clearInterval(temporizadorPausa);
    document.getElementById("banner-pausa").style.display = "none";
    hostId = data.host_id;
    document.getElementById("codigo-sala").textContent = gameId;
    renderizarListaJugadores(data.jugadores);
    mostrarPantalla("pantalla-lobby");
    actualizarControlesHost();
    log("La partida volvió a la sala de espera.");
});

let temporizadorPausa = null;

socket.on("game:pausado", (data) => {
    const banner = document.getElementById("banner-pausa");
    banner.style.display = "block";

    let segundos = data.segundos_espera || 60;
    const actualizarTexto = () => {
        banner.textContent = `⏸ Partida en pausa: un jugador se desconectó. Si no vuelve en ${segundos}s, todos regresan a la sala.`;
    };
    actualizarTexto();

    clearInterval(temporizadorPausa);
    temporizadorPausa = setInterval(() => {
        segundos -= 1;
        if (segundos <= 0) {
            clearInterval(temporizadorPausa);
            banner.textContent = "⏸ Partida en pausa: volviendo a la sala...";
            return;
        }
        actualizarTexto();
    }, 1000);
});

socket.on("game:reanudado", () => {
    clearInterval(temporizadorPausa);
    document.getElementById("banner-pausa").style.display = "none";
});
