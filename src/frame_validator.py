"""Validador automático V2 para imágenes generadas desde FrameSpec."""
from __future__ import annotations

import base64
import os
import re
import unicodedata
from dataclasses import dataclass, asdict
from pathlib import Path

from PIL import Image, ImageStat

from .frame_spec import FrameSpec


@dataclass
class ValidationResult:
    frame_id: int
    is_valid: bool
    score: float
    event_match_score: float
    action_score: float
    camera_consistency_score: float
    narrative_clarity_score: float
    repetition_score: float
    reasons: list[str]
    caption: str = ""


def _is_blank_or_black(path: Path) -> bool:
    with Image.open(path) as img:
        rgb = img.convert("RGB")
        stat = ImageStat.Stat(rgb)
        mean = stat.mean
        stddev = stat.stddev
        # Imagen muy oscura o muy plana => sospecha de frame roto/negro
        if sum(mean) / 3 < 10:
            return True
        if sum(stddev) / 3 < 4:
            return True
    return False


def _phash_like(path: Path) -> int:
    """Hash perceptual simple (aHash 8x8)."""
    with Image.open(path) as img:
        g = img.convert("L").resize((8, 8))
        pixels = list(g.getdata())
    avg = sum(pixels) / len(pixels)
    bits = 0
    for p in pixels:
        bits = (bits << 1) | (1 if p > avg else 0)
    return bits


def _hamming(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def _normalizar(txt: str) -> str:
    t = (txt or "").lower().strip()
    t = unicodedata.normalize("NFKD", t)
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    t = re.sub(r"\s+", " ", t)
    return t


def _tokens_relevantes(txt: str) -> set[str]:
    t = _normalizar(txt)
    parts = re.split(r"[^a-zA-Záéíóúñ0-9]+", t)
    return {p for p in parts if len(p) >= 3}


def _caption_vlm(image_path: Path, spec: FrameSpec) -> str:
    """
    Caption semántico de la imagen usando VLM (OpenAI) si hay API key.
    Si no hay key, devuelve string vacío y el validador cae en heurísticas más conservadoras.
    """
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return ""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        raw = image_path.read_bytes()
        b64 = base64.b64encode(raw).decode("utf-8")
        model = os.getenv("OPENAI_VISION_MODEL", "gpt-4o-mini")
        prompt = (
            "Describe SOLAMENTE lo que se ve en esta imagen en español, con foco en: "
            "personas, acciones físicas, postura (parados/caídos), entorno (interior/exterior/callejón/oficina/etc), "
            "y evidencia crítica (sangre/heridas/arma/cuerpo en suelo). "
            "No inventes nada. Máximo 120 palabras."
        )
        r = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                ]}
            ],
            temperature=0.0,
            max_tokens=220,
        )
        return (r.choices[0].message.content or "").strip()
    except Exception:
        return ""


def _contains_any(texto: str, palabras: tuple[str, ...]) -> bool:
    t = _normalizar(texto)
    return any(p in t for p in palabras)


def _semantic_phrase_match(caption: str, phrase: str) -> bool:
    cap = _normalizar(caption)
    p = _normalizar(phrase)
    if not p:
        return True
    if p in cap:
        return True

    # Alias semánticos para evitar falsos negativos por wording del VLM.
    alias_groups: list[tuple[tuple[str, ...], tuple[str, ...]]] = [
        (
            ("amigo", "friend", "compañero", "companero", "persona"),
            ("cuerpo", "persona", "personaje", "hombre", "mujer", "figura"),
        ),
        (
            ("herido", "injured", "lesionado", "wounded"),
            ("herido", "herida", "sangre", "ensangrent", "caido", "caído", "tendido", "suelo"),
        ),
        (
            ("llegada", "urgente", "approaching", "aproxim"),
            ("corriendo", "avanzando", "acercando", "mano extendida", "postura activa", "movimiento"),
        ),
        (
            ("charcos", "manchas", "sangre"),
            ("sangre", "ensangrent", "mancha roja", "charco"),
        ),
    ]
    for needs, accepts in alias_groups:
        if any(n in p for n in needs) and any(a in cap for a in accepts):
            return True

    toks = _tokens_relevantes(p)
    if not toks:
        return True
    cap_words = set(re.split(r"[^a-z0-9]+", cap))
    cap_words = {w for w in cap_words if w}

    def _token_hit(tok: str) -> bool:
        if tok in cap:
            return True
        # Match por raíz para variaciones simples: caido/caida, herido/herida, etc.
        root = tok[:4]
        if len(root) >= 4 and any(w.startswith(root) for w in cap_words):
            return True
        return False

    return sum(1 for tok in toks if _token_hit(tok)) >= max(1, min(2, len(toks)))


