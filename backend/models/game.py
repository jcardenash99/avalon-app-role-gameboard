"""
Modelo principal de la partida.
"""
import random
import string
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .player import Player
from .mission import Mission, ResultadoMision
from .roles import (
    Rol, Bando, Preset,
    ROLES_POR_PRESET, MIN_JUGADORES_POR_PRESET,
    BANDOS_POR_NUM_JUGADORES, CONFIG_MISIONES,
)


class Fase(str, Enum):
    LOBBY = "LOBBY"
    ASIGNACION_ROLES = "ASIGNACION_ROLES"
    SELECCION_EQUIPO = "SELECCION_EQUIPO"
    VOTACION_EQUIPO = "VOTACION_EQUIPO"
    VOTACION_MISION = "VOTACION_MISION"
    RESULTADO_MISION = "RESULTADO_MISION"
    ASESINATO = "ASESINATO"
    FIN_JUEGO = "FIN_JUEGO"


class Ganador(str, Enum):
    BUENO = "BUENO"
    MALO = "MALO"


def generar_codigo_sala(longitud: int = 5) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=longitud))


@dataclass
class GameConfig:
    preset: Preset = Preset.CLASICO
    num_jugadores: int = 5

    def roles_especiales(self) -> list[Rol]:
        return ROLES_POR_PRESET[self.preset]

    def es_valido(self) -> tuple[bool, str]:
        if self.num_jugadores < 5 or self.num_jugadores > 10:
            return False, "Avalon requiere entre 5 y 10 jugadores."
        minimo = MIN_JUGADORES_POR_PRESET[self.preset]
        if self.num_jugadores < minimo:
            return False, f"El preset {self.preset.value} requiere al menos {minimo} jugadores."
        return True, ""

    def revelar_conteo_mision(self) -> bool:
        # Con más de 6 jugadores, el conteo de fracasos ya no delata tanto a un jugador puntual
        return self.num_jugadores > 6


