"""
Handlers de Socket.IO. Cada función acá corresponde a un evento
del catálogo que diseñamos. La convención:
  - eventos que el cliente manda: nombres simples ("join_game", "votar_equipo")
  - eventos que el servidor emite: "namespace:accion" ("lobby:jugador_unido")
"""
from flask import request
from flask_socketio import join_room, emit
import random

from backend import store
from backend.models.player import Player
from backend.models.game import GameConfig, Fase
from backend.models.roles import Preset
from backend.game import role_assignment, game_logic


def emitir_vistas_privadas(socketio, game):
    """Manda a cada jugador conectado SU PROPIA vista del estado (rol incluido)."""
    for jugador in game.jugadores:
        if jugador.sid:
            socketio.emit("game:estado", game.vista_jugador(jugador.id), room=jugador.sid)


def registrar_handlers(socketio):

    @socketio.on("join_game")
    def on_join_game(data):
        game_id = (data.get("game_id") or "").strip().upper() or None
        nombre = data.get("nombre_jugador", "").strip()

        if not nombre:
            emit("lobby:error", {"mensaje": "Escribe un nombre para unirte."})
            return

        if game_id:
            game = store.obtener_partida(game_id)
            if game is None:
                emit("lobby:error", {
                    "mensaje": f"La sala '{game_id}' no existe. Verifica el código, o déjalo vacío para crear una sala nueva.",
                })
                return
            if game.fase_actual != Fase.LOBBY:
                emit("lobby:error", {
                    "mensaje": "Esa partida ya comenzó. Si ya estabas jugando, recarga la página para reconectarte automáticamente.",
                })
                return
        else:
            game = store.crear_partida()

        jugador = Player(nombre=nombre, sid=request.sid)
        game.jugadores.append(jugador)

        if game.host_id is None:
            game.host_id = jugador.id

        join_room(game.id)

        # Confirmación PRIVADA solo para quien se acaba de unir (su propio tu_id)
        emit("lobby:bienvenida", {
            "game_id": game.id,
            "tu_id": jugador.id,
        }, room=request.sid)

        # Broadcast a TODA la sala con la lista actualizada (sin tu_id)
        emit("lobby:jugador_unido", {
            "game_id": game.id,
            "host_id": game.host_id,
            "jugador_nuevo": jugador.nombre,
            "jugadores": [j.to_public_dict() for j in game.jugadores],
        }, room=game.id)

    @socketio.on("set_config")
    def on_set_config(data):
        game_id = data.get("game_id")
        game = store.obtener_partida(game_id)
        if game is None:
            return

        if not game.es_host(data.get("jugador_id")):
            emit("lobby:error", {"mensaje": "Solo el host puede cambiar la configuración."})
            return

        game.config = GameConfig(
            preset=Preset(data.get("preset", "CLASICO")),
            num_jugadores=len(game.jugadores),
        )
        valido, mensaje = game.config.es_valido()
        if not valido:
            emit("lobby:error", {"mensaje": mensaje})
            return

        emit("lobby:config_actualizada", {
            "preset": game.config.preset.value,
            "num_jugadores": game.config.num_jugadores,
        }, room=game.id)

    @socketio.on("start_game")
    def on_start_game(data):
        game_id = data.get("game_id")
        game = store.obtener_partida(game_id)
        if game is None:
            return

        if not game.es_host(data.get("jugador_id")):
            emit("lobby:error", {"mensaje": "Solo el host puede iniciar la partida."})
            return

        # Recalculamos con el conteo REAL de jugadores conectados ahora mismo,
        # sin confiar en el valor que se haya guardado antes con set_config
        game.config.num_jugadores = len(game.jugadores)
        valido, mensaje = game.config.es_valido()
        if not valido:
            emit("lobby:error", {"mensaje": mensaje})
            return

        role_assignment.asignar_roles(game)
        game.inicializar_misiones()
        game.fase_actual = Fase.ASIGNACION_ROLES
        game.jugadores_confirmados_rol = set()
        game.lider_actual_index = random.randrange(len(game.jugadores))

        emitir_vistas_privadas(socketio, game)
        emit("roles:progreso", {
            "confirmados": 0,
            "total": len(game.jugadores),
        }, room=game.id)

    @socketio.on("listo_para_ronda")
    def on_listo_para_ronda(data):
        game = store.obtener_partida(data.get("game_id"))
        if game is None:
            return

        jugador_id = data.get("jugador_id")
        game.jugadores_confirmados_rol.add(jugador_id)

        emit("roles:progreso", {
            "confirmados": len(game.jugadores_confirmados_rol),
            "total": len(game.jugadores),
        }, room=game.id)

        if len(game.jugadores_confirmados_rol) >= len(game.jugadores):
            game_logic.iniciar_ronda(game)
            emit("ronda:nueva", game.estado_publico(), room=game.id)

    @socketio.on("proponer_equipo")
    def on_proponer_equipo(data):
        game = store.obtener_partida(data.get("game_id"))
        if game is None:
            return
        ok, mensaje = game_logic.proponer_equipo(game, data.get("jugadores_ids", []))
        if not ok:
            emit("lobby:error", {"mensaje": mensaje})
            return
        emit("equipo:propuesto", {
            "jugadores_ids": game.mision_actual().equipo_propuesto
        }, room=game.id)

    @socketio.on("votar_equipo")
    def on_votar_equipo(data):
        game = store.obtener_partida(data.get("game_id"))
        if game is None:
            return
        jugador = game.get_jugador(data.get("jugador_id"))
        if jugador is None:
            return

        game_logic.registrar_voto_equipo(game, jugador.id, data.get("aprueba", False))
        emit("equipo:voto_registrado", {
            "jugador_id": jugador.id,
            "votos_registrados": len(game.mision_actual().votos_equipo),
            "total": len(game.jugadores),
        }, room=game.id)

        if game_logic.todos_votaron_equipo(game):
            resumen = game_logic.resolver_votacion_equipo(game)
            emit("equipo:resultado", resumen, room=game.id)
            socketio.start_background_task(_continuar_tras_equipo, socketio, game)

    @socketio.on("votar_mision")
    def on_votar_mision(data):
        game = store.obtener_partida(data.get("game_id"))
        if game is None:
            return
        jugador = game.get_jugador(data.get("jugador_id"))
        if jugador is None:
            return

        game_logic.registrar_voto_mision(game, jugador.id, data.get("exito", True))
        emit("mision:voto_registrado", {
            "jugador_id": jugador.id,
            "votos_registrados": len(game.mision_actual().votos_mision),
            "total": len(game.mision_actual().equipo_propuesto),
        }, room=game.id)

        if game_logic.todos_votaron_mision(game):
            resumen = game_logic.resolver_votacion_mision(game)
            emit("mision:resultado", resumen, room=game.id)
            emit("game:estado_general", game.estado_publico(), room=game.id)

            game_logic.avanzar_despues_de_resultado(game)
            socketio.start_background_task(_continuar_tras_mision, socketio, game)

    @socketio.on("asesinar")
    def on_asesinar(data):
        game = store.obtener_partida(data.get("game_id"))
        if game is None:
            return
        resumen = game_logic.resolver_asesinato(game, data.get("objetivo_id"))
        emit("game:resultado_asesinato", resumen, room=game.id)
        emit("game:fin", _payload_fin_juego(game), room=game.id)

    @socketio.on("volver_a_lobby")
    def on_volver_a_lobby(data):
        game = store.obtener_partida(data.get("game_id"))
        if game is None:
            return
        _forzar_regreso_a_lobby(socketio, game)

    @socketio.on("forzar_lobby")
    def on_forzar_lobby(data):
        game = store.obtener_partida(data.get("game_id"))
        if game is None:
            return
        if not game.es_host(data.get("jugador_id")):
            emit("lobby:error", {"mensaje": "Solo el host puede forzar el regreso a la sala."})
            return
        _forzar_regreso_a_lobby(socketio, game)

    @socketio.on("reconectar")
    def on_reconectar(data):
        game = store.obtener_partida(data.get("game_id"))
        if game is None:
            emit("lobby:reconexion_fallida", {"mensaje": "La sala ya no existe en el servidor."})
            return

        jugador = game.get_jugador(data.get("jugador_id"))
        if jugador is None:
            emit("lobby:reconexion_fallida", {"mensaje": "No se encontró tu jugador en esa sala."})
            return

        jugador.sid = request.sid
        jugador.conectado = True
        join_room(game.id)

        # Confirmación privada solo para quien se reconecta
        emit("reconexion:exitosa", {
            "game_id": game.id,
            "host_id": game.host_id,
            "jugadores": [j.to_public_dict() for j in game.jugadores],
        }, room=request.sid)

        # Aviso informativo al resto (no fuerza cambio de pantalla en nadie)
        emit("jugador:reconectado", {"jugador_id": jugador.id, "nombre": jugador.nombre}, room=game.id)

        if game.pausado and all(j.conectado for j in game.jugadores):
            game.pausado = False
            game.jugador_desconectado_id = None
            emit("game:reanudado", {}, room=game.id)

        if game.fase_actual == Fase.LOBBY:
            emit("lobby:jugador_unido", {
                "game_id": game.id,
                "host_id": game.host_id,
                "jugadores": [j.to_public_dict() for j in game.jugadores],
            }, room=game.id)
        else:
            _reenviar_estado_actual(socketio, game, jugador)

    @socketio.on("expulsar_jugador")
    def on_expulsar_jugador(data):
        game = store.obtener_partida(data.get("game_id"))
        if game is None:
            return

        if not game.es_host(data.get("jugador_id")):
            emit("lobby:error", {"mensaje": "Solo el host puede expulsar jugadores."})
            return

        if game.fase_actual != Fase.LOBBY:
            emit("lobby:error", {"mensaje": "No puedes expulsar jugadores durante la partida."})
            return

        objetivo_id = data.get("objetivo_id")
        jugador = game.get_jugador(objetivo_id)
        if jugador is None:
            return

        game.jugadores = [j for j in game.jugadores if j.id != objetivo_id]

        if jugador.sid:
            emit("lobby:fuiste_expulsado", {}, room=jugador.sid)

        emit("lobby:jugador_unido", {
            "game_id": game.id,
            "host_id": game.host_id,
            "jugadores": [j.to_public_dict() for j in game.jugadores],
        }, room=game.id)

    @socketio.on("disconnect")
    def on_disconnect():
        for game in store.games.values():
            jugador = next((j for j in game.jugadores if j.sid == request.sid), None)
            if jugador:
                jugador.conectado = False
                game.pausado = True
                game.jugador_desconectado_id = jugador.id
                emit("jugador:desconectado", {"jugador_id": jugador.id, "nombre": jugador.nombre}, room=game.id)
                emit("game:pausado", {
                    "motivo": "jugador_desconectado",
                    "jugador_id": jugador.id,
                    "segundos_espera": SEGUNDOS_ESPERA_PAUSA,
                }, room=game.id)
                _iniciar_temporizador_pausa(socketio, game.id, jugador.id)
                break