def _es_requisito_meta(frase: str) -> bool:
    """Frases demasiado abstractas para matchear en caption VLM; no penalizan score."""
    x = _normalizar(frase)
    return any(
        k in x
        for k in (
            "entorno contextual legible",
            "evento central inequivoco",
            "evento central inequívoco",
            "accion en progreso (mid-action)",
            "acción en progreso (mid-action)",
            "personaje principal",
            "reaccion fisica creible",
            "reacción física creíble",
            "cuerpo o victima claramente visible",
            "cuerpo o víctima claramente visible",
            "texto/código legible en pantalla",
            "ambiente de escritorio o sala de servidores",
            "movimiento de juego visible",
            "césped o líneas de campo si aplica",
            "evidencia de violencia o herida en pantalla",
            "persona herida o en peligro visible",
            "acción visible en el lugar del beat",
        )
    )


def _mide_evento_en_caption(spec: FrameSpec, caption: str) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 1.0
    cap = _normalizar(caption)

    # 1) Entidades obligatorias
    faltantes_ent = []
    for ent in spec.must_visible_entities:
        if _es_requisito_meta(ent):
            continue
        if not _semantic_phrase_match(cap, ent):
            faltantes_ent.append(ent)
    if faltantes_ent:
        reasons.append(f"faltan entidades obligatorias: {', '.join(faltantes_ent[:4])}")
        score -= min(0.55, 0.18 * len(faltantes_ent))

    # 2) Evidencia crítica
    faltantes_evi = []
    for evi in spec.must_visible_evidence:
        if _es_requisito_meta(evi):
            continue
        if not _semantic_phrase_match(cap, evi):
            faltantes_evi.append(evi)
    if faltantes_evi:
        reasons.append(f"falta evidencia visual obligatoria: {', '.join(faltantes_evi[:4])}")
        score -= min(0.65, 0.22 * len(faltantes_evi))

    # Reglas explícitas críticas: sangre/herida/cuerpo en suelo si el spec lo pide
    spec_all = _normalizar(
        " ".join(spec.must_visible_evidence + spec.must_visible_entities + [spec.event_core, spec.action, spec.location])
    )
    if any(k in spec_all for k in ("sangre", "desangr", "herid", "herida")):
        if not _contains_any(cap, ("sangre", "ensangrent", "herida", "herido", "desangr")):
            reasons.append("no se observa sangre/herida pese a ser evidencia crítica")
            score -= 0.45
    if any(k in spec_all for k in ("suelo", "cuerpo caído", "cuerpo caido", "yace", "tirado")):
        if not _contains_any(
            cap,
            ("en el suelo", "tirado", "caído", "caido", "yace", "tendido", "boca abajo", "en la calle", "calle"),
        ):
            reasons.append("no se ve cuerpo en el suelo pese a ser evidencia crítica")
            score -= 0.40

    return max(0.0, score), reasons


def _mide_entorno(spec: FrameSpec, caption: str) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 1.0
    loc = _normalizar(spec.location)
    cap = _normalizar(caption)

    pide_callejon = any(k in loc for k in ("callejón", "callejon", "alley", "calle "))
    ve_interior = _contains_any(cap, ("interior", "habitación", "habitacion", "sala", "cocina", "oficina", "cuarto"))
    ve_exterior = _contains_any(cap, ("calle", "callejón", "callejon", "exterior", "alley", "vereda"))

    if pide_callejon and ve_interior and not ve_exterior:
        reasons.append("mismatch de entorno: se pidió callejón/exterior y se detecta interior")
        score -= 0.75

    return max(0.0, score), reasons


def _mide_accion_vs_pose(spec: FrameSpec, caption: str) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 1.0
    cap = _normalizar(caption)

    # Trabajo en PC / stream: manos + teclado/pantalla cuenta como acción
    if _contains_any(cap, ("teclado", "monitor", "pantalla", "código", "codigo")) and _contains_any(
        cap, ("manos", "dedos", "escribiendo", "escribe", "mecanografía")
    ):
        return max(0.0, score), reasons

    verbos_accion = (
        "corre", "corriendo", "cae", "cayendo", "extiende", "agacha", "arrodilla",
        "sostiene", "arrastra", "golpea", "apunta", "teclea", "grita",
        "avanza", "avanzando", "acerca", "acercando", "postura activa", "mano extendida",
        "movimiento", "en movimiento", "pie levantado",
        "salta", "saltando", "lanza", "señala", "teclea", "dispara", "usa",
        "concentrad", "leyendo", "escribiendo",
    )
    signos_pose = ("parado", "de pie", "posando", "mirando a cámara", "quieto", "estático", "estatico")

    if not _contains_any(cap, verbos_accion):
        reasons.append("no hay acción física clara en caption")
        score -= 0.45
    if _contains_any(cap, signos_pose) and not _contains_any(cap, verbos_accion):
        reasons.append("la imagen parece pose estática")
        score -= 0.45

    # Si el spec exige motion fuerte y caption no lo refleja, penalizar más
    if _contains_any(_normalizar(spec.physical_motion), ("urgente", "movimiento", "corre", "frena", "mid-action")):
        if not _contains_any(cap, verbos_accion):
            score -= 0.25

    return max(0.0, score), reasons


