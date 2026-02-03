"""FASE 4: División automática del guion en escenas con duración estimada."""
from dataclasses import dataclass

from .config_loader import get_duracion_por_imagen


@dataclass
class Escena:
    numero: int
    texto: str
    duracion_segundos: float


def dividir_en_escenas(guion: str, segundos_por_imagen: float | None = None) -> list[Escena]:
    """
    Divide el guion en escenas por párrafos.
    Cada escena tiene duración estimada (por defecto 5 segundos).
    """
    seg = segundos_por_imagen or get_duracion_por_imagen()
    bloques = [p.strip() for p in guion.strip().split("\n\n") if p.strip()]
    if not bloques:
        bloques = [guion.strip() or "Escena"]
    return [
        Escena(numero=i + 1, texto=t, duracion_segundos=seg)
        for i, t in enumerate(bloques)
    ]


def escenas_a_texto_continuo(escenas: list[Escena]) -> str:
    """Texto completo del guion (para TTS), uniendo todas las escenas."""
    return " ".join(e.texto for e in escenas)
