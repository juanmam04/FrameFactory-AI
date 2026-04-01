"""FASE 5: Conversión de escenas / beats a prompts visuales (arquitectura simplificada stickman storyboard)."""
from __future__ import annotations

import os
import random
from pathlib import Path
from typing import List, Dict, Any

from .config_loader import (
    get_visual_bible,
    get_character_bible,
    get_role_library,
)
from .scene_splitter import Escena
from .visual_beats import VisualBeat
from .scene_visual_mapper import map_escena_to_visual_meta, map_beat_to_visual_meta
from .action_scene import apply_action_scene_meta_overrides, action_prompt_appendix
from .visual_story_mapper import enrich_scene_visual_meta, enrich_beat_visual_meta
from .storyboard_continuity import (
    CharacterStateStore,
    StoryboardState,
    apply_beat_camera_position_hint,
    construir_prompt_secuencial,
    initial_storyboard_state,
    resolve_scene_context,
    update_storyboard_state,
)
from .storyboard_debug import (
    BeatPromptDebugBundle,
    clone_storyboard_state,
    scene_continuity_to_dict,
    storyboard_state_to_dict,
    visual_beat_to_dict,
    write_beat_debug_json,
)

# Mapeo emoción del beat → clave en character_reference (Kontext)
_EMOTION_TO_EXPRESSION_KEY: dict[str, str] = {
    "alegría": "happy",
    "alegria": "happy",
    "happy": "happy",
    "joy": "happy",
    "felicidad": "happy",
    "determinación": "determined",
    "determinacion": "determined",
    "determined": "determined",
    "sorpresa": "surprised",
    "surprised": "surprised",
    "sorprendido": "surprised",
    "miedo": "scared",
    "scared": "scared",
    "fear": "scared",
    "asustado": "scared",
    "enojo": "angry",
    "angry": "angry",
    "ira": "angry",
    "rabia": "angry",
    "shock": "shocked",
    "shocked": "shocked",
    "neutral": "neutral",
    "calma": "neutral",
    "calm": "neutral",
    "tensión": "neutral",
    "tension": "neutral",
    "intensidad": "neutral",
    "conflicto": "neutral",
    "duda": "neutral",
    "decisión": "determined",
    "decision": "determined",
    "resolución": "neutral",
    "resolucion": "neutral",
}


def emotion_to_expression_key(emotion: str | None) -> str | None:
    """Clave de referencia de expresión para Kontext (happy, determined, …) o None → usar front."""
    if not (emotion or "").strip():
        return None
    e = emotion.strip().lower()
    return _EMOTION_TO_EXPRESSION_KEY.get(e)


def _camera_options() -> list[str]:
    vb = get_visual_bible()
    cam = vb.get("camera_options") or []
    if cam:
        return list(cam)
    return [
        "wide shot",
        "medium shot",
        "close up",
        "side shot",
        "over the shoulder",
        "top down",
        "low angle",
        "rear view",
    ]


def _style_lock() -> str:
    vb = get_visual_bible()
    return vb.get(
        "style_lock",
        "Flat 2D storyboard illustration. Minimal stickman characters. Same visual style across all images.",
    )


def _character_bible() -> dict:
    return get_character_bible().get("characters", {})


def _role_library() -> dict:
    return get_role_library().get("roles", {})


def _extras_rule() -> str | None:
    vb = get_visual_bible()
    return (vb.get("extras_rule") or "").strip() or None


def _resolve_camera_order(n: int, shuffle: bool = False) -> list[str]:
    """Devuelve una lista de cámaras de longitud n sin repetir la misma dos veces seguidas."""
    options = _camera_options()
    if not options or n <= 0:
        return []
    order: list[str] = []
    for i in range(n):
        if i == 0:
            cam = random.choice(options) if shuffle else options[0]
        else:
            prev = order[-1]
            candidates = [c for c in options if c != prev] or options
            cam = random.choice(candidates) if shuffle else candidates[(i - 1) % len(candidates)]
        order.append(cam)
    return order