@dataclass
class Game:
    id: str = field(default_factory=generar_codigo_sala)
    jugadores: list[Player] = field(default_factory=list)
    config: GameConfig = field(default_factory=GameConfig)

    fase_actual: Fase = Fase.LOBBY
    ronda_actual: int = 0  # índice 0-based dentro de historial_misiones
    lider_actual_index: int = 0
    intentos_fallidos_ronda: int = 0

    historial_misiones: list[Mission] = field(default_factory=list)

    asesino_id: Optional[str] = None
    objetivo_asesinato: Optional[str] = None
    asesinato_exitoso: Optional[bool] = None

    ganador: Optional[Ganador] = None
    pausado: bool = False
    jugador_desconectado_id: Optional[str] = None
    host_id: Optional[str] = None
    jugadores_confirmados_rol: set = field(default_factory=set)

    def es_host(self, jugador_id: str) -> bool:
        return jugador_id == self.host_id

    # ---------- helpers de jugadores ----------

    def get_jugador(self, jugador_id: str) -> Optional[Player]:
        return next((j for j in self.jugadores if j.id == jugador_id), None)

    def lider_actual(self) -> Player:
        return self.jugadores[self.lider_actual_index]

    def avanzar_lider(self):
        self.lider_actual_index = (self.lider_actual_index + 1) % len(self.jugadores)

    def motivo_fin(self) -> str:
        if self.asesinato_exitoso is not None:
            return "asesino_acierta" if self.asesinato_exitoso else "3_exitos_asesino_falla"
        if self.misiones_ganadas(ResultadoMision.FRACASO) >= 3:
            return "3_fracasos"
        if self.intentos_fallidos_ronda >= 5:
            return "5_rechazos"
        return ""

    def reiniciar_para_lobby(self):
        """Vuelve la partida al lobby, conservando jugadores, host y configuración."""
        self.fase_actual = Fase.LOBBY
        self.ronda_actual = 0
        self.lider_actual_index = 0
        self.intentos_fallidos_ronda = 0
        self.historial_misiones = []
        self.asesino_id = None
        self.objetivo_asesinato = None
        self.asesinato_exitoso = None
        self.ganador = None
        self.pausado = False
        self.jugador_desconectado_id = None
        self.jugadores_confirmados_rol = set()
        for jugador in self.jugadores:
            jugador.rol = None
            jugador.bando = None

    # ---------- helpers de misión ----------

    def mision_actual(self) -> Mission:
        return self.historial_misiones[self.ronda_actual]

    def inicializar_misiones(self):
        config_rondas = CONFIG_MISIONES[self.config.num_jugadores]
        self.historial_misiones = [
            Mission(numero_ronda=i + 1, jugadores_requeridos=req, fallos_requeridos=fallos)
            for i, (req, fallos) in enumerate(config_rondas)
        ]

    def misiones_ganadas(self, resultado: ResultadoMision) -> int:
        return sum(1 for m in self.historial_misiones if m.resultado == resultado)

    # ---------- vista pública / privada ----------

    def estado_publico(self) -> dict:
        info_mision = {}
        if self.historial_misiones and self.ronda_actual < len(self.historial_misiones):
            mision = self.mision_actual()
            info_mision = {
                "jugadores_requeridos": mision.jugadores_requeridos,
                "fallos_requeridos": mision.fallos_requeridos,
            }

        return {
            "id": self.id,
            "jugadores": [j.to_public_dict() for j in self.jugadores],
            "fase_actual": self.fase_actual.value,
            "ronda_actual": self.ronda_actual + 1,
            "lider_id": self.lider_actual().id if self.jugadores else None,
            "intentos_fallidos_ronda": self.intentos_fallidos_ronda,
            "misiones_ganadas_bien": self.misiones_ganadas(ResultadoMision.EXITO),
            "misiones_ganadas_mal": self.misiones_ganadas(ResultadoMision.FRACASO),
            "historial_resultados": [m.resultado.value for m in self.historial_misiones],
            "pausado": self.pausado,
            "ganador": self.ganador.value if self.ganador else None,
            **info_mision,
        }

    def vista_jugador(self, jugador_id: str) -> dict:
        """Combina el estado público con la info secreta de ESTE jugador."""
        jugador = self.get_jugador(jugador_id)
        if jugador is None:
            return self.estado_publico()

        vista = self.estado_publico()
        vista["tu_id"] = jugador.id
        vista["tu_rol"] = jugador.rol.value if jugador.rol else None
        vista["tu_bando"] = jugador.bando.value if jugador.bando else None
        vista["jugadores_visibles"] = self._info_visible_para(jugador)
        return vista

    def _info_visible_para(self, jugador: Player) -> list[dict]:
        """
        Calcula qué ve este jugador de los demás, según su rol.
        Esto reemplaza tener que 'recordar' censurar datos: se arma desde cero cada vez.
        """
        resultado = []
        for otro in self.jugadores:
            if otro.id == jugador.id:
                continue
            info = None

            if jugador.rol == Rol.MERLIN:
                # Merlín ve a todos los malos EXCEPTO Mordred
                if otro.bando == Bando.MALO and otro.rol != Rol.MORDRED:
                    info = "malo"

            elif jugador.rol == Rol.PERCIVAL:
                # Percival ve a Merlín y Morgana, pero no sabe distinguir cuál es cuál
                if otro.rol in (Rol.MERLIN, Rol.MORGANA):
                    info = "merlin_o_morgana"

            elif jugador.bando == Bando.MALO and jugador.rol != Rol.OBERON:
                # Los malos se ven entre sí, EXCEPTO Oberon (que nadie ve y que no ve a nadie)
                if otro.bando == Bando.MALO and otro.rol != Rol.OBERON:
                    info = "malo"

            resultado.append({"id": otro.id, "nombre": otro.nombre, "info": info})
        return resultado
