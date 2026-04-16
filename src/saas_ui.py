"""UI SaaS premium (Streamlit): flujo producto, no panel técnico."""
from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from src.catalog_service import BACKGROUNDS, CHARACTERS, VOICES, get_background, get_character, get_voice
from src.config_loader import BASE, get_background_music_path
from src.pipeline import run_saas_mvp
from src.saas_audio_catalog import ensure_audio_dirs, list_safe_music, list_safe_sfx
from src.saas_creative_profile import (
    merge_profile_disk,
    merge_profile_updates,
    parse_llm_json_object,
    profile_to_script_context,
)
from src.saas_sessions import (
    add_session,
    build_pipeline_session_context,
    ensure_store,
    get_session,
    load_store,
    persist_session,
    persist_session_summary,
    rename_session,
    set_active_session,
    summarize_session_messages,
)
from src.scene_planner import plan_scenes
from src.script_generator import generar_guion

load_dotenv(BASE / ".env")

OUTPUT_DIR = BASE / "output"
PROJECTS_DB = OUTPUT_DIR / "saas_projects.json"
PROFILE_STORE = OUTPUT_DIR / "saas_creative_profile.json"
CHAT_STORE = OUTPUT_DIR / "saas_agent_chat.json"
RENDER_PROGRESS = OUTPUT_DIR / ".saas_render_progress.json"

PRESETS = ["clean_youtube", "dynamic_punchy", "minimal_subtle"]


def _ensure_dirs() -> None:
    (BASE / "assets" / "characters").mkdir(parents=True, exist_ok=True)
    (BASE / "assets" / "backgrounds").mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "uploads").mkdir(parents=True, exist_ok=True)
    ensure_audio_dirs()