def _describe_character_from_bible(key: str, body_override: str | None, outfit_override: str | None) -> str:
    """
    Devuelve una descripción corta del personaje tomando solo atributos visuales.
    Aplica overrides de body_preset y outfit_base si vienen del mapper.
    """
    data = _character_bible().get(key, {})
    body = body_override or data.get("body_preset", "adult")
    outfit = outfit_override or data.get("outfit_base", "casual_dark")
    color = data.get("color_identity", "")
    sil = data.get("silhouette_hint", "")
    acc = data.get("accessory", "")
    parts = [body, "body", f"{outfit} outfit"]
    if color:
        parts.append(f"{color} identity")
    if sil:
        parts.append(f"{sil} silhouette")
    if acc and acc != "none":
        parts.append(f"simple accessory: {acc}")
    return ", ".join(parts)


def _describe_role(role_key: str) -> str:
    """Descripción visual mínima para personajes funcionales (role_library)."""
    data = _role_library().get(role_key, {})
    body = data.get("body_preset", "adult")
    outfit = data.get("outfit_base", "casual_dark")
    color = data.get("color_identity", "")
    sil = data.get("silhouette_hint", "")
    acc = data.get("accessory", "")
    parts = [body, "body", f"{outfit} outfit"]
    if color:
        parts.append(f"{color} identity")
    if sil:
        parts.append(f"{sil} silhouette")
    if acc and acc != "none":
        parts.append(f"simple accessory: {acc}")
    return ", ".join(parts)


def _build_characters_block(scene_characters: list[str] | None, meta: Dict[str, Any]) -> str:
    """
    Construye el bloque "Characters in scene:".
    scene_characters es una lista de claves (character_bible o role_library).
    Usa character_overrides[personaje] para body_preset / outfit_base cuando existan.
    """
    if not scene_characters:
        scene_characters = ["protagonist"]

    chars_cfg = _character_bible()
    roles_cfg = _role_library()
    overrides: Dict[str, Dict[str, str]] = meta.get("character_overrides") or {}

    lines: list[str] = []
    for key in scene_characters:
        if key in chars_cfg:
            ov = overrides.get(key, {})
            bo = ov.get("body_preset")
            oo = ov.get("outfit_base")
            desc = _describe_character_from_bible(key, bo, oo)
            label = chars_cfg[key].get("role", key)
            lines.append(f"- {label.capitalize()}: {desc}.")
        elif key in roles_cfg:
            desc = _describe_role(key)
            lines.append(f"- {key.replace('_', ' ').title()}: {desc}.")
        elif key == "extras":
            rule = _extras_rule()
            if rule:
                lines.append(f"- Extras: {rule}")
        else:
            lines.append(f"- {key.replace('_', ' ').title()}: flat stickman character matching the project style.")

    if not lines:
        return ""

    header = "Characters in scene:\n"
    return header + "\n".join(lines)


def _build_scene_block(meta: Dict[str, Any]) -> str:
    loc = (meta.get("location") or "clear location that matches the story").strip()
    act = (meta.get("action") or "clear readable action that matches the script").strip()
    md = (meta.get("mood") or "neutral").strip()
    kv = (meta.get("key_visual") or "").strip()

    lines = [
        "Scene:",
        f"Location: {loc}.",
        f"Action: {act}.",
        f"Mood: {md}.",
    ]
    if kv:
        lines.append(f"Key visual element: {kv}.")
    return "\n".join(lines)


def _build_camera_block(camera: str) -> str:
    return f"Camera:\n{camera}."


def _final_rules_block() -> str:
    return (
        "Rules:\n"
        "One clear narrative image.\n"
        "Clear visual focus.\n"
        "No empty background.\n"
        "16:9 frame."
    )


