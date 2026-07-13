"""
Modelo de una misión (ronda).
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ResultadoMision(str, Enum):
    PENDIENTE = "PENDIENTE"
    EXITO = "EXITO"
    FRACASO = "FRACASO"


@dataclass
class Mission:
    numero_ronda: int
    jugadores_requeridos: int
    fallos_requeridos: int

    equipo_propuesto: list[str] = field(default_factory=list)  # ids de jugadores
    propuestas_rechazadas: list[list[str]] = field(default_factory=list)

    votos_equipo: dict[str, bool] = field(default_factory=dict)  # player_id -> aprueba
    votos_mision: dict[str, bool] = field(default_factory=dict)  # player_id -> exito

    resultado: ResultadoMision = ResultadoMision.PENDIENTE

    def equipo_aprobado(self) -> Optional[bool]:
        """None si aún no han votado todos, True/False si ya se puede resolver."""
        return None  # la lógica real de conteo vive en game_logic.py

    def reset_para_nueva_propuesta(self):
        """Se llama cuando se rechaza un equipo y hay que proponer de nuevo."""
        if self.equipo_propuesto:
            self.propuestas_rechazadas.append(self.equipo_propuesto)
        self.equipo_propuesto = []
        self.votos_equipo = {}