def _load_projects() -> list[dict]:
    if not PROJECTS_DB.exists():
        return []
    try:
        return json.loads(PROJECTS_DB.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_projects(items: list[dict]) -> None:
    PROJECTS_DB.parent.mkdir(parents=True, exist_ok=True)
    PROJECTS_DB.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_project(item: dict) -> None:
    items = _load_projects()
    items.insert(0, item)
    _save_projects(items[:200])


def _update_project(project_id: str, **fields: object) -> None:
    items = _load_projects()
    for i, it in enumerate(items):
        if str(it.get("id")) == str(project_id):
            items[i] = {**it, **fields}
            break
    _save_projects(items)


def _load_profile_disk() -> dict | None:
    if not PROFILE_STORE.exists():
        return None
    try:
        raw = json.loads(PROFILE_STORE.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and raw.get("profile"):
            return raw["profile"]
    except Exception:
        return None
    return None


def _save_profile_disk(profile: dict) -> None:
    PROFILE_STORE.parent.mkdir(parents=True, exist_ok=True)
    PROFILE_STORE.write_text(
        json.dumps(
            {"updated_at": datetime.now().isoformat(timespec="seconds"), "profile": profile},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _load_chat_disk() -> list[dict] | None:
    if not CHAT_STORE.exists():
        return None
    try:
        raw = json.loads(CHAT_STORE.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and isinstance(raw.get("messages"), list):
            return raw["messages"]
    except Exception:
        return None
    return None


def _save_chat_disk(messages: list[dict]) -> None:
    CHAT_STORE.parent.mkdir(parents=True, exist_ok=True)
    CHAT_STORE.write_text(
        json.dumps(
            {"updated_at": datetime.now().isoformat(timespec="seconds"), "messages": messages},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _session_hydrate_from_disk() -> None:
    store = ensure_store()
    sid = store.get("active_id")
    sess = get_session(store, sid)
    if not sess:
        return
    st.session_state.active_session_id = str(sess.get("id") or sid)
    st.session_state.agent_messages = list(sess.get("messages") or [{"role": "assistant", "content": "Hola. ¿Qué tipo de videos querés publicar en esta sesión?"}])
    st.session_state.creative_profile = merge_profile_disk(sess.get("creative_profile"))
    st.session_state.session_memory_summary = str(sess.get("memory_summary") or "")


def _session_persist() -> None:
    store = load_store()
    sid = st.session_state.get("active_session_id") or store.get("active_id")
    if not sid:
        store = ensure_store()
        sid = store.get("active_id")
        st.session_state.active_session_id = sid
    persist_session(store, str(sid), st.session_state.agent_messages, st.session_state.creative_profile)


def _trim_chat_messages(msgs: list[dict], max_chars: int = 28000) -> list[dict]:
    out: list[dict] = []
    n = 0
    for m in reversed(msgs):
        if not isinstance(m, dict) or m.get("role") not in ("user", "assistant", "system"):
            continue
        piece = str(m.get("content") or "")
        if n + len(piece) > max_chars and out:
            break
        out.insert(0, dict(m))
        n += len(piece)
    return out


def _get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
    except Exception:
        return None
    return OpenAI(api_key=api_key)


def _creative_agent_reply(messages: list[dict], profile: dict) -> str:
    client = _get_openai_client()
    if not client:
        return "Contame más sobre el estilo de videos que querés. ¿Nicho, tono, formato y cómo querés el montaje?"
    mem = str(st.session_state.get("session_memory_summary") or "").strip()
    mem_block = f"\n\nMEMORIA LARGA DE ESTA SESIÓN (recordá esto al responder):\n{mem}\n" if mem else ""
    system_prompt = (
        "Sos director creativo y de postproducción para YouTube. Español. "
        "Tenés el historial de esta sesión de trabajo abajo: tratá de ser coherente con todo lo acordado. "
        "Ayudá a definir con precisión: nicho, público, tono, hooks, ritmo narrativo, formato (largo vs vertical), "
        "estética visual (luz, color, planos), ritmo de corte, transiciones, texto en pantalla, rol de la música y "
        "notas para quien edite o para la IA de montaje. "
        "Preguntá 1–2 cosas muy concretas por turno. Sin markdown largo. No digas que actualizaste el perfil."
    )
    conv = [
        {
            "role": "system",
            "content": system_prompt
            + mem_block
            + "\nPerfil actual: "
            + json.dumps(merge_profile_disk(profile), ensure_ascii=False),
        }
    ]
    conv.extend(_trim_chat_messages(messages, 30000))
    try:
        r = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.65,
            messages=conv,
        )
        return r.choices[0].message.content.strip()
    except Exception:
        return "Seguimos: ¿qué tono querés y qué duración sueles publicar?"


def _extract_profile_from_conversation(messages: list[dict], current: dict) -> tuple[dict, str | None]:
    """
    Devuelve (perfil_fusionado, error).
    error es None si todo bien; si hay fallo de API o JSON, devolvé mensaje corto para mostrar en UI.
    """
    client = _get_openai_client()
    base = merge_profile_disk(current)
    if not client:
        return base, "Sin OPENAI_API_KEY no se puede extraer el perfil."
    voice_list = ", ".join(VOICES.keys())
    system = f"""Devolvé un ÚNICO objeto JSON (objeto raíz) con el perfil creativo del canal para producción de video.

OBLIGATORIO:
- Incluí SIEMPRE las claves de primer nivel: niche, tone, hook_style, pacing, narrator_preference, language_register,
  topics_to_avoid, notes_freeform, audience, channel, script, video, visual, editing (podés anidar objetos).
- Cada campo de texto que puedas deducir del chat debe tener al menos una frase concreta (no dejes "" si el usuario dio contexto).
- Si el usuario fue vago pero dio un tema, inferí tono, hook y look razonables y aclaralo en notes_freeform.
- pacing: exactamente uno de: Lento, Medio, Rápido.
- narrator_preference: exactamente uno de estos ids: {voice_list}
- video.primary_format: youtube_long_16_9 o short_vertical_9_16

PROHIBIDO: texto fuera del JSON, markdown, comentarios."""
    slim_msgs = []
    for m in messages[-45:]:
        if not isinstance(m, dict) or m.get("role") not in ("user", "assistant"):
            continue
        c = str(m.get("content") or "")
        if len(c) > 3500:
            c = c[:3500] + "…"
        slim_msgs.append({"role": m["role"], "content": c})
    user_blob = json.dumps(
        {"messages": slim_msgs, "perfil_actual_como_pista": base},
        ensure_ascii=False,
    )

    def _call(with_json_mode: bool) -> str:
        kwargs: dict = {
            "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            "temperature": 0.25,
            "max_tokens": 8192,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_blob},
            ],
        }
        if with_json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        r = client.chat.completions.create(**kwargs)
        return (r.choices[0].message.content or "").strip()

    raw = ""
    try:
        try:
            raw = _call(with_json_mode=True)
        except Exception:
            raw = _call(with_json_mode=False)
        parsed = parse_llm_json_object(raw)
        if not parsed:
            snippet = (raw[:900] + "…") if len(raw) > 900 else raw
            return base, f"No se pudo leer JSON del modelo. Respuesta (recorte): {snippet}"
        merged = merge_profile_updates(base, parsed)
        return merged, None
    except Exception as e:
        return base, f"Error al extraer perfil: {e!s}"


def _resolve_asset(uri: str) -> Path:
    p = Path(uri)
    return p if p.is_absolute() else BASE / p


def _theme() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,600;0,9..40,700;1,9..40,400&display=swap');
        html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
        .stApp {
          background: radial-gradient(1200px 600px at 10% -10%, #1a2240 0%, transparent 55%),
                      radial-gradient(900px 500px at 90% 0%, #2a1535 0%, transparent 50%),
                      linear-gradient(165deg, #0a0c12 0%, #0f1118 40%, #0c0e14 100%);
          color: #eceef4;
        }
        .main .block-container { max-width: 1200px; padding: 2rem 1.5rem 3rem; }
        div[data-testid="stSidebar"] {
          background: rgba(12,14,22,0.92);
          border-right: 1px solid rgba(255,255,255,0.06);
        }
        .saas-brand { font-size: 1.15rem; font-weight: 700; letter-spacing: -0.02em; color: #f4f5f8; }
        .saas-tag { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.12em; color: #7b849c; }
        .saas-hero { font-size: 2.1rem; font-weight: 700; letter-spacing: -0.03em; margin: 0 0 0.35rem; color: #fafbff; }
        .saas-sub { color: #8b93a8; font-size: 0.95rem; margin-bottom: 1.75rem; }
        .saas-card {
          background: rgba(255,255,255,0.04);
          border: 1px solid rgba(255,255,255,0.08);
          border-radius: 18px;
          padding: 1.25rem 1.35rem;
          margin-bottom: 1rem;
        }
        .saas-card h4 { margin: 0 0 0.5rem; font-size: 0.95rem; color: #c5cad8; font-weight: 600; }
        .saas-metric { font-size: 1.65rem; font-weight: 700; color: #fff; }
        .saas-label { font-size: 0.78rem; color: #7b849c; text-transform: uppercase; letter-spacing: 0.08em; }
        div[data-testid="stVerticalBlockBorderWrapper"] > div {
          background: rgba(255,255,255,0.03) !important;
          border-color: rgba(255,255,255,0.08) !important;
          border-radius: 16px !important;
        }
        .stButton > button[kind="primary"] {
          background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
          border: none;
          font-weight: 600;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _init_state() -> None:
    if st.session_state.get("_saas_boot"):
        return
    st.session_state._saas_boot = True
    st.session_state.nav = "Dashboard"
    st.session_state.create_step = 1
    st.session_state.create_topic = ""
    st.session_state.create_duration = 4
    st.session_state.create_character = list(CHARACTERS.keys())[0]
    st.session_state.create_background = list(BACKGROUNDS.keys())[0]
    st.session_state.create_voice = list(VOICES.keys())[0]
    st.session_state.create_preset = PRESETS[0]
    st.session_state.create_use_bgm = True
    st.session_state.create_use_sfx = False
    st.session_state.create_safe_music_path = None
    st.session_state.create_safe_sfx_path = None
    st.session_state.create_use_env_music = False
    st.session_state.create_music_vol = 0.18
    st.session_state.create_sfx_vol = 0.08
    st.session_state.active_session_id = None
    st.session_state.session_memory_summary = ""
    st.session_state.agent_messages = []
    st.session_state.creative_profile = merge_profile_disk(None)
    st.session_state.last_video_path = None
    st.session_state.last_script = ""
    st.session_state.last_blocks = []
    st.session_state.block_approved = {}
    st.session_state.render = None


def _nav() -> None:
    with st.sidebar:
        st.markdown('<p class="saas-tag">FrameFactory</p>', unsafe_allow_html=True)
        st.markdown('<p class="saas-brand">Studio</p>', unsafe_allow_html=True)
        st.caption(" ")
        store = ensure_store()
        ids = [str(s["id"]) for s in store.get("sessions") or [] if isinstance(s, dict) and s.get("id")]
        if not ids:
            store = ensure_store()
            ids = [str(s["id"]) for s in store.get("sessions") or [] if isinstance(s, dict) and s.get("id")]
        titles = {str(s["id"]): str(s.get("title") or "Sesión")[:48] for s in store.get("sessions") or [] if isinstance(s, dict) and s.get("id")}
        cur = str(st.session_state.get("active_session_id") or store.get("active_id") or (ids[0] if ids else ""))
        if cur not in ids and ids:
            cur = ids[0]

        def _fmt_sid(sid: str) -> str:
            s = get_session(load_store(), sid) or {}
            return f"{titles.get(sid, sid)} · {len(s.get('messages') or [])} mensajes"

        chosen = st.selectbox(
            "Sesión de trabajo",
            ids,
            index=ids.index(cur) if cur in ids else 0,
            format_func=_fmt_sid,
            key="saas_session_select",
        )
        if chosen and chosen != st.session_state.get("active_session_id"):
            _session_persist()
            store = load_store()
            set_active_session(store, chosen)
            _session_hydrate_from_disk()
            st.rerun()

        rn_col1, rn_col2 = st.columns([2, 1])
        with rn_col1:
            new_title = st.text_input("Nombre sesión", value=titles.get(cur, ""), key="saas_sess_rename_txt", label_visibility="collapsed", placeholder="Renombrar…")
        with rn_col2:
            if st.button("OK", key="saas_sess_rename_btn"):
                if new_title.strip():
                    rename_session(load_store(), cur, new_title.strip())
                    st.rerun()

        if st.button("Nueva sesión", use_container_width=True, key="saas_sess_new"):
            _session_persist()
            store = load_store()
            _, nid = add_session(store, "Nueva sesión", None)
            st.session_state.active_session_id = nid
            _session_hydrate_from_disk()
            st.rerun()

        st.divider()
        for label, key in [
            ("Inicio", "Dashboard"),
            ("Nuevo video", "Create"),
            ("Render", "Rendering"),
            ("Revisar", "Review"),
            ("Perfil", "Profile"),
        ]:
            btn_type = "primary" if st.session_state.nav == key else "secondary"
            if st.button(label, key=f"nav_{key}", use_container_width=True, type=btn_type):
                st.session_state.nav = key
                st.rerun()


def _card_metric(label: str, value: str) -> None:
    st.markdown(
        f'<div class="saas-card"><div class="saas-label">{label}</div><div class="saas-metric">{value}</div></div>',
        unsafe_allow_html=True,
    )


def page_dashboard() -> None:
    st.markdown('<p class="saas-hero">Tus videos</p>', unsafe_allow_html=True)
    st.markdown('<p class="saas-sub">Creá contenido, no configuraciones.</p>', unsafe_allow_html=True)
    items = _load_projects()
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        _card_metric("Total", str(len(items)))
    with c2:
        _card_metric("Listos", str(len([i for i in items if i.get("status") == "ready"])))
    with c3:
        _card_metric("Render", str(len([i for i in items if i.get("status") == "rendering"])))
    with c4:
        _card_metric("Fallidos", str(len([i for i in items if i.get("status") == "failed"])))

    st.markdown(" ")
    b1, _ = st.columns([1, 2])
    with b1:
        if st.button("Crear video", type="primary", use_container_width=True):
            st.session_state.nav = "Create"
            st.session_state.create_step = 1
            st.rerun()

    st.markdown("#### Recientes")
    if not items:
        st.info("Todavía no hay videos. Creá el primero.")
        return
    for it in items[:12]:
        status = it.get("status", "draft")
        badge = {"ready": "Listo", "rendering": "Renderizando", "failed": "Error", "draft": "Borrador"}.get(status, status)
        with st.container():
            c_a, c_b = st.columns([4, 1])
            with c_a:
                st.markdown(f"**{it.get('topic', 'Sin título')[:80]}**")
                st.caption(f"{badge} · {it.get('created_at', '')}")
            with c_b:
                if st.button("Abrir", key=f"dash_open_{it['id']}"):
                    st.session_state.last_video_path = it.get("video_path")
                    st.session_state.nav = "Review"
                    st.rerun()


def _pick_card(title: str, options: list[str], state_key: str, fmt=None) -> None:
    st.markdown(f"#### {title}")
    cols = st.columns(min(4, len(options)))
    for i, opt in enumerate(options):
        with cols[i % len(cols)]:
            label = fmt(opt) if fmt else opt
            if st.button(label, key=f"{state_key}_{opt}", use_container_width=True):
                st.session_state[state_key] = opt
                st.rerun()
    st.caption(f"Selección: **{st.session_state[state_key]}**")


def page_create() -> None:
    st.markdown('<p class="saas-hero">Nuevo video</p>', unsafe_allow_html=True)
    sid = st.session_state.get("active_session_id") or "—"
    st.caption(
        f"Paso {st.session_state.create_step} de 3 · Sesión: {sid} — al generar, el guion y el montaje usan el chat y la memoria de esa sesión."
    )
    st.progress((st.session_state.create_step - 1) / 3)

    if st.session_state.create_step == 1:
        st.markdown("### Tu idea")
        idea = st.text_area(
            " ",
            value=st.session_state.create_topic,
            height=220,
            placeholder="Ej.: mini historias de terror narradas, 5 minutos, tono cinematográfico…",
            label_visibility="collapsed",
        )
        st.session_state.create_topic = idea
        _, r = st.columns([3, 1])
        with r:
            if st.button("Siguiente", type="primary", disabled=not idea.strip(), use_container_width=True):
                st.session_state.create_step = 2
                st.rerun()

    elif st.session_state.create_step == 2:
        st.markdown("### Estilo del video")
        _pick_card(
            "Personaje",
            list(CHARACTERS.keys()),
            "create_character",
            lambda k: CHARACTERS[k].get("name", k),
        )
        _pick_card("Fondo", list(BACKGROUNDS.keys()), "create_background", lambda k: k.replace("_", " ").title())
        _pick_card("Voz", list(VOICES.keys()), "create_voice", lambda k: k.replace("_", " ").title())
        _pick_card("Preset", PRESETS, "create_preset", lambda k: k.replace("_", " "))
        st.session_state.create_duration = st.slider("Duración objetivo (min)", 3, 8, st.session_state.create_duration)

        st.markdown("#### Sonido seguro para YouTube")
        st.markdown(
            "Descargá música y SFX **solo** desde la [Biblioteca de audio de YouTube](https://support.google.com/youtube/answer/3376882?hl=es) "
            "(Studio) y colocá los archivos en `assets/saas_youtube_audio/music/` y `.../sfx/`. "
            "Google **no** ofrece API pública para esa biblioteca: la app solo mezcla archivos que vos pongás ahí."
        )
        st.session_state.create_use_bgm = st.checkbox(
            "Música bajo la voz",
            value=st.session_state.get("create_use_bgm", True),
        )
        tracks_m = list_safe_music()
        labels_m = ["— Ninguna —"] + [t[0] for t in tracks_m]
        paths_m = [None] + [t[1] for t in tracks_m]
        def_idx_m = 0
        cur_m = st.session_state.get("create_safe_music_path")
        if cur_m:
            for j, p in enumerate(paths_m):
                if p is not None and str(p.resolve()) == str(Path(cur_m).resolve()):
                    def_idx_m = j
                    break
        ix_m = labels_m.index(
            st.selectbox(
                "Pista de música (carpeta local)",
                labels_m,
                index=min(def_idx_m, len(labels_m) - 1),
                key="saas_safe_music_sel",
            )
        )
        st.session_state.create_safe_music_path = str(paths_m[ix_m]) if paths_m[ix_m] is not None else None

        st.session_state.create_use_env_music = st.checkbox(
            "Usar también BACKGROUND_MUSIC_PATH del .env",
            value=st.session_state.get("create_use_env_music", False),
            help="Solo activalo si esa ruta apunta a audio que vos descargaste con licencia adecuada (p. ej. Biblioteca de YouTube).",
        )
        st.session_state.create_music_vol = float(
            st.slider("Volumen música", 0.05, 0.45, float(st.session_state.get("create_music_vol", 0.18)), step=0.01)
        )
        if not tracks_m:
            st.info("No hay archivos en `assets/saas_youtube_audio/music/`. Agregá mp3/wav descargados de la Biblioteca de audio.")

        st.session_state.create_use_sfx = st.checkbox(
            "Capa de ambiente (SFX)",
            value=st.session_state.get("create_use_sfx", False),
        )
        tracks_s = list_safe_sfx()
        labels_s = ["— Ninguno —"] + [t[0] for t in tracks_s]
        paths_s = [None] + [t[1] for t in tracks_s]
        def_idx_s = 0
        cur_s = st.session_state.get("create_safe_sfx_path")
        if cur_s:
            for j, p in enumerate(paths_s):
                if p is not None and str(p.resolve()) == str(Path(cur_s).resolve()):
                    def_idx_s = j
                    break
        ix_s = labels_s.index(
            st.selectbox(
                "SFX / ambiente (carpeta local)",
                labels_s,
                index=min(def_idx_s, len(labels_s) - 1),
                key="saas_safe_sfx_sel",
            )
        )
        st.session_state.create_safe_sfx_path = str(paths_s[ix_s]) if paths_s[ix_s] is not None else None
        st.session_state.create_sfx_vol = float(
            st.slider("Volumen SFX", 0.02, 0.22, float(st.session_state.get("create_sfx_vol", 0.08)), step=0.01)
        )
        if st.session_state.create_use_sfx and not tracks_s:
            st.info("No hay SFX en `assets/saas_youtube_audio/sfx/`.")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Atrás"):
                st.session_state.create_step = 1
                st.rerun()
        with c2:
            if st.button("Siguiente", type="primary", use_container_width=True):
                st.session_state.create_step = 3
                st.rerun()

    else:
        st.markdown("### Listo para generar")
        ch = get_character(st.session_state.create_character)
        bgm_note = "No"
        if st.session_state.get("create_use_bgm"):
            if st.session_state.get("create_safe_music_path"):
                bgm_note = "Sí (carpeta segura)"
            elif st.session_state.get("create_use_env_music") and get_background_music_path():
                bgm_note = "Sí (.env)"
            elif st.session_state.get("create_use_bgm"):
                bgm_note = "Sí (sin pista; revisá carpeta o .env)"
        sfx_note = "Sí" if st.session_state.get("create_use_sfx") and st.session_state.get("create_safe_sfx_path") else "No"
        st.markdown(
            f"**Idea:** {st.session_state.create_topic[:200]}\n\n"
            f"**Personaje:** {ch.get('name')} · **Fondo:** {st.session_state.create_background} · "
            f"**Voz:** {st.session_state.create_voice} · **Preset:** {st.session_state.create_preset} · "
            f"**Duración:** {st.session_state.create_duration} min\n\n"
            f"**Música:** {bgm_note} · **SFX:** {sfx_note}"
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Atrás"):
                st.session_state.create_step = 2
                st.rerun()
        with c2:
            if st.button("Generar video", type="primary", use_container_width=True):
                _session_persist()
                pid = datetime.now().strftime("%Y%m%d%H%M%S")
                _append_project(
                    {
                        "id": pid,
                        "topic": st.session_state.create_topic.strip(),
                        "status": "rendering",
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "video_path": "",
                        "character_id": st.session_state.create_character,
                        "background_id": st.session_state.create_background,
                        "voice_id": st.session_state.create_voice,
                        "duration_target_min": st.session_state.create_duration,
                        "preset": st.session_state.create_preset,
                        "use_bgm": st.session_state.get("create_use_bgm", True),
                        "use_sfx": st.session_state.get("create_use_sfx", False),
                        "safe_music_path": st.session_state.get("create_safe_music_path"),
                        "safe_sfx_path": st.session_state.get("create_safe_sfx_path"),
                        "use_env_music": st.session_state.get("create_use_env_music", False),
                        "session_id": str(st.session_state.get("active_session_id") or ""),
                    }
                )
                st.session_state.render = {
                    "project_id": pid,
                    "topic": st.session_state.create_topic.strip(),
                    "holder": [None],
                    "err": [None],
                    "started": False,
                    "use_bgm": st.session_state.get("create_use_bgm", True),
                    "use_sfx": st.session_state.get("create_use_sfx", False),
                    "safe_music_path": st.session_state.get("create_safe_music_path"),
                    "safe_sfx_path": st.session_state.get("create_safe_sfx_path"),
                    "use_env_music": st.session_state.get("create_use_env_music", False),
                    "music_volume": st.session_state.get("create_music_vol", 0.18),
                    "sfx_volume": st.session_state.get("create_sfx_vol", 0.08),
                    "creative_profile": json.loads(
                        json.dumps(merge_profile_disk(st.session_state.creative_profile), ensure_ascii=False)
                    ),
                    "session_context": build_pipeline_session_context(
                        {
                            "memory_summary": st.session_state.get("session_memory_summary", ""),
                            "messages": list(st.session_state.agent_messages),
                        }
                    ),
                }
                if RENDER_PROGRESS.exists():
                    try:
                        RENDER_PROGRESS.unlink()
                    except Exception:
                        pass
                st.session_state.nav = "Rendering"
                st.rerun()


def _run_mvp_thread(topic: str, holder: list, err: list, opts: dict | None) -> None:
    try:
        opts = opts or {}

        m_path = Path(opts["safe_music_path"]) if opts.get("safe_music_path") else None
        if m_path is not None and not m_path.exists():
            m_path = None
        s_path = Path(opts["safe_sfx_path"]) if opts.get("safe_sfx_path") else None
        if s_path is not None and not s_path.exists():
            s_path = None
        if not opts.get("use_bgm", True):
            m_path = None
        if not opts.get("use_sfx", True):
            s_path = None
        use_env = bool(opts.get("use_env_music", False)) and bool(opts.get("use_bgm", True))
        if m_path is None and use_env:
            env_p = get_background_music_path()
            if env_p and env_p.exists():
                m_path = env_p
        use_env_flag = use_env and m_path is None
        holder[0] = run_saas_mvp(
            topic,
            progress_path=RENDER_PROGRESS,
            music_path=m_path,
            sfx_path=s_path,
            music_volume=float(opts.get("music_volume", 0.18)),
            sfx_volume=float(opts.get("sfx_volume", 0.08)),
            use_env_music_if_no_upload=use_env_flag,
            creative_profile=opts.get("creative_profile"),
            session_context=opts.get("session_context"),
        )
    except Exception as e:
        err[0] = e


def page_rendering() -> None:
    st.markdown('<p class="saas-hero">Generando</p>', unsafe_allow_html=True)
    st.markdown('<p class="saas-sub">Esto puede tardar varios minutos.</p>', unsafe_allow_html=True)
    job = st.session_state.get("render")
    if not job:
        st.info("No hay render en curso. Volvé a **Nuevo video**.")
        if st.button("Ir a crear"):
            st.session_state.nav = "Create"
            st.rerun()
        return

    if not job.get("started"):
        job["started"] = True
        opts = {
            "use_bgm": job.get("use_bgm", True),
            "use_sfx": job.get("use_sfx", False),
            "safe_music_path": job.get("safe_music_path"),
            "safe_sfx_path": job.get("safe_sfx_path"),
            "use_env_music": job.get("use_env_music", False),
            "music_volume": job.get("music_volume", 0.18),
            "sfx_volume": job.get("sfx_volume", 0.08),
            "creative_profile": job.get("creative_profile"),
            "session_context": job.get("session_context"),
        }
        t = threading.Thread(
            target=_run_mvp_thread,
            args=(job["topic"], job["holder"], job["err"], opts),
            daemon=True,
        )
        t.start()
        job["thread"] = t
        st.session_state.render = job

    pct = 0.0
    step = "Preparando…"
    if RENDER_PROGRESS.exists():
        try:
            d = json.loads(RENDER_PROGRESS.read_text(encoding="utf-8"))
            pct = float(d.get("pct", 0))
            step = str(d.get("step", step))
        except Exception:
            pass

    st.progress(min(1.0, pct / 100.0))
    st.caption(f"{int(pct)}% · {step}")

    th: threading.Thread = job["thread"]
    if th.is_alive():
        time.sleep(0.45)
        st.rerun()
        return

    th.join(timeout=2.0)
    err = job["err"][0]
    out = job["holder"][0]
    pid = job["project_id"]
    if err:
        _update_project(pid, status="failed", error=str(err))
        st.error(str(err))
        st.session_state.render = None
        return

    st.session_state.last_video_path = str(out)
    meta_path = OUTPUT_DIR / "saas_last_mvp_meta.json"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            st.session_state.last_script = str(meta.get("script") or "")
            st.session_state.last_blocks = meta.get("blocks") or []
        except Exception:
            prof = merge_profile_disk(st.session_state.get("creative_profile"))
            ctx = profile_to_script_context(prof)
            op = (prof.get("script") or {}).get("opening_style") or ""
            force_pov = not bool(str(op).strip())
            script_text, _, _ = generar_guion(
                job["topic"],
                target_words=420,
                plantilla="explicativo",
                segundos_por_imagen=6.0,
                creative_context=ctx,
                force_este_eres_tu_opening=force_pov,
            )
            st.session_state.last_script = script_text
            st.session_state.last_blocks = plan_scenes(script_text)
    else:
        prof = merge_profile_disk(job.get("creative_profile") or st.session_state.get("creative_profile"))
        ctx = profile_to_script_context(prof)
        op = (prof.get("script") or {}).get("opening_style") or ""
        force_pov = not bool(str(op).strip())
        script_text, _, _ = generar_guion(
            job["topic"],
            target_words=420,
            plantilla="explicativo",
            segundos_por_imagen=6.0,
            creative_context=ctx,
            force_este_eres_tu_opening=force_pov,
        )
        st.session_state.last_script = script_text
        st.session_state.last_blocks = plan_scenes(script_text)
    _update_project(
        pid,
        status="ready",
        video_path=str(out),
        topic=job["topic"],
    )
    st.session_state.render = None
    st.success("Video listo.")
    st.session_state.nav = "Review"
    time.sleep(0.3)
    st.rerun()


def page_review() -> None:
    st.markdown('<p class="saas-hero">Revisión</p>', unsafe_allow_html=True)
    st.markdown('<p class="saas-sub">Previsualizá y aprobá por bloque.</p>', unsafe_allow_html=True)
    if not st.session_state.get("last_script"):
        st.info("Generá un video primero.")
        return
    left, right = st.columns([1.1, 1])
    with left:
        vp = st.session_state.get("last_video_path")
        if vp and Path(vp).exists():
            st.video(str(vp))
            st.caption("La mezcla de música / SFX se aplicó al exportar el MP4 final.")
        else:
            st.warning("Archivo de video no encontrado.")
    with right:
        st.markdown("#### Guion por bloques (con plan de montaje IA)")
        for b in st.session_state.last_blocks[:40]:
            bid = str(b.get("id", ""))
            approved = st.session_state.block_approved.get(bid, False)
            st.markdown(f"**{bid}**")
            st.caption((b.get("text") or "")[:280])
            mo = b.get("motion") or "—"
            vd = (b.get("visual_direction") or "").strip()
            br = (b.get("b_roll_suggestion") or "").strip()
            tx = (b.get("on_screen_text") or "").strip()
            tins = f"{b.get('transition_in') or 'none'} → {b.get('transition_out') or 'none'}"
            st.caption(f"Movimiento: `{mo}` · Transiciones: {tins}")
            if vd:
                st.caption(f"Plano / luz: {vd[:220]}")
            if br:
                st.caption(f"B-roll: {br[:220]}")
            if tx:
                st.caption(f"Texto en pantalla sugerido: **{tx}**")
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("Regenerar", key=f"rg_{bid}"):
                    st.toast("Regeneración: próximamente conectada al pipeline.")
            with c2:
                if st.button("Aprobar", key=f"ap_{bid}"):
                    st.session_state.block_approved[bid] = True
                    st.rerun()
            with c3:
                st.write("OK" if approved else "")
            st.divider()
    if st.button("Aprobar proyecto", type="primary"):
        st.success("Proyecto aprobado (demo).")
    if st.button("Volver al inicio"):
        st.session_state.nav = "Dashboard"
        st.rerun()


def page_profile() -> None:
    st.markdown('<p class="saas-hero">Perfil creativo</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="saas-sub">Guion, estética, montaje y voz: todo alimenta al LLM del guion, al plan por bloque y al render MVP.</p>',
        unsafe_allow_html=True,
    )
    tab_summary, tab_edit, tab_chat = st.tabs(["Resumen", "Editar perfil", "Asistente"])

    pm = merge_profile_disk(st.session_state.creative_profile)
    with tab_summary:
        c1, c2, c3 = st.columns(3)
        with c1:
            _card_metric("Nicho", str(pm.get("niche") or "—")[:44])
        with c2:
            _card_metric("Tono", str(pm.get("tone") or "—")[:44])
        with c3:
            _card_metric("Hook", str(pm.get("hook_style") or "—")[:44])
        c4, c5, c6 = st.columns(3)
        with c4:
            _card_metric("Ritmo guion", str(pm.get("pacing") or "—"))
        with c5:
            _card_metric("Voz MVP", str(pm.get("narrator_preference") or "—"))
        with c6:
            vid = pm.get("video") or {}
            _card_metric("Formato", str(vid.get("primary_format") or "—")[:28])
        c7, c8 = st.columns(2)
        vis = pm.get("visual") or {}
        ed = pm.get("editing") or {}
        with c7:
            _card_metric("Look visual", str(vis.get("look") or "—")[:56])
        with c8:
            _card_metric("Ritmo de corte", str(ed.get("cut_rhythm") or "—")[:40])
        with st.expander("Perfil completo (JSON)", expanded=False):
            st.json(pm)

    with tab_edit:
        st.markdown("##### Identidad y guion")
        niche = st.text_input("Nicho", value=str(pm.get("niche") or ""))
        tone = st.text_input("Tono del canal", value=str(pm.get("tone") or ""))
        hook = st.text_input("Estilo de hook", value=str(pm.get("hook_style") or ""))
        pace_opts = ["Lento", "Medio", "Rápido"]
        pace_i = pace_opts.index(pm.get("pacing")) if pm.get("pacing") in pace_opts else 1
        pace = st.selectbox("Ritmo narrativo", pace_opts, index=pace_i)
        narr = st.selectbox("Voz preferida (MVP)", list(VOICES.keys()))
        lang = st.text_input("Registro lingüístico", value=str(pm.get("language_register") or ""))
        avoid = st.text_area("Temas o enfoques a evitar", value=str(pm.get("topics_to_avoid") or ""), height=72)

        st.markdown("##### Público y marca")
        aud = pm.get("audience") or {}
        a_who = st.text_input("Público objetivo", value=str(aud.get("who") or ""))
        a_pain = st.text_area("Dolores / necesidades", value=str(aud.get("pain_points") or ""), height=64)
        a_read = st.text_input("Nivel de lectura", value=str(aud.get("reading_level") or "general"))
        ch = pm.get("channel") or {}
        ch_name = st.text_input("Nombre del canal (marca)", value=str(ch.get("name") or ""))
        ch_tag = st.text_input("Tagline", value=str(ch.get("tagline") or ""))
        ch_pill = st.text_area("Pilares de contenido", value=str(ch.get("content_pillars") or ""), height=64)

        st.markdown("##### Guion detallado")
        scr = pm.get("script") or {}
        scr_struct = st.text_area("Estructura preferida (acts, lista, historia…)", value=str(scr.get("structure_preference") or ""), height=56)
        scr_forb = st.text_area("Frases prohibidas", value=str(scr.get("forbidden_phrases") or ""), height=56)
        scr_cta = st.text_input("Estilo de CTA / cierre", value=str(scr.get("cta_style") or ""))
        scr_open = st.text_area(
            "Apertura personalizada (si rellenás, el MVP no fuerza «Este eres tú.»)",
            value=str(scr.get("opening_style") or ""),
            height=70,
        )

        st.markdown("##### Video y formato")
        vid = pm.get("video") or {}
        fmt_opts = ["youtube_long_16_9", "short_vertical_9_16"]
        fi = fmt_opts.index(vid.get("primary_format")) if vid.get("primary_format") in fmt_opts else 0
        v_fmt = st.selectbox("Formato principal", fmt_opts, index=fi, format_func=lambda x: "YouTube 16:9" if x == fmt_opts[0] else "Short vertical 9:16")
        v_len = st.text_input("Categoría de largo buscado", value=str(vid.get("target_length_category") or ""))
        v_aspect = st.text_input("Notas de encuadre / safe area", value=str(vid.get("aspect_notes") or ""))

        st.markdown("##### Estética visual")
        vis = pm.get("visual") or {}
        v_look = st.text_area("Look general (documental, neon, minimal…)", value=str(vis.get("look") or ""), height=56)
        v_color = st.text_input("Color y mood", value=str(vis.get("color_mood") or ""))
        v_shot = st.text_area("Planos preferidos", value=str(vis.get("shot_preferences") or ""), height=56)
        v_broll = st.text_area("Estilo de B-roll", value=str(vis.get("b_roll_style") or ""), height=56)
        v_ref = st.text_area("Referencias / moodboard (texto)", value=str(vis.get("reference_moodboards") or ""), height=56)

        st.markdown("##### Montaje y post (IA + editor humano)")
        ed = pm.get("editing") or {}
        e_cut = st.text_input("Ritmo de corte (lento / medio / rápido + notas)", value=str(ed.get("cut_rhythm") or ""))
        e_tr = st.text_input("Transiciones por defecto", value=str(ed.get("transitions_default") or ""))
        e_low = st.text_input("Lower thirds", value=str(ed.get("lower_thirds") or ""))
        e_sub = st.text_input("Subtítulos (intención)", value=str(ed.get("subtitles_intent") or ""))
        e_mus = st.text_input("Rol de la música", value=str(ed.get("music_role") or ""))
        e_pvis = st.text_input("Ritmo visual vs audio", value=str(ed.get("pacing_visual") or ""))
        e_notes = st.text_area("Instrucciones para la IA de montaje / editor", value=str(ed.get("notes_for_ai_director") or ""), height=88)

        notes_free = st.text_area("Notas libres (cualquier contexto extra)", value=str(pm.get("notes_freeform") or ""), height=80)

        env_m = get_background_music_path()
        st.caption(f"Música global del .env (opcional al crear): `{env_m}`" if env_m else "Sin BACKGROUND_MUSIC_PATH en .env.")

        if st.button("Guardar perfil", type="primary"):
            updated = merge_profile_disk(pm)
            updated["niche"] = niche.strip()
            updated["tone"] = tone.strip()
            updated["hook_style"] = hook.strip()
            updated["pacing"] = pace
            updated["narrator_preference"] = narr
            updated["language_register"] = lang.strip()
            updated["topics_to_avoid"] = avoid.strip()
            updated["audience"] = {"who": a_who.strip(), "pain_points": a_pain.strip(), "reading_level": a_read.strip()}
            updated["channel"] = {
                "name": ch_name.strip(),
                "tagline": ch_tag.strip(),
                "content_pillars": ch_pill.strip(),
            }
            updated["script"] = {
                "structure_preference": scr_struct.strip(),
                "forbidden_phrases": scr_forb.strip(),
                "cta_style": scr_cta.strip(),
                "opening_style": scr_open.strip(),
            }
            updated["video"] = {
                "primary_format": v_fmt,
                "target_length_category": v_len.strip(),
                "aspect_notes": v_aspect.strip(),
            }
            updated["visual"] = {
                "look": v_look.strip(),
                "color_mood": v_color.strip(),
                "shot_preferences": v_shot.strip(),
                "b_roll_style": v_broll.strip(),
                "reference_moodboards": v_ref.strip(),
            }
            updated["editing"] = {
                "cut_rhythm": e_cut.strip(),
                "transitions_default": e_tr.strip(),
                "lower_thirds": e_low.strip(),
                "subtitles_intent": e_sub.strip(),
                "music_role": e_mus.strip(),
                "pacing_visual": e_pvis.strip(),
                "notes_for_ai_director": e_notes.strip(),
            }
            updated["notes_freeform"] = notes_free.strip()
            st.session_state.creative_profile = updated
            _session_persist()
            _save_profile_disk(updated)
            st.success("Guardado.")

    with tab_chat:
        st.caption(
            "Todo queda guardado en la **sesión activa** (sidebar). La IA ve el historial largo + resumen de memoria. "
            "Ese mismo contexto alimenta el guion y el montaje al generar un video."
        )
        hist = st.expander("Historial completo", expanded=False)
        with hist:
            for m in st.session_state.agent_messages:
                role = "Tú" if m["role"] == "user" else "IA"
                st.markdown(f"**{role}:** {m['content'][:500]}")
        for m in st.session_state.agent_messages[-6:]:
            with st.chat_message(m["role"]):
                st.write(m["content"])
        if msg := st.chat_input("Mensaje"):
            st.session_state.agent_messages.append({"role": "user", "content": msg})
            st.session_state.agent_messages.append(
                {"role": "assistant", "content": _creative_agent_reply(st.session_state.agent_messages, st.session_state.creative_profile)}
            )
            _session_persist()
            st.rerun()
        c1, c2, c3 = st.columns(3)
        if c1.button("Actualizar perfil desde el chat", type="primary"):
            new_prof, err = _extract_profile_from_conversation(
                st.session_state.agent_messages, st.session_state.creative_profile
            )
            st.session_state.creative_profile = new_prof
            _save_profile_disk(st.session_state.creative_profile)
            _session_persist()
            if err:
                st.warning(err)
            else:
                st.success("Perfil actualizado desde la conversación.")
        if c2.button("Condensar memoria de sesión"):
            cl = _get_openai_client()
            if not cl:
                st.warning("Sin OPENAI_API_KEY no se puede resumir.")
            else:
                try:
                    summ = summarize_session_messages(
                        cl,
                        st.session_state.agent_messages,
                        st.session_state.get("session_memory_summary") or "",
                    )
                    st.session_state.session_memory_summary = summ
                    aid = st.session_state.get("active_session_id")
                    if aid:
                        persist_session_summary(load_store(), str(aid), summ)
                    st.success("Memoria larga actualizada.")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
        if c3.button("Limpiar historial"):
            st.session_state.agent_messages = [{"role": "assistant", "content": "Historial borrado en esta sesión. ¿Por dónde empezamos?"}]
            _session_persist()
            st.rerun()


def render_app() -> None:
    _ensure_dirs()
    st.set_page_config(page_title="FrameFactory Studio", page_icon="◆", layout="wide", initial_sidebar_state="expanded")
    _theme()
    _init_state()
    _session_hydrate_from_disk()
    _nav()

    nav = st.session_state.nav
    if nav == "Dashboard":
        page_dashboard()
    elif nav == "Create":
        page_create()
    elif nav == "Rendering":
        page_rendering()
    elif nav == "Review":
        page_review()
    elif nav == "Profile":
        page_profile()
    else:
        page_dashboard()
