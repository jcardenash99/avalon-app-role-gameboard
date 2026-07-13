"""
Almacén en memoria de partidas activas.
Como cada partida es efímera (dura lo que dura la reunión), no hace falta
una base de datos real: un diccionario en RAM del proceso alcanza.
"""
from backend.models.game import Game

games: dict[str, Game] = {}


def crear_partida() -> Game:
    game = Game()
    games[game.id] = game
    return game


def obtener_partida(game_id: str) -> Game | None:
    return games.get(game_id)


def eliminar_partida(game_id: str) -> None:
    games.pop(game_id, None)
