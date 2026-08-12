"""Visual director: script → structured shots. NO image generation."""
from __future__ import annotations

import json
import os
from typing import Any

from src.documentary.project import append_log, project_dir, save_project
from src.documentary.story_bible import build_story_bible
from src.frame_director import beats_a_frame_specs
from src.frame_prompt_builder import prompt_desde_frame_spec
from src.scene_splitter import dividir_en_escenas
from src.visual_beats import generar_beats_para_escenas


def analyze_visuals(project: dict[str, Any], *, use_llm: bool = True, max_shots: int = 80) -> dict[str, Any]:
    """Build shot list + light story bible. Persists under flow-pack/ (pre-export)."""
    script = str(project.get("script") or "").strip()
    if not script:
        raise ValueError("Generate and approve a script before creating Flow prompts.")
    if not project.get("script_approved"):
        raise ValueError("Approve the script first — then we can build Flow references and shots.")

    from src.documentary.channel import visual_style_from_profile

    snap = project.get("creative_profile_snapshot") if isinstance(project.get("creative_profile_snapshot"), dict) else {}
    style_hint = visual_style_from_profile(snap or None)

    # ~22–28 words/scene → ~50–80 stills for 1300–1800 words
    words = max(1, len(script.split()))
    target_shots = int(max(50, min(max_shots, round(words / 24))))
    # segundos_por_imagen drives palabras_por_escena ≈ seg*3.5
    seg = max(4.0, min(12.0, words / max(1, target_shots) / 2.3))

    prev = os.environ.get("VISUAL_BEATS_LLM_DISABLED")
    if not use_llm:
        os.environ["VISUAL_BEATS_LLM_DISABLED"] = "1"
    try:
        escenas = dividir_en_escenas(script, segundos_por_imagen=seg)
        # Cap scenes if too many
        if len(escenas) > max_shots:
            escenas = escenas[:max_shots]
        beats = generar_beats_para_escenas(escenas, str(project.get("topic") or ""), max_beats_total=max_shots)
        specs = beats_a_frame_specs(beats)
    finally:
        if not use_llm:
            if prev is None:
                os.environ.pop("VISUAL_BEATS_LLM_DISABLED", None)
            else:
                os.environ["VISUAL_BEATS_LLM_DISABLED"] = prev

    shots: list[dict[str, Any]] = []
    for i, (beat, spec) in enumerate(zip(beats, specs), start=1):
        raw_prompt = prompt_desde_frame_spec(spec)
        prompt = _compose_flow_prompt(
            global_hint=style_hint[:220] or "Documentary cinematic realism, 16:9.",
            action=spec.action or beat.action,
            environment=spec.location or beat.location,
            camera=spec.camera_mode or beat.camera_type,
            lighting=beat.time_of_day or "natural light",
            continuity=_continuity_line(i, specs),
            raw=raw_prompt,
        )
        refs = _guess_refs(spec.location or "", beat.original_text or "")
        shots.append(
            {
                "number": i,
                "id": f"SHOT_{i:03d}",
                "expected_file": f"{i:03d}.png",
                "narration": (beat.original_text or "").strip(),
                "shot_type": (beat.camera_type or spec.camera_mode or "medium_shot"),
                "camera": spec.camera_mode or beat.camera_type,
                "action": spec.action or beat.action,
                "location": spec.location or beat.location,
                "emotion": spec.emotion or beat.emotion,
                "continuity": _continuity_line(i, specs),
                "references": refs,
                "prompt": prompt,
                "status": "pending",  # pending|generated|approved|needs_regen
                "scene_id": spec.scene_id,
                "beat_id": spec.beat_id,
            }
        )

    bible = build_story_bible(
        str(project.get("topic") or ""),
        script,
        shots,
        use_llm=use_llm,
        style_override=style_hint,
    )
    # Re-link refs using bible names lightly
    for shot in shots:
        if not shot["references"]:
            shot["references"] = _match_bible_refs(shot, bible)

    root = project_dir(str(project["id"]))
    analysis_path = root / "flow-pack" / "visual_analysis.json"
    analysis_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"shots": shots, "story_bible": bible, "target_shots": target_shots, "scene_count": len(escenas)}
    analysis_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    project["visual_analysis"] = {"shot_count": len(shots), "path": str(analysis_path.relative_to(root))}
    save_project(project)
    append_log(str(project["id"]), f"visual analysis shots={len(shots)}")
    return {**project, "_analysis": payload}


def load_analysis(project_id: str) -> dict[str, Any]:
    path = project_dir(project_id) / "flow-pack" / "visual_analysis.json"
    if not path.exists():
        raise FileNotFoundError("visual_analysis.json missing — run Visual Director first")
    return json.loads(path.read_text(encoding="utf-8"))


def _continuity_line(i: int, specs: list) -> str:
    if i <= 1:
        return "opening shot"
    prev = specs[i - 2]
    cur = specs[i - 1]
    bits = []
    if (prev.location or "").strip().lower() == (cur.location or "").strip().lower():
        bits.append("same location as previous")
    else:
        bits.append("location change")
    bits.append(f"follow from shot {i-1:03d}")
    return "; ".join(bits)


def _guess_refs(location: str, text: str) -> list[str]:
    refs: list[str] = []
    low = f"{location} {text}".lower()
    if any(k in low for k in ("office", "hq", "headquarters", "workspace")):
        refs.append("LOC_001")
    if any(k in low for k in ("press", "conference", "stage", "media")):
        refs.append("LOC_002")
    if any(k in low for k in ("report", "chart", "deck", "document", "balance")):
        refs.append("OBJ_001")
    return refs


def _match_bible_refs(shot: dict, bible: dict) -> list[str]:
    text = f"{shot.get('narration')} {shot.get('location')} {shot.get('action')}".lower()
    out: list[str] = []
    for group in ("characters", "locations", "important_objects"):
        for ent in bible.get(group) or []:
            name = str(ent.get("name") or "").lower()
            if name and name in text:
                out.append(str(ent["id"]))
    return out[:4]


def _compose_flow_prompt(
    *,
    global_hint: str,
    action: str,
    environment: str,
    camera: str,
    lighting: str,
    continuity: str,
    raw: str,
) -> str:
    # Keep prompts clear and not absurdly long
    core = [
        f"GLOBAL STYLE: {global_hint}",
        f"CURRENT ACTION: {(action or 'documentary moment').strip()[:220]}",
        f"ENVIRONMENT: {(environment or 'relevant setting').strip()[:160]}",
        f"CAMERA: {(camera or 'medium shot').strip()[:80]}",
        f"LIGHTING: {(lighting or 'natural').strip()[:60]}",
        f"CONTINUITY: {(continuity or '').strip()[:120]}",
        "REFERENCE: Prefer previously generated master refs for recurring people/places; do not reinvent wardrobe or architecture.",
    ]
    # Trim raw structural hints
    raw_short = " ".join((raw or "").split())[:500]
    if raw_short:
        core.append(f"DETAIL: {raw_short}")
    return "\n".join(core)