def _reenviar_estado_actual(socketio, game, jugador):
    """
    Cuando alguien se reconecta a mitad de partida, le reenviamos (solo a él)
    los eventos necesarios para que su pantalla quede igual que la de los demás.
    """
    sid = jugador.sid

    if game.fase_actual == Fase.ASIGNACION_ROLES:
        socketio.emit("game:estado", game.vista_jugador(jugador.id), room=sid)
        socketio.emit("roles:progreso", {
            "confirmados": len(game.jugadores_confirmados_rol),
            "total": len(game.jugadores),
        }, room=sid)
        return

    # A partir de aquí el rol ya se reveló para todos; reenviamos el estado base de la ronda
    socketio.emit("ronda:nueva", game.estado_publico(), room=sid)

    if not game.historial_misiones or game.ronda_actual >= len(game.historial_misiones):
        return
    mision = game.mision_actual()

    if game.fase_actual == Fase.VOTACION_EQUIPO:
        socketio.emit("equipo:propuesto", {"jugadores_ids": mision.equipo_propuesto}, room=sid)
    elif game.fase_actual == Fase.VOTACION_MISION:
        socketio.emit("mision:en_curso", {"jugadores_en_mision": mision.equipo_propuesto}, room=sid)
    elif game.fase_actual == Fase.ASESINATO:
        socketio.emit("game:fase_asesinato", {
            "asesino_id": game.asesino_id,
            "candidatos": [j.id for j in game.jugadores if j.bando.value == "BUENO"],
        }, room=sid)
    elif game.fase_actual == Fase.FIN_JUEGO:
        socketio.emit("game:fin", _payload_fin_juego(game), room=sid)


