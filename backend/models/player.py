"""
Modelo del jugador.
"""
import uuid
from dataclasses import dataclass, field
from typing import Optional

from .roles import Rol, Bando


@dataclass
class Player:
    nombre: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    rol: Optional[Rol] = None
    bando: Optional[Bando] = None
    conectado: bool = True
    sid: Optional[str] = None  # session id de Socket.IO, para mandarle mensajes directos

    def to_public_dict(self) -> dict:
        """Lo que TODOS pueden ver de este jugador (nunca incluye rol/bando)."""
        return {
            "id": self.id,
            "nombre": self.nombre,
            "conectado": self.conectado,
        }

    def to_private_dict(self) -> dict:
        """Lo que SOLO este jugador puede ver de sí mismo."""
        return {
            **self.to_public_dict(),
            "rol": self.rol.value if self.rol else None,
            "bando": self.bando.value if self.bando else None,
        }