def construir_prompt(
    escena: Escena,
    indice_plan: int | None = None,
    descripcion_visual: str | None = None,
    scene_meta: Dict[str, Any] | None = None,
) -> str:
    """
    Prompt final simplificado para una escena (con capa narrativa aplicada).
    """
    meta = scene_meta or map_escena_to_visual_meta(escena, descripcion_visual)

    cameras = _camera_options()
    cam = meta.get("camera")
    if not cam:
        if indice_plan is not None and 0 <= indice_plan < len(cameras):
            cam = cameras[indice_plan]
        else:
            order = _resolve_camera_order(escena.numero + 1)
            cam = order[escena.numero] if escena.numero < len(order) else order[-1]
    meta["camera"] = cam

    style = _style_lock()
    theme = meta.get("thematic_context") or "generic"
    visual_device = meta.get("visual_device") or "literal"
    rep_mode = meta.get("narrative_representation_mode") or "literal"
    scene_focus = meta.get("scene_focus") or "protagonist_face"
    symbolic_desc = meta.get("symbolic_descriptions") or []
    symbolic_str = ", ".join(symbolic_desc) if symbolic_desc else ""

    chars_block = _build_characters_block(meta.get("scene_characters"), meta)
    scene_block = _build_scene_block(meta)
    # Cámara final: la ya resuelta en meta["camera"] (p. ej. anti-repetición) tiene prioridad absoluta.
    camera_block = _build_camera_block(cam)
    rules_block = _final_rules_block()

    parts = [style.strip()]

    parts.append(f"Theme:\n{theme}.")

    if chars_block:
        parts.append(chars_block.strip())

    parts.append(
        "Narrative device:\n"
        f"{visual_device}.\n"
        "Representation mode:\n"
        f"{rep_mode}.\n"
        "Scene focus:\n"
        f"{scene_focus}."
    )

    if meta.get("action_scene_dynamic"):
        parts.append(action_prompt_appendix())

    parts.append(scene_block.strip())

    if symbolic_str:
        parts.append(f"Symbolic elements:\n{symbolic_str}.")

    parts.append(camera_block.strip())
    parts.append(rules_block.strip())

    return "\n\n".join(parts)


def _indices_planos_sin_repetir_consecutivo(
    n_escenas: int,
    planos: list[str],
    shuffle: bool = False,
) -> list[int]:
    """
    Conservado por compatibilidad: devuelve índices de cámaras sin repetir consecutivos.
    Usa la lista de camera_options de visual_bible.yaml.
    """
    if not planos or n_escenas == 0:
        return [0] * n_escenas
    n = len(planos)
    orden: list[int] = []
    for i in range(n_escenas):
        if i == 0:
            orden.append(random.randint(0, n - 1) if shuffle else 0)
        else:
            prev_idx = orden[i - 1]
            prev_plano = planos[prev_idx]
            otros = [j for j in range(n) if planos[j] != prev_plano] or list(range(n))
            orden.append(random.choice(otros) if shuffle else otros[(i - 1) % len(otros)])
    return orden


def prompts_para_escenas(
    escenas: list[Escena],
    shuffle_planos: bool = False,
    tema: str | None = None,
    usar_descripciones_ia: bool = True,
    video_theme: str | None = None,
) -> list[tuple[Escena, str, str | None, str]]:
    """
    Genera un prompt por escena usando la nueva arquitectura.
    'video_theme' puede ser, por ejemplo: 'football_career'.
    Retorna (Escena, prompt, expression_key, outfit_key). Los dos últimos se dejan en None.
    """
    from .scene_descriptions import generar_descripciones_visuales_escenas  # import local para evitar ciclos

    if video_theme is None:
        video_theme = tema

    descripciones: list[str] = []
    if usar_descripciones_ia and escenas:
        descripciones = generar_descripciones_visuales_escenas(
            escenas, tema=tema, verificar_y_corregir=False
        )
        if descripciones:
            print(f"   Descripciones visuales generadas para {len(descripciones)} escenas.")

    cameras = _camera_options()
    resultados: list[tuple[Escena, str, str | None, str]] = []
    last_cam: str | None = None

    for i, e in enumerate(escenas):
        desc = descripciones[i] if i < len(descripciones) else None
        base_meta = map_escena_to_visual_meta(e, desc)
        full_meta = enrich_scene_visual_meta(base_meta, video_theme=video_theme)
        full_meta = apply_action_scene_meta_overrides(full_meta, escena_text=e.texto)

        # Aplicar camera_priority intentando no repetir consecutivo
        pref_cam = full_meta.get("camera_priority")
        cam: str
        if pref_cam:
            cam = pref_cam
        else:
            cam = cameras[0] if cameras else "medium shot"
        if cam == last_cam and cameras:
            # elegir otra cámara distinta
            alt = [c for c in cameras if c != last_cam] or cameras
            cam = alt[0]
        full_meta["camera"] = cam
        last_cam = cam

        prompt = construir_prompt(e, indice_plan=None, descripcion_visual=desc, scene_meta=full_meta)
        resultados.append((e, prompt, None, None))
    return resultados