def validar_frame(
    spec: FrameSpec,
    image_path: Path,
    prev_image_path: Path | None = None,
    caption_override: str | None = None,
) -> ValidationResult:
    reasons: list[str] = []
    event_match_score = 1.0
    action_score = 1.0
    camera_consistency_score = 1.0
    narrative_clarity_score = 1.0
    repetition_score = 1.0

    caption = caption_override if caption_override is not None else (_caption_vlm(image_path, spec) if image_path.exists() else "")

    if not image_path.exists():
        return ValidationResult(
            frame_id=spec.frame_id,
            is_valid=False,
            score=0.0,
            event_match_score=0.0,
            action_score=0.0,
            camera_consistency_score=0.0,
            narrative_clarity_score=0.0,
            repetition_score=0.0,
            reasons=["imagen no existe"],
            caption=caption,
        )

    if _is_blank_or_black(image_path):
        reasons.append("imagen vacía/negra o sin detalle")
        narrative_clarity_score -= 0.7
        event_match_score -= 0.5

    # 1) Event/entities/evidence via caption
    event_caption_score, event_reasons = _mide_evento_en_caption(spec, caption)
    event_match_score = min(event_match_score, event_caption_score)
    reasons.extend(event_reasons)

    # 2) Entorno
    env_score, env_reasons = _mide_entorno(spec, caption)
    narrative_clarity_score = min(narrative_clarity_score, env_score)
    reasons.extend(env_reasons)

    # 3) Acción vs pose
    action_caption_score, action_reasons = _mide_accion_vs_pose(spec, caption)
    action_score = min(action_score, action_caption_score)
    reasons.extend(action_reasons)

    # Reglas lógicas duras por spec (hooks semánticos)
    if not (spec.event_core or "").strip():
        reasons.append("event_core vacío")
        event_match_score -= 0.6
    if not (spec.physical_motion or "").strip():
        reasons.append("sin physical_motion definido")
        action_score -= 0.6
    if not spec.must_visible_evidence:
        reasons.append("sin must_visible_evidence")
        event_match_score -= 0.5
    if "pov" in spec.camera_mode.lower() and "over the shoulder" in spec.camera_mode.lower():
        reasons.append("camera_mode contradictorio: POV + over the shoulder")
        camera_consistency_score -= 0.9
    if "pov" in spec.camera_mode.lower() and spec.camera_subject_visibility != "protagonist_not_visible_except_hands_optional":
        reasons.append("camera_subject_visibility inválido para POV")
        camera_consistency_score -= 0.7
    if "over the shoulder" in spec.camera_mode.lower() and spec.camera_subject_visibility == "protagonist_not_visible_except_hands_optional":
        reasons.append("camera_subject_visibility inválido para over the shoulder")
        camera_consistency_score -= 0.7

    if prev_image_path and prev_image_path.exists():
        d = _hamming(_phash_like(image_path), _phash_like(prev_image_path))
        # Muy parecido al frame anterior => repetición no usable
        if d <= 5:
            reasons.append("demasiado similar al frame anterior")
            repetition_score -= 0.8
            narrative_clarity_score -= 0.3

    if any(p in (spec.action or "").lower() for p in ("mira", "ve", "piensa", "llega a la escena", "se aproxima")):
        reasons.append("acción abstracta/débil en spec")
        action_score -= 0.6

    # Score final ponderado
    score = (
        event_match_score * 0.30
        + action_score * 0.25
        + camera_consistency_score * 0.20
        + narrative_clarity_score * 0.15
        + repetition_score * 0.10
    )
    score = max(0.0, min(1.0, score))

    # 6) Jamás 1.0 si faltan evidencias/evento crítico
    hay_fallo_critico_evento = any(
        ("falta evidencia visual obligatoria" in r)
        or ("faltan entidades obligatorias" in r)
        or ("no se observa sangre/herida" in r)
        or ("no se ve cuerpo en el suelo" in r)
        or ("mismatch de entorno" in r)
        for r in reasons
    )
    if hay_fallo_critico_evento:
        score = min(score, 0.49)
    elif not caption:
        # Sin lectura semántica de imagen (sin API key) no permitir score perfecto.
        score = min(score, 0.89)

    is_valid = score >= 0.70 and not any(
        r
        for r in reasons
        if any(
            k in r
            for k in (
                "event_core vacío",
                "sin must_visible_evidence",
                "camera_mode contradictorio",
                "camera_subject_visibility inválido",
                "acción abstracta",
            )
        )
    )
    return ValidationResult(
        frame_id=spec.frame_id,
        is_valid=is_valid,
        score=score,
        event_match_score=max(0.0, event_match_score),
        action_score=max(0.0, action_score),
        camera_consistency_score=max(0.0, camera_consistency_score),
        narrative_clarity_score=max(0.0, narrative_clarity_score),
        repetition_score=max(0.0, repetition_score),
        reasons=reasons,
        caption=caption,
    )


def resultado_a_dict(r: ValidationResult) -> dict:
    return asdict(r)
