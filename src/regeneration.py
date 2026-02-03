"""FASE 10: Regeneración parcial de escenas (guardar prompts y regenerar solo las indicadas)."""
import json
from pathlib import Path

from .config_loader import BASE
from .scene_splitter import Escena
from .prompt_builder import construir_prompt
from .image_generator import generar_imagen

META_DIR = BASE / "output" / "meta"


def guardar_prompts_por_escena(
    escenas_con_prompts: list[tuple[Escena, str]],
    proyecto: str,
) -> Path:
    """Guarda los prompts originales por escena para poder regenerar después."""
    META_DIR.mkdir(parents=True, exist_ok=True)
    meta = {
        "proyecto": proyecto,
        "escenas": [
            {
                "numero": e.numero,
                "texto": e.texto,
                "duracion_segundos": e.duracion_segundos,
                "prompt": p,
            }
            for e, p in escenas_con_prompts
        ],
    }
    path = META_DIR / f"{proyecto}_prompts.json"
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def cargar_prompts(proyecto: str) -> list[tuple[Escena, str]]:
    """Carga escenas y prompts guardados para un proyecto."""
    path = META_DIR / f"{proyecto}_prompts.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for item in data.get("escenas", []):
        e = Escena(
            numero=item["numero"],
            texto=item["texto"],
            duracion_segundos=item["duracion_segundos"],
        )
        out.append((e, item["prompt"]))
    return out


def regenerar_escenas(
    numeros_escenas: list[int],
    proyecto: str,
    carpeta_imagenes: str = "default",
) -> list[Path]:
    """Regenera solo las escenas indicadas usando los prompts guardados."""
    escenas_con_prompts = cargar_prompts(proyecto)
    if not escenas_con_prompts:
        raise FileNotFoundError(f"No hay meta para proyecto: {proyecto}")
    by_num = {e.numero: (e, p) for e, p in escenas_con_prompts}
    carpeta = BASE / "output" / "imagenes" / carpeta_imagenes
    rutas = []
    for n in numeros_escenas:
        if n not in by_num:
            continue
        e, prompt = by_num[n]
        path = generar_imagen(prompt, e.numero, carpeta)
        if path:
            rutas.append(path)
    return rutas