def _forzar_regreso_a_lobby(socketio, game):
    game.reiniciar_para_lobby()
    socketio.emit("lobby:reiniciado", {
        "game_id": game.id,
        "host_id": game.host_id,
        "jugadores": [j.to_public_dict() for j in game.jugadores],
    }, room=game.id)


SEGUNDOS_ESPERA_PAUSA = 60


def _iniciar_temporizador_pausa(socketio, game_id, jugador_id):
    """
    Si un jugador desconectado no vuelve en SEGUNDOS_ESPERA_PAUSA, regresa
    a todos a la sala de espera automáticamente.
    """
    def tarea():
        socketio.sleep(SEGUNDOS_ESPERA_PAUSA)
        game = store.obtener_partida(game_id)
        if game is None:
            return
        jugador = game.get_jugador(jugador_id)
        # Solo forzamos el regreso si SIGUE pausado por ESE mismo jugador
        # (si ya volvió, o si la partida avanzó de otra forma, no hacemos nada)
        if game.pausado and jugador and not jugador.conectado:
            _forzar_regreso_a_lobby(socketio, game)

    socketio.start_background_task(tarea)


def _continuar_tras_equipo(socketio, game):
    """Espera 3s (el tiempo del banner de resultado de equipo) antes de avanzar de fase."""
    socketio.sleep(3)
    if game.fase_actual == Fase.SELECCION_EQUIPO:
        socketio.emit("ronda:nueva", game.estado_publico(), room=game.id)
    elif game.fase_actual == Fase.VOTACION_MISION:
        socketio.emit("mision:en_curso", {
            "jugadores_en_mision": game.mision_actual().equipo_propuesto
        }, room=game.id)
    elif game.fase_actual == Fase.FIN_JUEGO:
        socketio.emit("game:fin", _payload_fin_juego(game), room=game.id)


def _continuar_tras_mision(socketio, game):
    """Espera 2s (el tiempo del banner de resultado de misión) antes de avanzar de fase."""
    socketio.sleep(2)
    if game.fase_actual == Fase.SELECCION_EQUIPO:
        socketio.emit("ronda:nueva", game.estado_publico(), room=game.id)
    elif game.fase_actual == Fase.ASESINATO:
        socketio.emit("game:fase_asesinato", {
            "asesino_id": game.asesino_id,
            "candidatos": [j.id for j in game.jugadores if j.bando.value == "BUENO"],
        }, room=game.id)
    elif game.fase_actual == Fase.FIN_JUEGO:
        socketio.emit("game:fin", _payload_fin_juego(game), room=game.id)


def _payload_fin_juego(game) -> dict:
    return {
        "ganador": game.ganador.value if game.ganador else None,
        "motivo": game.motivo_fin(),
        "revelar_roles": [
            {"id": j.id, "nombre": j.nombre, "rol": j.rol.value, "bando": j.bando.value}
            for j in game.jugadores
        ],
    }
