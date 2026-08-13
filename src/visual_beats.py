"""FASE 4.5: Beats visuales cinematográficos (acts -> scenes -> visual beats).

Este módulo implementa la capa intermedia entre escenas de guion y prompts de imagen:

script
↓
scene segmentation (scene_splitter.Dividir_en_escenas)
↓
visual beats (este módulo)
↓
camera selection + prompt builder (prompt_builder.prompts_para_beats)
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import List, Optional

from .config_loader import BASE, get_duracion_por_imagen
from .scene_splitter import Escena


@dataclass
class VisualBeat:
    """Unidad mínima visual para una imagen estática cinematográfica."""

    beat_id: int
    scene: int  # scene_id
    original_text: str
    action: str
    emotion: str
    context: str
    location: str
    time_of_day: str
    shot_role: str
    camera_type: str
    camera_position: str
    camera_distance: str
    importance: str
    # Campos adicionales útiles para pipeline largo
    act: Optional[int] = None


CAMERA_SHOTS = [
    "POV",
    "over_the_shoulder",
    "wide_shot",
    "medium_shot",
    "close_up",
    "side_angle",
    "top_down",
    "low_angle",
    "rear_view",
    "environment_shot",
]

SHOT_ROLES = [
    "establishing",
    "action",
    "reaction",
    "detail",
    "transition",
]


def _act_for_scene(idx: int, total_scenes: int) -> int:
    """Asignación aproximada de acto (I/II/III) según posición en el guion."""
    if total_scenes <= 0:
        return 1
    ratio = (idx + 1) / total_scenes
    if ratio <= 0.25:
        return 1
    if ratio <= 0.75:
        return 2
    return 3


def _beats_por_escena_llm(
    escena: Escena,
    act: int,
    tema: str,
    beat_offset: int,
    protagonists: Optional[List[str]] = None,
) -> List[VisualBeat]:
    """Pide a la LLM que convierta una escena de texto en varios beats visuales."""
    # Permitir desactivar la LLM vía .env para evitar cuelgues/costos excesivos (usa solo fallback).
    if os.getenv("VISUAL_BEATS_LLM_DISABLED", "").strip().lower() in ("1", "true", "yes"):
        return []

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return []

    try:
        from openai import OpenAI
    except Exception:
        return []

    client = OpenAI(api_key=api_key)

    system = (
        "You are a documentary film director. Convert narration into VISUAL BEATS for still photographs.\n"
        "Each beat is ONE 16:9 still that could not be swapped into another episode.\n"
        "Return JSON only: a list of beats with exactly these keys:\n"
        "beat_id, scene, original_text, action, emotion, context, location, time_of_day, shot_role, camera_type, camera_position, camera_distance, importance.\n"
        "shot_role MUST be one of: establishing, action, reaction, detail, transition.\n"
        "camera_type MUST be one of: POV, over_the_shoulder, wide_shot, medium_shot, close_up, side_angle, top_down, low_angle, rear_view, environment_shot.\n"
        "HARD RULES:\n"
        "- Name the person in `action` (the real protagonist of this sentence).\n"
        "- `location` must be SPECIFIC (penthouse at 3am, jet cabin, empty floor after eviction, "
        "courthouse steps, a printing plant) — never 'office', 'WeWork office', or 'conference room'.\n"
        "- `action` = one physical verb happening NOW (rips a lease, dances on a desk, stares at a For Sale sign alone).\n"
        "- One protagonist, maybe one counterpart. Never a crowd of anonymous workers unless the beat IS a mass event.\n"
        "- FORBIDDEN: crowded coworking, rows of laptops, generic glass conference rooms, handshake, CEO portrait.\n"
        "- Write action and location in English.\n"
        "Return ONLY valid JSON, no extra text."
    )

    user_payload = {
        "tema": tema,
        "acto": act,
        "numero_de_escena": escena.numero,
        "texto_escena": escena.texto,
        "beat_id_offset": beat_offset,
        "protagonists": [p for p in (protagonists or []) if p][:8],
    }

    try:
        prompt_usuario = (
            "Turn this scene into 1 visual beat (2 only if the narration truly contains two distinct moments).\n"
            "Name the protagonist. Pick a unique location. JSON list only.\n\n"
            + json.dumps(user_payload, ensure_ascii=False)
        )
        r = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {
                    "role": "system",
                    "content": system,
                },
                {
                    "role": "user",
                    "content": prompt_usuario,
                },
            ],
            max_tokens=800,
            temperature=0.5,
        )
    except Exception as e:
        print(f"⚠️ Error LLM al generar beats para escena {escena.numero}: {e}")
        return []

    # El SDK moderno devuelve `message.content` como string para texto puro
    content = (r.choices[0].message.content or "").strip()
    try:
        data = json.loads(content)
    except Exception as e:
        print(f"⚠️ Error parseando JSON de beats para escena {escena.numero}: {e}")
        return []

    if not isinstance(data, list):
        print(f"⚠️ Respuesta de beats para escena {escena.numero} no es lista.")
        return []

    beats: List[VisualBeat] = []
    for i, raw in enumerate(data):
        if not isinstance(raw, dict):
            continue
        try:
            beat = VisualBeat(
                beat_id=int(raw.get("beat_id", beat_offset + i + 1)),
                scene=int(raw.get("scene", escena.numero)),
                original_text=str(raw.get("original_text") or escena.texto).strip(),
                action=str(raw.get("action") or escena.texto[:200]).strip(),
                emotion=str(raw.get("emotion") or "tensión").strip(),
                context=str(raw.get("context") or "").strip(),
                location=str(raw.get("location") or "").strip(),
                time_of_day=str(raw.get("time_of_day") or "").strip(),
                shot_role=str(raw.get("shot_role") or "").strip(),
                camera_type=str(raw.get("camera_type") or "medium_shot").strip(),
                camera_position=str(raw.get("camera_position") or "").strip(),
                camera_distance=str(raw.get("camera_distance") or "").strip(),
                importance=str(raw.get("importance") or "normal").strip(),
                act=act,
            )
            beats.append(beat)
        except Exception:
            continue
    return beats


def _beats_por_escena_fallback(escena: Escena, act: int, beat_offset: int) -> List[VisualBeat]:
    """Fallback sin LLM: un beat por escena, heurístico."""
    texto = (escena.texto or "").strip()
    if not texto:
        texto = "Momento de transición."
    primera_frase = texto.split(".")[0].strip() or texto
    beat = VisualBeat(
        beat_id=beat_offset + 1,
        scene=escena.numero,
        original_text=texto,
        action=primera_frase,
        emotion="tensión",
        context="momento clave de la escena",
        location="lugar principal de la historia",
        time_of_day="indefinido",
        shot_role="action",
        camera_type="medium_shot",
        camera_position="frontal",
        camera_distance="media",
        importance="normal",
        act=act,
    )
    return [beat]


def generar_beats_para_escenas(
    escenas: list[Escena],
    tema: str,
    max_beats_total: int | None = None,
    protagonists: list[str] | None = None,
) -> list[VisualBeat]:
    """Genera beats visuales para una lista de escenas.

    - Respeta acts (aproximados por posición en el guion).
    - Numeración global de beat_id.
    - Usa LLM si hay API, con fallback heurístico.
    """
    beats: list[VisualBeat] = []
    total_escenas = len(escenas)
    beat_counter = 0

    for idx, escena in enumerate(escenas):
        if max_beats_total is not None and beat_counter >= max_beats_total:
            break
        act = _act_for_scene(idx, total_escenas)
        # Intentar LLM primero
        llm_beats = _beats_por_escena_llm(escena, act, tema, beat_counter, protagonists=protagonists)
        if not llm_beats:
            llm_beats = _beats_por_escena_fallback(escena, act, beat_counter)

        for b in llm_beats:
            beat_counter += 1
            b.beat_id = beat_counter
            beats.append(b)
            if max_beats_total is not None and beat_counter >= max_beats_total:
                break

    # Normalizar y suavizar shot_role para evitar repeticiones excesivas y valores fuera de SHOT_ROLES
    prev_role: str | None = None
    for b in beats:
        role = (b.shot_role or "").strip().lower()
        if role not in SHOT_ROLES:
            role = "action"
        if prev_role is not None and role == prev_role:
            # Elegir otro rol distinto al anterior (rotación simple)
            candidatos = [r for r in SHOT_ROLES if r != prev_role]
            role = candidatos[(SHOT_ROLES.index(prev_role) + 1) % len(candidatos)] if candidatos else role
        b.shot_role = role
        prev_role = role

    # 1 beat por escena = 1 imagen por parte del guion (evitar mismo prompt / misma escena cada 3 fotos)
    vistos: set[int] = set()
    unico_por_escena: list[VisualBeat] = []
    for b in beats:
        if b.scene not in vistos:
            vistos.add(b.scene)
            unico_por_escena.append(b)
    beats = unico_por_escena
    # Renumerar beat_id
    for i, b in enumerate(beats, start=1):
        b.beat_id = i

    print(f"🎬 Beats visuales generados: {len(beats)} para {len(escenas)} escenas (1 imagen por escena).")
    return beats


def generar_prompts_desde_guion(
    guion_texto: str,
    tema: str,
    segundos_por_imagen: float | None = None,
) -> list[dict]:
    """
    Pipeline compacto pedido en la especificación:

    script -> scene segmentation -> visual beats -> camera selection -> prompt builder

    Devuelve: lista de {beat_id, prompt} lista para generación de imágenes.
    """
    from .scene_splitter import dividir_en_escenas
    from .prompt_builder import prompts_para_beats

    seg = segundos_por_imagen or float(get_duracion_por_imagen())
    escenas = dividir_en_escenas(guion_texto, segundos_por_imagen=seg)
    beats = generar_beats_para_escenas(escenas, tema=tema)
    beat_prompts = prompts_para_beats(beats, video_theme=tema, project_id="compact")
    return [{"beat_id": b.beat_id, "prompt": p, "gen_meta": gm} for b, p, gm in beat_prompts]


def generar_subtitulos_srt(
    beats: list[VisualBeat],
    proyecto: str,
    segundos_por_imagen: float,
) -> Path:
    """Genera un archivo .srt simple (un subtítulo por beat, 1 beat = 1 imagen)."""
    from datetime import timedelta

    def _fmt(t: float) -> str:
        td = timedelta(seconds=t)
        total_ms = int(td.total_seconds() * 1000)
        h, rem = divmod(total_ms, 3600 * 1000)
        m, rem = divmod(rem, 60 * 1000)
        s, ms = divmod(rem, 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    out_dir = BASE / "output" / "subtitles"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{proyecto}.srt"

    lines: list[str] = []
    t = 0.0
    for idx, beat in enumerate(beats, start=1):
        start = t
        end = t + segundos_por_imagen
        t = end
        texto = beat.action or beat.original_text or ""
        texto = texto.strip().replace("\n", " ")
        if not texto:
            continue
        lines.append(str(idx))
        lines.append(f"{_fmt(start)} --> {_fmt(end)}")
        lines.append(texto[:120])
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def guardar_beats(beats: list[VisualBeat], proyecto: str) -> None:
    """Guarda los beats en JSON para inspección/depuración."""
    if not beats:
        return
    out_dir = BASE / "output" / "meta"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"beats_{proyecto}.json"
    data = [
        {
            "beat_id": b.beat_id,
            "scene": b.scene,
            "act": b.act,
            "original_text": b.original_text,
            "action": b.action,
            "emotion": b.emotion,
            "context": b.context,
            "location": b.location,
            "time_of_day": b.time_of_day,
            "shot_role": b.shot_role,
            "camera_type": b.camera_type,
            "camera_position": b.camera_position,
            "camera_distance": b.camera_distance,
            "importance": b.importance,
        }
        for b in beats
    ]
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def cargar_beats(proyecto: str) -> list[VisualBeat]:
    """Carga beats desde disco si existen."""
    path = BASE / "output" / "meta" / f"beats_{proyecto}.json"
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    beats: list[VisualBeat] = []
    for d in raw:
        try:
            beats.append(
                VisualBeat(
                    beat_id=int(d.get("beat_id", 0)),
                    scene=int(d.get("scene", 0)),
                    original_text=str(d.get("original_text") or "").strip(),
                    action=str(d.get("action") or "").strip(),
                    emotion=str(d.get("emotion") or "").strip(),
                    context=str(d.get("context") or "").strip(),
                    location=str(d.get("location") or "").strip(),
                    time_of_day=str(d.get("time_of_day") or "").strip(),
                    shot_role=str(d.get("shot_role") or "").strip(),
                    camera_type=str(d.get("camera_type") or "").strip(),
                    camera_position=str(d.get("camera_position") or "").strip(),
                    camera_distance=str(d.get("camera_distance") or "").strip(),
                    importance=str(d.get("importance") or "").strip(),
                    act=d.get("act"),
                )
            )
        except Exception:
            continue
    return beats


