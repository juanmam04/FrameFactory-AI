"""
Capa de continuidad visual secuencial: estado global del storyboard, resolución de
ubicación/cámara/personaje y construcción de prompts con bloque de continuidad explícito.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field, replace
from typing import Any

from .action_scene import action_prompt_appendix
from .config_loader import get_character_bible, get_visual_bible
from .location_visual_enrichment import maybe_enrich_location_prompt
from .visual_beats import VisualBeat

# --- Dataclasses de estado y resolución -------------------------------------


@dataclass
class StoryboardState:
    current_location_id: str | None = None
    current_location_prompt: str | None = None
    current_scene_type: str | None = None
    current_time_of_day: str | None = None
    current_mood: str | None = None
    current_characters: list[str] = field(default_factory=list)
    protagonist_profile: dict[str, Any] = field(default_factory=dict)
    wardrobe_state: dict[str, Any] = field(default_factory=dict)
    last_camera: str | None = None
    last_action: str | None = None
    last_prompt_summary: str | None = None
    continuity_notes: list[str] = field(default_factory=list)
    project_id: str = ""
    video_theme: str | None = None


@dataclass
class ResolvedLocation:
    location_prompt: str
    location_id: str
    inherited_from_previous: bool
    changed: bool
    confidence: float
    source: str  # beat.location | text_inference | state_inheritance


@dataclass
class ResolvedCamera:
    chosen_camera: str
    inherited_from_beat: bool
    changed_due_to_repeat: bool
    previous_camera: str | None
    reason: str


@dataclass
class SceneContinuity:
    scene_index: int
    raw_location: str
    resolved_location: str
    location_changed: bool
    previous_location: str | None
    raw_camera: str
    resolved_camera: str
    previous_camera: str | None
    action: str
    previous_action: str | None
    characters_present: list[str]
    protagonist_locked_description: str
    continuity_block: str
    symbolic_overlay_allowed: bool
    symbolic_overlay_reason: str
    sanitized_symbolic_descriptions: list[str]
    seed_material: str
    protagonist_signature: str


# --- Normalización -----------------------------------------------------------


def location_id_from_text(text: str) -> str:
    t = (text or "").strip().lower()
    t = re.sub(r"[^a-z0-9áéíóúüñ\s]+", " ", t, flags=re.I)
    t = re.sub(r"\s+", "_", t.strip())[:80]
    return t or "unknown_place"


def stable_seed_int(project_id: str, beat_id: int, location_id: str, protagonist_signature: str) -> int:
    raw = f"{project_id}\0{beat_id}\0{location_id}\0{protagonist_signature}"
    h = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return int(h[:8], 16) % (2**31)


def comfyui_seed_from_material(seed_material: str) -> int:
    """Semilla determinista a partir del string ya compuesto (proyecto|beat|location|firma)."""
    h = hashlib.sha256((seed_material or "default").encode("utf-8")).hexdigest()
    return int(h[:8], 16) % (2**31)


# --- Señales de cambio de locación ------------------------------------------


_LOCATION_CHANGE_PATTERNS = [
    r"\bentra(r)?\s+(a|en|al|del)\b",
    r"\bentra(r)?\s+al\s+edificio\b",
    r"\bsale(r)?\s+de\b",
    r"\bllega(r)?\s+a\b",
    r"\bva(r)?\s+a\b",
    r"\bnueva\s+ubicaci[oó]n\b",
    r"\botro\s+lugar\b",
    r"\bdentro\s+del\b",
    r"\ben\s+el\s+pasillo\b",
    r"\ben\s+el\s+living\b",
    r"\ben\s+la\s+sala\b",
    r"\bapartamento\b",
    r"\bedificio\b",
    r"\bcambia(r)?\s+de\s+lugar\b",
]


def signals_strong_location_change(text: str) -> bool:
    t = (text or "").lower()
    return any(re.search(p, t) for p in _LOCATION_CHANGE_PATTERNS)


# --- Cámara: mapeo desde beat (LLM) -----------------------------------------

_BEAT_CAMERA_TO_PROMPT: dict[str, str] = {
    "pov": "close up",
    "over_the_shoulder": "over the shoulder",
    "wide_shot": "wide shot",
    "medium_shot": "medium shot",
    "close_up": "close up",
    "side_angle": "side shot",
    "top_down": "top down",
    "low_angle": "low angle",
    "rear_view": "rear view",
    "environment_shot": "wide shot",
}


def _camera_options_list() -> list[str]:
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


def map_beat_camera_fields_to_prompt(beat: VisualBeat) -> str | None:
    ct = (beat.camera_type or "").strip().lower()
    if ct in _BEAT_CAMERA_TO_PROMPT:
        return _BEAT_CAMERA_TO_PROMPT[ct]
    return None


def resolve_camera(
    beat: VisualBeat,
    full_meta: dict[str, Any],
    prev_state: StoryboardState,
    cameras: list[str] | None = None,
) -> ResolvedCamera:
    cameras = cameras or _camera_options_list()
    if not cameras:
        cameras = ["medium shot"]

    raw = (beat.camera_type or "").strip()
    from_beat = map_beat_camera_fields_to_prompt(beat)
    if from_beat:
        chosen = from_beat
        inherited_from_beat = True
        reason = "mapped from beat.camera_type"
    else:
        chosen = (full_meta.get("camera_priority") or cameras[0]).strip()
        inherited_from_beat = False
        reason = "from narrative camera_priority / default"

    prev = prev_state.last_camera
    changed_due_to_repeat = False
    if chosen == prev and len(cameras) > 1:
        # Alternativa determinista por índice de escena (evita random)
        idx = cameras.index(chosen) if chosen in cameras else 0
        for offset in range(1, len(cameras)):
            alt = cameras[(idx + offset) % len(cameras)]
            if alt != prev:
                chosen = alt
                changed_due_to_repeat = True
                reason += "; alternated to avoid consecutive duplicate"
                break

    return ResolvedCamera(
        chosen_camera=chosen,
        inherited_from_beat=inherited_from_beat,
        changed_due_to_repeat=changed_due_to_repeat,
        previous_camera=prev,
        reason=reason,
    )


# --- Ubicación ---------------------------------------------------------------

def resolve_location(
    beat: VisualBeat,
    prev_state: StoryboardState,
    base_meta: dict[str, Any],
) -> ResolvedLocation:
    raw_loc = (getattr(beat, "location", None) or "").strip()
    inferred = (base_meta.get("location") or "").strip() or "clear location that matches the story"
    blob = f"{beat.original_text} {beat.action} {beat.context}"

    if raw_loc:
        lid = location_id_from_text(raw_loc)
        changed = prev_state.current_location_id is None or lid != prev_state.current_location_id
        return ResolvedLocation(
            location_prompt=raw_loc,
            location_id=lid,
            inherited_from_previous=False,
            changed=changed,
            confidence=0.95,
            source="beat.location",
        )

    if prev_state.current_location_prompt and not signals_strong_location_change(blob):
        return ResolvedLocation(
            location_prompt=prev_state.current_location_prompt,
            location_id=prev_state.current_location_id or location_id_from_text(prev_state.current_location_prompt),
            inherited_from_previous=True,
            changed=False,
            confidence=0.75,
            source="state_inheritance",
        )

    lid = location_id_from_text(inferred)
    changed = prev_state.current_location_id is None or lid != prev_state.current_location_id
    return ResolvedLocation(
        location_prompt=inferred,
        location_id=lid,
        inherited_from_previous=False,
        changed=changed,
        confidence=0.6,
        source="text_inference",
    )


# --- Overlay simbólico: compatibilidad ---------------------------------------

# Tipos "exteriores" / masivos donde empty_room_tension rompe literalidad
_EXTERIOR_LIKE_SCENE_TYPES = frozenset(
    {
        "city_street",
        "generic_exterior",
        "war_street",
        "press_conference",
    }
)

_DISALLOWED_DEVICE_FOR_SCENE: dict[str, frozenset[str]] = {
    "city_street": frozenset({"empty_room_tension"}),
    "generic_exterior": frozenset({"empty_room_tension"}),
    "war_street": frozenset({"empty_room_tension"}),
    "press_conference": frozenset({"empty_room_tension"}),
}


def symbolic_overlay_allowed(scene_type: str, visual_device: str) -> bool:
    vd = (visual_device or "").strip()
    st = (scene_type or "").strip()
    bad = _DISALLOWED_DEVICE_FOR_SCENE.get(st)
    if bad and vd in bad:
        return False
    if vd == "empty_room_tension" and st in _EXTERIOR_LIKE_SCENE_TYPES:
        return False
    return True


def resolve_interior_subtype(
    resolved_location: str,
    scene_type: str,
    action: str = "",
    text: str = "",
) -> str:
    """Subtipo interior liviano para sanitizar overlays con más semántica."""
    blob = " ".join(
        x.lower().strip()
        for x in (resolved_location or "", scene_type or "", action or "", text or "")
        if x
    )
    if any(k in blob for k in ("pasillo", "hallway", "corridor")):
        return "hallway"
    if any(k in blob for k in ("living", "sala", "living room", "sofa", "sofá")):
        return "living_room"
    if any(k in blob for k in ("dormitorio", "bedroom", "cuarto", "habitación", "habitacion", "cama", "bed")):
        return "bedroom"
    if any(k in blob for k in ("oficina", "office", "escritorio", "meeting room", "boardroom")):
        return "office"
    return "generic_interior"


_INTERIOR_SUBTYPE_FORBIDDEN_HINTS: dict[str, tuple[str, ...]] = {
    "hallway": ("desk", "desk lamp", "bed", "sofa", "chair facing the protagonist"),
    "living_room": ("bed", "bedroom"),
    "bedroom": ("coffee table", "living room", "sofa-centric"),
    "office": ("bed", "bedroom", "sofa"),
    "generic_interior": (),
}


def sanitize_symbolic_elements_by_subtype(
    interior_subtype: str,
    scene_type: str,
    visual_device: str,
    symbolic_tags: list[str],
    symbolic_descriptions: list[str],
) -> tuple[list[str], list[str], str]:
    """Compatibilidad fina por subtipo interior; si hay duda, neutralizar."""
    if scene_type in _EXTERIOR_LIKE_SCENE_TYPES:
        return sanitize_symbolic_elements(scene_type, visual_device, symbolic_tags, symbolic_descriptions)

    subtype = interior_subtype if interior_subtype in _INTERIOR_SUBTYPE_FORBIDDEN_HINTS else "generic_interior"
    descs = list(symbolic_descriptions or [])
    forbidden = _INTERIOR_SUBTYPE_FORBIDDEN_HINTS.get(subtype, ())
    if forbidden:
        lowered = [d.lower() for d in descs]
        if any(any(f in d for f in forbidden) for d in lowered):
            descs = []

    if descs:
        return list(symbolic_tags), descs, f"overlay compatible with interior subtype {subtype}"

    if subtype == "hallway":
        return (
            [],
            [
                "narrow corridor walls and doors with overhead light",
                "subtle hallway tension with clean floor and perspective depth",
            ],
            "neutralized for hallway subtype compatibility",
        )
    if subtype == "living_room":
        return (
            [],
            [
                "living room continuity with sofa, lamp and coffee table",
                "subtle phone-focused tension without sleep-area props",
            ],
            "neutralized for living_room subtype compatibility",
        )
    if subtype == "bedroom":
        return (
            [],
            [
                "bedroom continuity with bed, side lamp and window",
                "quiet indoor tension consistent with sleeping area",
            ],
            "neutralized for bedroom subtype compatibility",
        )
    if subtype == "office":
        return (
            [],
            [
                "office continuity with desk, monitor and papers",
                "workplace tension without domestic furniture",
            ],
            "neutralized for office subtype compatibility",
        )
    return (
        [],
        [
            "subtle indoor atmosphere with walls, floor and door/window continuity",
        ],
        "neutralized for generic interior subtype",
    )


def sanitize_symbolic_elements(
    scene_type: str,
    visual_device: str,
    symbolic_tags: list[str],
    symbolic_descriptions: list[str],
) -> tuple[list[str], list[str], str]:
    if symbolic_overlay_allowed(scene_type, visual_device):
        return list(symbolic_tags), list(symbolic_descriptions), "overlay compatible with scene_type"

    neutral_desc = [
        "subtle atmospheric tension consistent with the outdoor or public setting",
        "no indoor furniture that contradicts the exterior",
    ]
    return [], neutral_desc, f"filtered: device {visual_device!r} incompatible with scene_type {scene_type!r}"


# --- Personaje: lock y tienda de estado -------------------------------------


@dataclass
class CharacterSlot:
    stable_description: str
    current_outfit: str
    body_preset: str
    allowed_variations: str
    last_seen_scene: int


class CharacterStateStore:
    def __init__(self) -> None:
        self.by_character_key: dict[str, CharacterSlot] = {}

    def ensure_protagonist(self, scene_index: int) -> CharacterSlot:
        if "protagonist" in self.by_character_key:
            self.by_character_key["protagonist"].last_seen_scene = scene_index
            return self.by_character_key["protagonist"]
        bible = get_character_bible().get("characters", {}).get("protagonist", {})
        body = bible.get("body_preset", "teen")
        outfit = bible.get("outfit_base", "casual_dark")
        sil = bible.get("silhouette_hint", "")
        color = bible.get("color_identity", "")
        acc = bible.get("accessory", "none")
        desc = f"{body} body, {outfit} outfit, {sil} silhouette, {color} color identity"
        if acc and acc != "none":
            desc += f", accessory: {acc}"
        slot = CharacterSlot(
            stable_description=desc,
            current_outfit=outfit,
            body_preset=body,
            allowed_variations="expression, pose, lighting angle",
            last_seen_scene=scene_index,
        )
        self.by_character_key["protagonist"] = slot
        return slot

    def _outfit_change_explicit(self, text: str) -> bool:
        t = (text or "").lower()
        return any(
            k in t
            for k in (
                "se cambia",
                "nueva ropa",
                "nuevo traje",
                "uniforme",
                "se pone un traje",
                "gala",
                "pijama",
            )
        )

    def update_protagonist_from_beat(self, beat: VisualBeat, scene_index: int, mapper_outfit_override: str | None) -> None:
        slot = self.ensure_protagonist(scene_index)
        blob = f"{beat.original_text} {beat.action}"
        # No pisar outfit por scene_type salvo evento explícito o override fuerte del guion
        if mapper_outfit_override and self._outfit_change_explicit(blob):
            slot.current_outfit = mapper_outfit_override
            slot.stable_description = re.sub(
                r"[^,]+ outfit",
                f"{mapper_outfit_override} outfit",
                slot.stable_description,
                count=1,
            )
        slot.last_seen_scene = scene_index

    def describe_secondary(self, key: str, scene_index: int) -> str:
        if key in self.by_character_key:
            self.by_character_key[key].last_seen_scene = scene_index
            return self.by_character_key[key].stable_description
        from .config_loader import get_role_library

        roles = get_role_library().get("roles", {})
        chars = get_character_bible().get("characters", {})
        if key in chars:
            d = chars[key]
            desc = f"{d.get('body_preset', 'adult')} body, {d.get('outfit_base', 'casual_dark')} outfit, {d.get('silhouette_hint', '')} silhouette"
        elif key in roles:
            d = roles[key]
            desc = f"{d.get('body_preset', 'adult')} body, {d.get('outfit_base', 'casual_dark')} outfit, {d.get('silhouette_hint', '')} silhouette"
        else:
            desc = f"flat stylized character ({key})"
        self.by_character_key[key] = CharacterSlot(
            stable_description=desc,
            current_outfit="",
            body_preset="",
            allowed_variations="pose",
            last_seen_scene=scene_index,
        )
        return desc


def build_protagonist_lock(store: CharacterStateStore, scene_index: int) -> str:
    slot = store.ensure_protagonist(scene_index)
    return (
        "CHARACTER LOCK (protagonist — do not change between shots unless script explicitly changes wardrobe):\n"
        f"Locked appearance: {slot.stable_description}.\n"
        f"Allowed to vary: {slot.allowed_variations}.\n"
        "Keep same face design, head shape, body proportions and base outfit as previous shots in this story."
    )


def resolve_character_state(
    store: CharacterStateStore,
    beat: VisualBeat,
    scene_index: int,
    scene_characters: list[str],
    character_overrides: dict[str, dict[str, str]],
) -> str:
    # Solo usar override de outfit del mapper si el texto lo justifica
    po = (character_overrides or {}).get("protagonist", {})
    outfit_ov = po.get("outfit_base")
    store.update_protagonist_from_beat(beat, scene_index, outfit_ov)
    lines = [build_protagonist_lock(store, scene_index)]
    for ck in scene_characters:
        if ck == "protagonist" or ck == "extras":
            continue
        desc = store.describe_secondary(ck, scene_index)
        lines.append(f"- {ck.replace('_', ' ').title()} (consistent if recurring): {desc}.")
    return "\n".join(lines)


# --- Contexto resuelto y actualización de estado -----------------------------


def resolve_scene_context(
    scene_index: int,
    beat: VisualBeat,
    base_meta: dict[str, Any],
    full_meta: dict[str, Any],
    state: StoryboardState,
    char_store: CharacterStateStore,
) -> SceneContinuity:
    res_loc = resolve_location(beat, state, base_meta)
    _loc_ctx = " ".join(
        x for x in (beat.original_text or "", beat.action or "", beat.context or "") if x
    )
    enriched_prompt = maybe_enrich_location_prompt(
        res_loc.location_prompt,
        context=_loc_ctx,
        scene_type=(base_meta.get("scene_type") or ""),
    )
    res_loc = replace(res_loc, location_prompt=enriched_prompt)
    cameras = _camera_options_list()
    res_cam = resolve_camera(beat, full_meta, state, cameras)

    scene_type = base_meta.get("scene_type") or "generic_interior"
    visual_device = full_meta.get("visual_device") or "literal"
    tags = full_meta.get("symbolic_tags") or []
    descs = full_meta.get("symbolic_descriptions") or []
    interior_subtype = resolve_interior_subtype(
        resolved_location=res_loc.location_prompt,
        scene_type=scene_type,
        action=(beat.action or ""),
        text=(beat.original_text or ""),
    )
    _sym_tags, sym_descs, sym_reason = sanitize_symbolic_elements_by_subtype(
        interior_subtype=interior_subtype,
        scene_type=scene_type,
        visual_device=visual_device,
        symbolic_tags=tags,
        symbolic_descriptions=descs,
    )

    action = (beat.action or beat.original_text or "").replace("\n", " ").strip()[:220]
    chars = list(base_meta.get("scene_characters") or ["protagonist"])

    character_lock_block = resolve_character_state(
        char_store, beat, scene_index, chars, base_meta.get("character_overrides") or {}
    )
    protagonist_sig = char_store.ensure_protagonist(scene_index).stable_description
    seed_material = f"{state.project_id}|{beat.beat_id}|{res_loc.location_id}|{location_id_from_text(protagonist_sig)}"

    cont_lines: list[str] = []
    if scene_index == 0:
        cont_lines.append("This is the first shot of the sequence; establish the environment and protagonist clearly.")
    else:
        prev_loc = state.current_location_prompt or "previous location"
        cont_lines.append(f"Previous scene context: {state.last_prompt_summary or 'continuation of the same story'}.")
        cont_lines.append(f"Previous location was: {prev_loc}.")
        if res_loc.inherited_from_previous:
            cont_lines.append(
                "Maintain the SAME environment as the previous shot unless action explicitly moves; "
                "keep background architecture, lighting direction and spatial continuity."
            )
        elif res_loc.changed:
            cont_lines.append(
                "Location has changed from the previous shot; show a new setting clearly while keeping the same protagonist design."
            )
        cont_lines.append("Keep protagonist appearance unchanged from CHARACTER LOCK.")
        cont_lines.append(f"Current scene progression: {action}")

    continuity_block = "CONTINUITY FROM PREVIOUS SCENE:\n" + "\n".join(cont_lines)

    return SceneContinuity(
        scene_index=scene_index,
        raw_location=(beat.location or "").strip(),
        resolved_location=res_loc.location_prompt,
        location_changed=res_loc.changed,
        previous_location=state.current_location_prompt,
        raw_camera=(beat.camera_type or "").strip(),
        resolved_camera=res_cam.chosen_camera,
        previous_camera=res_cam.previous_camera,
        action=action,
        previous_action=state.last_action,
        characters_present=chars,
        protagonist_locked_description=character_lock_block,
        continuity_block=continuity_block,
        symbolic_overlay_allowed=symbolic_overlay_allowed(scene_type, visual_device),
        symbolic_overlay_reason=f"{sym_reason}; subtype={interior_subtype}",
        sanitized_symbolic_descriptions=sym_descs,
        seed_material=seed_material,
        protagonist_signature=protagonist_sig,
    )


def update_storyboard_state(
    state: StoryboardState,
    ctx: SceneContinuity,
    full_meta: dict[str, Any],
    beat: VisualBeat | None = None,
) -> None:
    state.current_location_id = location_id_from_text(ctx.resolved_location)
    state.current_location_prompt = ctx.resolved_location
    state.current_scene_type = full_meta.get("scene_type") or state.current_scene_type
    if beat and (beat.time_of_day or "").strip():
        state.current_time_of_day = beat.time_of_day.strip()
    state.current_mood = full_meta.get("mood") or state.current_mood
    state.current_characters = list(ctx.characters_present)
    state.last_camera = ctx.resolved_camera
    state.last_action = ctx.action
    state.last_prompt_summary = f"{ctx.resolved_location[:120]} — {ctx.action[:80]}"
    note = []
    if ctx.location_changed:
        note.append("location_updated")
    if ctx.resolved_camera != ctx.previous_camera:
        note.append("camera_updated")
    state.continuity_notes.extend(note)


def construir_prompt_secuencial(
    ctx: SceneContinuity,
    full_meta: dict[str, Any],
    characters_in_scene_block: str,
) -> str:
    vb = get_visual_bible()
    style = (vb.get("style_lock") or vb.get("estilo_base") or "").strip()
    theme = full_meta.get("thematic_context") or "generic"
    visual_device = full_meta.get("visual_device") or "literal"
    rep_mode = full_meta.get("narrative_representation_mode") or "literal"
    scene_focus = full_meta.get("scene_focus") or "protagonist_face"

    current_scene_lines = [
        "CURRENT SCENE:",
        f"Location: {ctx.resolved_location}.",
        f"Action: {ctx.action}.",
        f"Mood: {full_meta.get('mood') or 'neutral'}.",
    ]
    kv = (full_meta.get("key_visual") or "").strip()
    if kv:
        current_scene_lines.append(f"Key visual element: {kv}.")

    parts = [
        "STYLE LOCK:\n" + style,
        ctx.protagonist_locked_description.strip(),
    ]
    if (characters_in_scene_block or "").strip():
        parts.append(characters_in_scene_block.strip())

    parts.append(ctx.continuity_block.strip())
    parts.append("\n".join(current_scene_lines).strip())

    parts.append(
        "Narrative device:\n"
        f"{visual_device}.\n"
        "Representation mode:\n"
        f"{rep_mode}.\n"
        "Scene focus:\n"
        f"{scene_focus}."
    )

    if full_meta.get("action_scene_dynamic"):
        parts.append(action_prompt_appendix())

    if ctx.sanitized_symbolic_descriptions and ctx.symbolic_overlay_allowed:
        sym = ", ".join(ctx.sanitized_symbolic_descriptions)
        parts.append(f"SYMBOLIC OVERLAY (compatible):\n{sym}.\n({ctx.symbolic_overlay_reason})")
    elif ctx.sanitized_symbolic_descriptions:
        sym = ", ".join(ctx.sanitized_symbolic_descriptions)
        parts.append(f"ATMOSPHERE (neutral, no contradictory props):\n{sym}.")

    # Cámara limpia: solo la resuelta; conservar posición si aporta.
    cam_line = f"{ctx.resolved_camera}"
    beat_pos = (full_meta.get("_beat_camera_position") or "").strip()
    if beat_pos:
        cam_line += f", {beat_pos} position"
    parts.append(f"CAMERA:\n{cam_line}.")

    parts.append(
        "HARD RULES:\n"
        "One clear narrative image.\n"
        "Clear visual focus.\n"
        "No empty background.\n"
        "16:9 frame.\n"
        "Do not contradict the continuity block or character lock."
    )

    parts.append(f"Theme:\n{theme}.")

    return "\n\n".join(p for p in parts if p)


def initial_storyboard_state(project_id: str = "", video_theme: str | None = None) -> StoryboardState:
    return StoryboardState(project_id=project_id or "", video_theme=video_theme)


def apply_beat_camera_position_hint(beat: VisualBeat, meta: dict[str, Any]) -> dict[str, Any]:
    m = dict(meta)
    if (beat.camera_position or "").strip():
        m["_beat_camera_position"] = beat.camera_position.strip()
    return m
