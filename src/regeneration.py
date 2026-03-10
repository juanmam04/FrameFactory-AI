"""FASE 10: Regeneración parcial de escenas (guardar prompts y regenerar solo las indicadas)."""
import json
import os
from datetime import datetime
from pathlib import Path

from .config_loader import BASE
from .scene_splitter import Escena
from .prompt_builder import construir_prompt
from .image_generator import generar_imagen

META_DIR = BASE / "output" / "meta"
FEEDBACK_APRENDIZAJE = META_DIR / "feedback_aprendizaje.json"


def _guardar_feedback_aprendizaje(
    proyecto: str,
    escena_numero: int,
    prompt_original: str,
    feedback_usuario: str,
    prompt_refinado: str,
) -> None:
    """Guarda cada corrección para poder usar el historial después (entrenar / preferencias)."""
    FEEDBACK_APRENDIZAJE.parent.mkdir(parents=True, exist_ok=True)
    entrada = {
        "proyecto": proyecto,
        "escena_numero": escena_numero,
        "prompt_original": prompt_original[:500],
        "feedback_usuario": feedback_usuario,
        "prompt_refinado": prompt_refinado[:500],
        "timestamp": datetime.now().isoformat(),
    }
    lista = []
    if FEEDBACK_APRENDIZAJE.exists():
        try:
            lista = json.loads(FEEDBACK_APRENDIZAJE.read_text(encoding="utf-8"))
        except Exception:
            lista = []
    if not isinstance(lista, list):
        lista = []
    lista.append(entrada)
    FEEDBACK_APRENDIZAJE.write_text(json.dumps(lista, ensure_ascii=False, indent=2), encoding="utf-8")


def cargar_historial_feedback() -> list[dict]:
    """Devuelve todo el historial de correcciones guardado (para usar en futuros prompts)."""
    if not FEEDBACK_APRENDIZAJE.exists():
        return []
    try:
        return json.loads(FEEDBACK_APRENDIZAJE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _texto_preferencias_aprendidas(max_entradas: int = 25) -> str:
    """Resumen del historial de correcciones para inyectar en prompts (entrenamiento permanente)."""
    historial = cargar_historial_feedback()
    if not historial:
        return ""
    # Últimas N entradas, solo el feedback del usuario (lo que pidió)
    recientes = historial[-max_entradas:] if len(historial) > max_entradas else historial
    preferencias = [e.get("feedback_usuario", "").strip() for e in recientes if e.get("feedback_usuario")]
    preferencias = list(dict.fromkeys(preferencias))  # sin duplicados, orden conservado
    if not preferencias:
        return ""
    return "Preferencias del usuario (aplicar siempre que aplique): " + "; ".join(preferencias[-15:])


def _refinar_prompt_con_feedback(prompt_original: str, feedback: str) -> str:
    """Usa la corrección del usuario + historial de correcciones anteriores para mejorar el prompt (entrenamiento permanente)."""
    feedback = (feedback or "").strip()
    if not feedback:
        return prompt_original
    preferencias = _texto_preferencias_aprendidas()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return f"{prompt_original} [Corrección del usuario: {feedback}]"
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        bloque_historial = f"\n\nAdemás, el usuario ha pedido antes estas cosas (incorporar cuando sea coherente con la escena): {preferencias}" if preferencias else ""
        r = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un experto en prompts para generación de imágenes. "
                        "Te dan un prompt actual y un comentario del usuario sobre qué no le gusta o qué quiere cambiar. "
                        "Tu trabajo: reescribir el prompt para que la próxima imagen refleje la corrección. "
                        "Si además te pasan preferencias del usuario de correcciones anteriores, incorporálas cuando tengan sentido. "
                        "Mantené el estilo y la escena; solo incorporá los cambios pedidos. "
                        "Devolvé SOLO el nuevo prompt, sin explicaciones, en el mismo idioma que el original."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Prompt actual:\n{prompt_original}\n\nEl usuario dice ahora: {feedback}{bloque_historial}\n\nNuevo prompt (solo el texto):",
                },
            ],
            max_tokens=500,
            temperature=0.3,
        )
        nuevo = (r.choices[0].message.content or "").strip()
        if nuevo:
            return nuevo
    except Exception as e:
        print(f"⚠️ No se pudo refinar prompt con IA ({e}), se agrega feedback al final.")
    return f"{prompt_original} [Corrección del usuario: {feedback}]"


def guardar_prompts_por_escena(
    escenas_con_prompts: list[tuple[Escena, str]] | list[tuple[Escena, str, str | None]] | list[tuple[Escena, str, str | None, str]],
    proyecto: str,
) -> Path:
    """Guarda los prompts por escena. Acepta (Escena, prompt), (Escena, prompt, expression_key) o (Escena, prompt, expression_key, outfit_key)."""
    META_DIR.mkdir(parents=True, exist_ok=True)
    escenas_list = []
    for item in escenas_con_prompts:
        rec = {
            "numero": item[0].numero,
            "texto": item[0].texto,
            "duracion_segundos": item[0].duracion_segundos,
            "prompt": item[1],
        }
        if len(item) >= 3 and item[2] is not None:
            rec["expression_key"] = item[2]
        if len(item) >= 4:
            rec["outfit_key"] = item[3]
        escenas_list.append(rec)
    meta = {"proyecto": proyecto, "escenas": escenas_list}
    path = META_DIR / f"{proyecto}_prompts.json"
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def cargar_prompts(proyecto: str) -> list[tuple[Escena, str, str | None, str | None]]:
    """Carga escenas y prompts guardados. Retorna (Escena, prompt, expression_key, outfit_key); expression_key y outfit_key pueden ser None."""
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
        out.append((
            e,
            item["prompt"],
            item.get("expression_key"),
            item.get("outfit_key"),
        ))
    return out


def regenerar_escenas(
    numeros_escenas: list[int],
    proyecto: str,
    carpeta_imagenes: str = "default",
    feedback_por_escena: dict[int, str] | None = None,
) -> list[Path]:
    """Regenera solo las escenas indicadas. Si pasás feedback_por_escena (número -> texto),
    la IA refina el prompt con esa corrección para adaptarse a lo que querés."""
    escenas_con_prompts = cargar_prompts(proyecto)
    if not escenas_con_prompts:
        raise FileNotFoundError(f"No hay meta para proyecto: {proyecto}")
    by_num = {e.numero: (e, p, expr, ok) for e, p, expr, ok in escenas_con_prompts}
    carpeta = BASE / "output" / "imagenes" / carpeta_imagenes
    feedback_por_escena = feedback_por_escena or {}
    rutas = []
    for n in numeros_escenas:
        if n not in by_num:
            continue
        e, prompt, expression_key, outfit_key = by_num[n]
        feedback = feedback_por_escena.get(n, "").strip()
        if feedback:
            prompt_refinado = _refinar_prompt_con_feedback(prompt, feedback)
            _guardar_feedback_aprendizaje(proyecto, n, prompt, feedback, prompt_refinado)
            prompt = prompt_refinado
        path = generar_imagen(prompt, e.numero, carpeta, expression_key=expression_key, outfit_key=outfit_key)
        if path:
            rutas.append(path)
    return rutas
