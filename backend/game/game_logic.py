"""
Máquina de estados del juego: qué pasa en cada transición de fase.
Cada función recibe el Game y lo muta in-place; el módulo de sockets
se encarga de emitir los eventos después de llamar a estas funciones.
"""
from backend.models.game import Game, Fase, Ganador
from backend.models.mission import ResultadoMision

MAX_RECHAZOS_POR_RONDA = 5
MISIONES_PARA_GANAR = 3


def iniciar_ronda(game: Game):
    game.fase_actual = Fase.SELECCION_EQUIPO
    game.intentos_fallidos_ronda = 0
    mision = game.mision_actual()
    mision.equipo_propuesto = []
    mision.votos_equipo = {}


def proponer_equipo(game: Game, jugadores_ids: list[str]) -> tuple[bool, str]:
    mision = game.mision_actual()
    if len(jugadores_ids) != mision.jugadores_requeridos:
        return False, f"Esta misión requiere exactamente {mision.jugadores_requeridos} jugadores."
    mision.equipo_propuesto = jugadores_ids
    game.fase_actual = Fase.VOTACION_EQUIPO
    return True, ""


def registrar_voto_equipo(game: Game, jugador_id: str, aprueba: bool):
    mision = game.mision_actual()
    mision.votos_equipo[jugador_id] = aprueba


def todos_votaron_equipo(game: Game) -> bool:
    mision = game.mision_actual()
    return len(mision.votos_equipo) == len(game.jugadores)


def resolver_votacion_equipo(game: Game) -> dict:
    """
    Cuenta los votos, decide si se aprueba, y avanza la fase correspondiente.
    Devuelve un resumen para que sockets.py arme el evento a emitir.
    """
    mision = game.mision_actual()
    a_favor = sum(1 for v in mision.votos_equipo.values() if v)
    en_contra = len(mision.votos_equipo) - a_favor
    aprobado = a_favor > en_contra  # empate cuenta como rechazo

    resumen = {
        "aprobado": aprobado,
        "votos_a_favor": a_favor,
        "votos_en_contra": en_contra,
        "detalle_por_jugador": dict(mision.votos_equipo),
    }

    if aprobado:
        game.fase_actual = Fase.VOTACION_MISION
    else:
        game.intentos_fallidos_ronda += 1
        mision.reset_para_nueva_propuesta()

        if game.intentos_fallidos_ronda >= MAX_RECHAZOS_POR_RONDA:
            game.fase_actual = Fase.FIN_JUEGO
            game.ganador = Ganador.MALO
        else:
            game.avanzar_lider()
            game.fase_actual = Fase.SELECCION_EQUIPO

    return resumen


def registrar_voto_mision(game: Game, jugador_id: str, exito: bool):
    mision = game.mision_actual()
    mision.votos_mision[jugador_id] = exito


def todos_votaron_mision(game: Game) -> bool:
    mision = game.mision_actual()
    return len(mision.votos_mision) == mision.jugadores_requeridos


def resolver_votacion_mision(game: Game) -> dict:
    mision = game.mision_actual()
    fracasos = sum(1 for v in mision.votos_mision.values() if not v)

    if fracasos >= mision.fallos_requeridos:
        mision.resultado = ResultadoMision.FRACASO
    else:
        mision.resultado = ResultadoMision.EXITO

    game.fase_actual = Fase.RESULTADO_MISION

    resumen = {
        "resultado": mision.resultado.value,
        "conteo_fracasos": fracasos if game.config.revelar_conteo_mision() else None,
    }
    return resumen


def avanzar_despues_de_resultado(game: Game) -> None:
    """
    Se llama después de mostrar el resultado. Decide si el juego terminó,
    si pasa a la fase de asesinato, o si arranca la siguiente ronda.
    """
    bien_ganadas = game.misiones_ganadas(ResultadoMision.EXITO)
    mal_ganadas = game.misiones_ganadas(ResultadoMision.FRACASO)

    if mal_ganadas >= MISIONES_PARA_GANAR:
        game.fase_actual = Fase.FIN_JUEGO
        game.ganador = Ganador.MALO
        return

    if bien_ganadas >= MISIONES_PARA_GANAR:
        game.fase_actual = Fase.ASESINATO
        return

    game.ronda_actual += 1
    game.avanzar_lider()
    iniciar_ronda(game)


def resolver_asesinato(game: Game, objetivo_id: str) -> dict:
    objetivo = game.get_jugador(objetivo_id)
    game.objetivo_asesinato = objetivo_id
    era_merlin = objetivo.rol.value == "MERLIN" if objetivo else False
    game.asesinato_exitoso = era_merlin

    game.fase_actual = Fase.FIN_JUEGO
    game.ganador = Ganador.MALO if era_merlin else Ganador.BUENO

    return {"objetivo_id": objetivo_id, "era_merlin": era_merlin}
