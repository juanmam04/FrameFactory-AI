"""Generación de metadata para YouTube: descripción optimizada y capítulos con timestamps."""
import os
from pathlib import Path

from dotenv import load_dotenv

from .config_loader import BASE
from .scene_splitter import Escena

load_dotenv(BASE / ".env")

OUTPUT_META = BASE / "output" / "metadata"


def _segundos_a_timestamp(seg: float) -> str:
    """Convierte segundos a formato 00:00 para YouTube."""
    m = int(seg // 60)
    s = int(seg % 60)
    return f"{m:02d}:{s:02d}"


def generar_capítulos(escenas: list[Escena]) -> str:
    """Genera texto de capítulos con timestamps (00:00, 00:05, ...). Cumple reglas YouTube."""
    lineas = []
    t_acum = 0.0
    for e in escenas:
        lineas.append(f"{_segundos_a_timestamp(t_acum)} {e.texto[:60]}{'…' if len(e.texto) > 60 else ''}")
        t_acum += e.duracion_segundos
    return "\n".join(lineas)


def generar_descripcion(
    titulo: str,
    guion_resumen: str,
    capítulos_texto: str,
    hook: str = "",
    cta: str = "Suscribite para más videos.",
) -> str:
    """
    Genera descripción optimizada para YouTube.
    Plantilla: hook, contexto, capítulos, CTA.
    """
    partes = []
    if hook:
        partes.append(hook.strip())
    partes.append(guion_resumen[:500].strip() + ("..." if len(guion_resumen) > 500 else ""))
    partes.append("\n--- Capítulos ---\n")
    partes.append(capítulos_texto)
    if cta:
        partes.append("\n---\n" + cta.strip())
    return "\n\n".join(partes)


def guardar_metadata(
    nombre_proyecto: str,
    titulo: str,
    descripcion: str,
    capítulos: str,
) -> Path:
    """Guarda descripción y capítulos en un archivo para copiar a YouTube."""
    OUTPUT_META.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_META / f"{nombre_proyecto}_youtube.txt"
    contenido = f"# Título\n{titulo}\n\n# Descripción\n{descripcion}\n\n# Capítulos (copiar en descripción)\n{capítulos}"
    path.write_text(contenido, encoding="utf-8")
    return path


def generar_metadata_completa(
    nombre_proyecto: str,
    tema: str,
    escenas: list[Escena],
    guion_texto: str,
) -> Path:
    """Genera descripción + capítulos y los guarda. Retorna ruta al archivo."""
    capítulos = generar_capítulos(escenas)
    titulo = tema[:100] if tema else nombre_proyecto
    descripcion = generar_descripcion(
        titulo=titulo,
        guion_resumen=guion_texto[:800],
        capítulos_texto=capítulos,
        hook=f"Video sobre: {tema[:200]}." if tema else "",
        cta="Suscribite para más videos.",
    )
    return guardar_metadata(nombre_proyecto, titulo, descripcion, capítulos)
