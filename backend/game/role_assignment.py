"""
Arma la lista final de roles a repartir y los asigna aleatoriamente a los jugadores.
"""
import random

from backend.models.game import Game, GameConfig
from backend.models.roles import Rol, BANDO_POR_ROL, BANDOS_POR_NUM_JUGADORES


def armar_roles(config: GameConfig) -> list[Rol]:
    """
    Toma los roles especiales del preset y rellena con genéricos (LEAL/SECUAZ)
    hasta completar la proporción buenos/malos que corresponde según num_jugadores.
    """
    especiales = list(config.roles_especiales())
    tabla = BANDOS_POR_NUM_JUGADORES[config.num_jugadores]

    buenos_especiales = [r for r in especiales if BANDO_POR_ROL[r].value == "BUENO"]
    malos_especiales = [r for r in especiales if BANDO_POR_ROL[r].value == "MALO"]

    faltan_buenos = tabla["buenos"] - len(buenos_especiales)
    faltan_malos = tabla["malos"] - len(malos_especiales)

    if faltan_buenos < 0 or faltan_malos < 0:
        raise ValueError(
            f"El preset tiene más roles especiales de un bando de los que caben "
            f"para {config.num_jugadores} jugadores."
        )

    roles_finales = (
        especiales
        + [Rol.LEAL] * faltan_buenos
        + [Rol.SECUAZ] * faltan_malos
    )
    return roles_finales


def asignar_roles(game: Game) -> None:
    """Asigna roles y bandos a los jugadores de la partida, in-place."""
    roles = armar_roles(game.config)
    random.shuffle(roles)

    for jugador, rol in zip(game.jugadores, roles):
        jugador.rol = rol
        jugador.bando = BANDO_POR_ROL[rol]
        if rol == Rol.ASESINO:
            game.asesino_id = jugador.id