def compute_beat_prompt_bundle(
    scene_index: int,
    beat: VisualBeat,
    state: StoryboardState,
    char_store: CharacterStateStore,
    video_theme: str | None,
) -> tuple[str, dict, BeatPromptDebugBundle]:
    """
    Un paso del pipeline: beat → meta → contexto resuelto → prompt.
    Mutates `state` y `char_store`. Para tests y modo debug.
    """
    state_before = storyboard_state_to_dict(clone_storyboard_state(state))

    base_meta = map_beat_to_visual_meta(beat)
    full_meta = enrich_beat_visual_meta(base_meta, video_theme=video_theme)
    full_meta = apply_action_scene_meta_overrides(full_meta, beat=beat)
    full_meta = apply_beat_camera_position_hint(beat, full_meta)

    ctx = resolve_scene_context(scene_index, beat, base_meta, full_meta, state, char_store)
    full_meta["location"] = ctx.resolved_location
    full_meta["camera"] = ctx.resolved_camera

    if set(ctx.characters_present) <= {"protagonist"}:
        chars_block = ""
    else:
        chars_block = _build_characters_block(ctx.characters_present, base_meta)
    prompt = construir_prompt_secuencial(ctx, full_meta, chars_block)

    update_storyboard_state(state, ctx, full_meta, beat=beat)
    state_after = storyboard_state_to_dict(state)

    gen_meta = {
        "seed_material": ctx.seed_material,
        "location_id": ctx.resolved_location,
        "resolved_camera": ctx.resolved_camera,
    }
    bundle = BeatPromptDebugBundle(
        scene_index=scene_index,
        beat_id=beat.beat_id,
        state_before=state_before,
        state_after=state_after,
        beat=visual_beat_to_dict(beat),
        base_meta=dict(base_meta),
        enriched_meta=dict(full_meta),
        resolved_context=scene_continuity_to_dict(ctx),
        prompt_final=prompt,
        gen_meta=dict(gen_meta),
    )
    return prompt, gen_meta, bundle


def prompts_para_beats(
    beats: list[VisualBeat],
    shuffle_planos: bool = True,
    video_theme: str | None = None,
    project_id: str = "",
    debug_output_dir: str | Path | None = None,
) -> list[tuple[VisualBeat, str, dict]]:
    """
    Genera prompts a partir de beats con estado secuencial (StoryboardState) y continuidad explícita.
    Retorna (beat, prompt, gen_meta) donde gen_meta incluye seed_material y location_id para el generador.

    Modo debug: `debug_output_dir` o variable de entorno `PROMPT_PIPELINE_DEBUG_DIR` escribe un JSON
    por beat (`scene_XXXX.json`) con beat, metas, contexto resuelto, prompt y estado antes/después.
    """
    if not beats:
        return []
    state = initial_storyboard_state(project_id=project_id or "", video_theme=video_theme)
    char_store = CharacterStateStore()
    resultados: list[tuple[VisualBeat, str, dict]] = []

    dbg = debug_output_dir or os.environ.get("PROMPT_PIPELINE_DEBUG_DIR", "").strip()
    debug_path = Path(dbg) if dbg else None

    for i, beat in enumerate(beats):
        prompt, gen_meta, bundle = compute_beat_prompt_bundle(
            i, beat, state, char_store, video_theme
        )
        if debug_path is not None:
            write_beat_debug_json(bundle, debug_path / f"scene_{beat.beat_id:04d}.json")
        resultados.append((beat, prompt, gen_meta))
    return resultados


def get_outfit_key_for_beat(beat: VisualBeat) -> str:
    """
    Compatibilidad: ya no se usa outfit library en la nueva arquitectura.
    Se mantiene la firma para no romper imports, pero siempre devuelve 'casual_dark'.
    """
    return "casual_dark"

