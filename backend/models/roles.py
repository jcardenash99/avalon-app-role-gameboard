"""
Catálogo de roles y bandos de Avalon.
"""
from enum import Enum


class Bando(str, Enum):
    BUENO = "BUENO"
    MALO = "MALO"


class Rol(str, Enum):
    MERLIN = "MERLIN"
    PERCIVAL = "PERCIVAL"
    LEAL = "LEAL"
    MORGANA = "MORGANA"
    MORDRED = "MORDRED"
    OBERON = "OBERON"
    SECUAZ = "SECUAZ"
    ASESINO = "ASESINO"


# A qué bando pertenece cada rol
BANDO_POR_ROL = {
    Rol.MERLIN: Bando.BUENO,
    Rol.PERCIVAL: Bando.BUENO,
    Rol.LEAL: Bando.BUENO,
    Rol.MORGANA: Bando.MALO,
    Rol.MORDRED: Bando.MALO,
    Rol.OBERON: Bando.MALO,
    Rol.SECUAZ: Bando.MALO,
    Rol.ASESINO: Bando.MALO,
}


class Preset(str, Enum):
    BASICO = "BASICO"
    CLASICO = "CLASICO"
    COMPLETO = "COMPLETO"


# Roles especiales incluidos en cada preset (sin contar los genéricos LEAL/SECUAZ)
ROLES_POR_PRESET = {
    Preset.BASICO: [Rol.MERLIN, Rol.ASESINO],
    Preset.CLASICO: [Rol.MERLIN, Rol.PERCIVAL, Rol.MORGANA, Rol.ASESINO],
    Preset.COMPLETO: [Rol.MERLIN, Rol.PERCIVAL, Rol.MORGANA, Rol.MORDRED, Rol.OBERON, Rol.ASESINO],
}

# Número mínimo de jugadores requerido para cada preset
MIN_JUGADORES_POR_PRESET = {
    Preset.BASICO: 5,
    Preset.CLASICO: 5,
    Preset.COMPLETO: 7,  # Oberon necesita partidas más grandes para no romper el balance
}

# Tabla estándar de Avalon: cuántos buenos/malos según número total de jugadores
BANDOS_POR_NUM_JUGADORES = {
    5: {"buenos": 3, "malos": 2},
    6: {"buenos": 4, "malos": 2},
    7: {"buenos": 4, "malos": 3},
    8: {"buenos": 5, "malos": 3},
    9: {"buenos": 6, "malos": 3},
    10: {"buenos": 6, "malos": 4},
}

# Tabla estándar: jugadores requeridos y fallos requeridos por ronda, según num_jugadores
CONFIG_MISIONES = {
    5: [(2, 1), (3, 1), (2, 1), (3, 1), (3, 1)],
    6: [(2, 1), (3, 1), (4, 1), (3, 1), (4, 1)],
    7: [(2, 1), (3, 1), (3, 1), (4, 2), (4, 1)],
    8: [(3, 1), (4, 1), (4, 1), (5, 2), (5, 1)],
    9: [(3, 1), (4, 1), (4, 1), (5, 2), (5, 1)],
    10: [(3, 1), (4, 1), (4, 1), (5, 2), (5, 1)],
}
