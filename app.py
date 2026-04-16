"""SaaS UI v1 para FrameFactory-AI (Streamlit)."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from src.catalog_service import BACKGROUNDS, CHARACTERS, VOICES, get_background, get_character, get_voice
from src.config_loader import BASE
from src.pipeline import run_saas_mvp
from src.scene_planner import plan_scenes
from src.script_generator import generar_guion

load_dotenv(BASE / ".env")

st.set_page_config(page_title="FrameFactory SaaS", page_icon="🎬", layout="wide")

PROJECTS_DB = BASE / "output" / "saas_projects.json"
OUTPUT_DIR = BASE / "output"


def _ensure_base_dirs() -> None:
    (BASE / "assets" / "characters").mkdir(parents=True, exist_ok=True)
    (BASE / "assets" / "backgrounds").mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


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


def _set_style() -> None:
    st.markdown(
        """
        <style>
        .stApp { background: linear-gradient(180deg, #0b0f1a 0%, #0e1322 100%); color: #e8ecf7; }
        .main .block-container { max-width: 1180px; padding-top: 1.5rem; padding-bottom: 2rem; }
        div[data-testid="stSidebar"] { background: #0a1020; border-right: 1px solid rgba(255,255,255,0.08); }
        .ff-title { font-size: 2rem; font-weight: 700; margin-bottom: .25rem; }
        .ff-sub { color: #9aa4bd; margin-bottom: 1.25rem; }
        .ff-card {
          border: 1px solid rgba(255,255,255,0.1);
          background: rgba(255,255,255,0.03);
          border-radius: 16px;
          padding: 14px 16px;
          min-height: 100px;
        }
        .ff-kpi { font-size: 1.55rem; font-weight: 700; margin: .15rem 0; }
        .ff-muted { color: #9aa4bd; font-size: .9rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _init_state() -> None:
    defaults = {
        "page": "Dashboard",
        "creative_profile": {
            "niche": "Negocios y dinero",
            "tone": "Directo y cinematográfico",
            "hook_style": "Pregunta fuerte + promesa",
            "narrator_preference": "male_sharp",
            "pacing": "Rápido",
        },
        "agent_messages": [
            {"role": "assistant", "content": "Soy tu AI Creative Agent. Decime tu nicho, tono y estilo de hook."}
        ],
        "selected_project_id": None,
        "last_video_path": None,
        "last_script": "",
        "last_blocks": [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _navbar() -> str:
    with st.sidebar:
        st.markdown("## FrameFactory SaaS")
        st.caption("Creator video studio")
        page = st.radio(
            "Navegación",
            ["Dashboard", "Creative Profile", "Create Video", "Review / Editor", "Library"],
            key="page",
            label_visibility="collapsed",
        )
    return page


def _page_header(title: str, subtitle: str) -> None:
    st.markdown(f'<div class="ff-title">{title}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="ff-sub">{subtitle}</div>', unsafe_allow_html=True)


def _render_dashboard() -> None:
    _page_header("Dashboard", "Vista operativa de proyectos, estados y generación.")
    items = _load_projects()
    total = len(items)
    done = len([i for i in items if i.get("status") == "ready"])
    failed = len([i for i in items if i.get("status") == "error"])
    recent = items[:5]

    c1, c2, c3 = st.columns(3)
    c1.markdown(f'<div class="ff-card"><div class="ff-muted">Proyectos totales</div><div class="ff-kpi">{total}</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="ff-card"><div class="ff-muted">Videos listos</div><div class="ff-kpi">{done}</div></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="ff-card"><div class="ff-muted">Errores</div><div class="ff-kpi">{failed}</div></div>', unsafe_allow_html=True)

    col_left, col_right = st.columns([2, 1])
    with col_left:
        st.markdown("### Proyectos recientes")
        if not recent:
            st.info("Todavía no hay proyectos SaaS generados.")
        for it in recent:
            with st.container(border=True):
                st.write(f"**{it.get('topic','(sin tema)')}**")
                st.caption(f"Estado: {it.get('status')} · {it.get('created_at')}")
    with col_right:
        st.markdown("### Acción rápida")
        st.button("➕ Crear nuevo video", use_container_width=True, key="go_create", on_click=lambda: st.session_state.update({"page": "Create Video"}))


def _render_creative_profile() -> None:
    _page_header("Creative Profile", "Agente creativo + preferencias estructuradas por creador.")
    left, right = st.columns([1.1, 1.4])

    with left:
        st.markdown("### AI Agent Chat")
        for m in st.session_state.agent_messages[-12:]:
            with st.chat_message(m["role"]):
                st.write(m["content"])
        user_msg = st.chat_input("Contame qué tipo de videos querés hacer…")
        if user_msg:
            st.session_state.agent_messages.append({"role": "user", "content": user_msg})
            st.session_state.agent_messages.append(
                {"role": "assistant", "content": "Entendido. Actualizá el perfil de la derecha y aplicá cambios para nuevos videos."}
            )
            st.rerun()

    with right:
        st.markdown("### Perfil estructurado")
        p = st.session_state.creative_profile
        niche = st.text_input("Nicho", value=p.get("niche", ""))
        tone = st.text_input("Tono", value=p.get("tone", ""))
        hook = st.text_input("Hook style", value=p.get("hook_style", ""))
        pace = st.selectbox("Ritmo", ["Lento", "Medio", "Rápido"], index=2 if p.get("pacing") == "Rápido" else 1)
        narrator = st.selectbox("Narrador preferido", options=list(VOICES.keys()), index=0)
        if st.button("Aplicar cambios", type="primary"):
            st.session_state.creative_profile = {
                "niche": niche,
                "tone": tone,
                "hook_style": hook,
                "pacing": pace,
                "narrator_preference": narrator,
            }
            st.success("Perfil creativo actualizado.")


def _render_create_video() -> None:
    _page_header("Create Video", "Configura un video largo de YouTube con catálogo cerrado y generación MVP.")
    left, right = st.columns([1.5, 1.0])

    with left:
        topic = st.text_area("Tema del video", value="Why most people fail at making money", height=120)
        duration = st.slider("Duración objetivo (min)", 3, 8, 4)
        character_id = st.selectbox("Character", options=list(CHARACTERS.keys()))
        background_id = st.selectbox("Background", options=list(BACKGROUNDS.keys()))
        voice_id = st.selectbox("Voice", options=list(VOICES.keys()))
        preset = st.selectbox("Editing preset", ["clean_youtube", "dynamic_punchy", "minimal_subtle"])

    with right:
        st.markdown("### Review summary")
        ch = get_character(character_id)
        bg = get_background(background_id)
        vc = get_voice(voice_id)
        st.container(border=True).markdown(
            "\n".join(
                [
                    f"**Tema:** {topic[:90]}",
                    f"**Duración:** {duration} min",
                    f"**Character:** {ch['name']}",
                    f"**Background:** {bg['id']}",
                    f"**Voice:** {vc['id']} ({vc['provider']})",
                    f"**Preset:** {preset}",
                    "",
                    "_Nota MVP: el pipeline actual usa selección fija de catálogo interno para render._",
                ]
            )
        )

        if st.button("Generate Video", type="primary", use_container_width=True):
            with st.status("Rendering video...", expanded=True) as status:
                try:
                    status.write("Generando video con run_saas_mvp()...")
                    out = run_saas_mvp(topic=topic.strip())
                    st.session_state.last_video_path = str(out)
                    script_text, _, _ = generar_guion(topic.strip(), target_words=420, plantilla="explicativo", segundos_por_imagen=6.0)
                    st.session_state.last_script = script_text
                    st.session_state.last_blocks = plan_scenes(script_text)
                    rec = {
                        "id": datetime.now().strftime("%Y%m%d%H%M%S"),
                        "topic": topic.strip(),
                        "status": "ready",
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "video_path": str(out),
                        "character_id": character_id,
                        "background_id": background_id,
                        "voice_id": voice_id,
                        "duration_target_min": duration,
                        "preset": preset,
                    }
                    _append_project(rec)
                    status.update(label="Render completed", state="complete")
                    st.success(f"Video generado: `{out}`")
                except Exception as e:
                    status.update(label="Render failed", state="error")
                    st.error(f"Error al generar: {e}")

    if st.session_state.get("last_video_path"):
        vp = Path(st.session_state.last_video_path)
        if vp.exists():
            st.markdown("### Último resultado")
            st.video(str(vp))


def _render_review_editor() -> None:
    _page_header("Review / Editor", "Aprueba, regenera y ajusta bloques del proyecto.")
    if not st.session_state.get("last_script"):
        st.info("No hay proyecto reciente en sesión. Generá uno desde Create Video.")
        return

    st.markdown("### Script")
    st.text_area("Texto generado", value=st.session_state.last_script, height=180, disabled=True)
    st.markdown("### Scene blocks")
    for b in st.session_state.last_blocks[:25]:
        col1, col2, col3 = st.columns([6, 1, 1])
        col1.markdown(f"**{b['id']}** · {b['text']}")
        col2.button("Regenerate", key=f"regen_{b['id']}", use_container_width=True)
        col3.button("Approve", key=f"approve_{b['id']}", use_container_width=True)

    st.markdown("### Selected configuration")
    p = st.session_state.creative_profile
    st.caption(
        f"Narrador preferido: {p.get('narrator_preference')} · "
        f"Nicho: {p.get('niche')} · Tono: {p.get('tone')}"
    )
    c1, c2 = st.columns(2)
    c1.button("Approve Project", type="primary", use_container_width=True)
    c2.button("Rerender Full Video", use_container_width=True)


def _render_library() -> None:
    _page_header("Library", "Historial de videos generados y operaciones de proyecto.")
    items = _load_projects()
    if not items:
        st.info("No hay proyectos guardados todavía.")
        return
    for it in items:
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
            c1.write(f"**{it.get('topic','(sin tema)')}**")
            c1.caption(f"Creado: {it.get('created_at')} · Estado: {it.get('status')}")
            if c2.button("Open", key=f"open_{it['id']}", use_container_width=True):
                st.session_state.selected_project_id = it["id"]
                vp = Path(it.get("video_path", ""))
                if vp.exists():
                    st.video(str(vp))
            if c3.button("Duplicate", key=f"dup_{it['id']}", use_container_width=True):
                dup = dict(it)
                dup["id"] = datetime.now().strftime("%Y%m%d%H%M%S%f")
                dup["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                dup["status"] = "draft"
                _append_project(dup)
                st.success("Proyecto duplicado.")
            c4.button("Archive", key=f"arc_{it['id']}", use_container_width=True)


_ensure_base_dirs()
_set_style()
_init_state()
page = _navbar()

if page == "Dashboard":
    _render_dashboard()
elif page == "Creative Profile":
    _render_creative_profile()
elif page == "Create Video":
    _render_create_video()
elif page == "Review / Editor":
    _render_review_editor()
elif page == "Library":
    _render_library()
