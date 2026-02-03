"""
FrameFactory-AI – Un solo lugar para generar el video completo.
Solo hace falta completar las credenciales en .env
Ejecutar: streamlit run app.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st
from dotenv import load_dotenv

from src.config_loader import BASE
from src.pipeline import run

load_dotenv(BASE / ".env")

# ─── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FrameFactory-AI",
    page_icon="◉",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── Credenciales requeridas ────────────────────────────────────────────────
def credenciales_ok():
    """True si hay al menos guion + voz + imágenes configurados."""
    openai = bool(os.getenv("OPENAI_API_KEY", "").strip())
    voz = bool(os.getenv("ELEVENLABS_API_KEY", "").strip()) or openai
    sd = bool(os.getenv("SD_API_URL", "").strip())
    return openai and voz and sd


def mensaje_credenciales():
    """Qué falta en .env."""
    faltan = []
    if not os.getenv("OPENAI_API_KEY", "").strip():
        faltan.append("OPENAI_API_KEY (guiones)")
    if not os.getenv("ELEVENLABS_API_KEY", "").strip() and not os.getenv("OPENAI_API_KEY", "").strip():
        faltan.append("ELEVENLABS_API_KEY o OPENAI_API_KEY (voz)")
    if not os.getenv("SD_API_URL", "").strip():
        faltan.append("SD_API_URL (Stable Diffusion)")
    return faltan


# ─── Session state ──────────────────────────────────────────────────────────
for key, default in [
    ("video_path", None),
    ("video_bytes", None),
    ("video_name", None),
    ("metadata_path", None),
    ("metadata_text", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default


def clear_result():
    st.session_state.video_path = None
    st.session_state.video_bytes = None
    st.session_state.video_name = None
    st.session_state.metadata_path = None
    st.session_state.metadata_text = None


# ─── Estilos ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700&display=swap');
    :root {
        --bg: #0a0a0b;
        --surface: #141416;
        --surface-elevated: #1c1c1f;
        --border: #2a2a2e;
        --muted: #71717a;
        --text: #fafafa;
        --accent: #f59e0b;
        --accent-hover: #fbbf24;
        --radius: 10px;
    }
    .stApp { background: var(--bg); font-family: 'DM Sans', system-ui, sans-serif; }
    header[data-testid="stHeader"] { background: transparent !important; }
    #MainMenu, footer { visibility: hidden; }
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; max-width: 720px; }
    .hero { font-size: 1.75rem !important; color: var(--text) !important; margin-bottom: 0.25rem !important; }
    .tagline { color: var(--muted) !important; font-size: 0.9rem !important; margin-bottom: 1.5rem !important; }
    .one-click { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 1.5rem; margin-bottom: 1.5rem; }
    .stTextInput input { background: var(--surface-elevated) !important; color: var(--text) !important; border: 1px solid var(--border) !important; border-radius: 8px !important; }
    .stButton > button {
        font-family: 'DM Sans', sans-serif !important; background: var(--surface-elevated) !important;
        color: var(--text) !important; border: 1px solid var(--border) !important; border-radius: var(--radius) !important;
    }
    .stButton > button:hover { border-color: var(--accent) !important; color: var(--accent) !important; }
    .btn-generar { background: var(--accent) !important; color: #0a0a0b !important; border: none !important; font-weight: 600 !important; padding: 0.75rem 1.5rem !important; }
    .btn-generar:hover { background: var(--accent-hover) !important; }
    .cred-warn { background: rgba(245,158,11,0.15); border: 1px solid var(--accent); border-radius: var(--radius); padding: 1rem; margin-bottom: 1rem; color: var(--text); font-size: 0.9rem; }
    .stSuccess { background: rgba(34,197,94,0.15) !important; border-radius: var(--radius) !important; }
    .stError { background: rgba(239,68,68,0.15) !important; border-radius: var(--radius) !important; }
</style>
""", unsafe_allow_html=True)

# ─── Hero ───────────────────────────────────────────────────────────────────
st.markdown('<p class="hero">FrameFactory</p>', unsafe_allow_html=True)
st.markdown('<p class="tagline">Generá el video completo automáticamente. Solo completá las credenciales en <code>.env</code>.</p>', unsafe_allow_html=True)

# ─── Aviso si faltan credenciales ────────────────────────────────────────────
faltan = mensaje_credenciales()
if faltan:
    st.markdown(
        f'<div class="cred-warn"><strong>Completá las credenciales en <code>.env</code></strong><br>'
        f'Copiá <code>.env.example</code> a <code>.env</code> y rellená: {", ".join(faltan)}.</div>',
        unsafe_allow_html=True,
    )

# ─── Generar video completo (un solo lugar) ──────────────────────────────────
st.markdown('<div class="one-click"><strong>Generar video completo</strong></div>', unsafe_allow_html=True)
tema = st.text_input("Tema o idea del video", placeholder="Ej: Historia de la inteligencia artificial en 2 minutos", key="tema_todo")
nombre_proyecto = st.text_input("Nombre del proyecto (opcional)", placeholder="Para carpetas y archivos. Si está vacío se usa el tema.", key="nombre_todo")
col1, col2 = st.columns([1, 2])
with col1:
    generar = st.button("Generar video completo", type="primary", key="btn_generar_todo")

if generar:
    if not tema or not tema.strip():
        st.error("Escribí un tema o idea.")
    elif faltan:
        st.error("Completá las credenciales en .env y volvé a intentar.")
    else:
        with st.spinner("Generando… guion → escenas → imágenes → voz → video → metadata YouTube"):
            try:
                video_path, metadata_path = run(
                    tema=tema.strip(),
                    duracion_min=2,
                    plantilla="explicativo",
                    nombre_proyecto=(nombre_proyecto or "").strip() or None,
                    skip_imagenes=False,
                    skip_voz=False,
                    musica_fondo=None,
                    generar_metadata=True,
                )
                clear_result()
                st.session_state.video_path = video_path
                st.session_state.video_bytes = video_path.read_bytes()
                st.session_state.video_name = video_path.name
                if metadata_path and metadata_path.exists():
                    st.session_state.metadata_path = metadata_path
                    st.session_state.metadata_text = metadata_path.read_text(encoding="utf-8")
                st.rerun()
            except Exception as e:
                st.exception(e)

# ─── Resultado: video + metadata ──────────────────────────────────────────────
if st.session_state.video_path and st.session_state.video_bytes:
    st.success("Video listo para subir.")
    st.video(st.session_state.video_path)
    st.download_button(
        "Descargar MP4",
        data=st.session_state.video_bytes,
        file_name=st.session_state.video_name or "video.mp4",
        mime="video/mp4",
        key="dl_video",
    )
    if st.session_state.metadata_text:
        st.subheader("Metadata para YouTube")
        st.text_area("Descripción y capítulos (copiá a YouTube)", value=st.session_state.metadata_text, height=280, key="meta_display")
        st.download_button(
            "Descargar metadata (.txt)",
            data=st.session_state.metadata_text,
            file_name=(Path(st.session_state.metadata_path).name if st.session_state.metadata_path else "youtube_metadata.txt"),
            mime="text/plain",
            key="dl_meta",
        )
    if st.button("Generar otro video", key="btn_otro"):
        clear_result()
        st.rerun()

# ─── Modo avanzado (4 partes) ───────────────────────────────────────────────
with st.expander("Modo avanzado (paso a paso: Guion → Escenas → Voz → Video)"):
    from src.script_generator import generar_guion, guardar_guion
    from src.scene_splitter import dividir_en_escenas, escenas_a_texto_continuo
    from src.prompt_builder import prompts_para_escenas
    from src.voice_generator import generar_voz
    from src.image_generator import generar_lote, OUTPUT_IMAGES
    from src.video_assembler import montar_video
    from src.regeneration import guardar_prompts_por_escena

    for key, default in [("guion_texto", ""), ("nombre_proyecto", ""), ("audio_path", None)]:
        if key not in st.session_state:
            st.session_state[key] = default

    tab1, tab2, tab3, tab4 = st.tabs(["📝 Guion", "🎞️ Escenas", "🔊 Voz", "🎬 Video"])
    with tab1:
        st.caption("Generar guion por tema o pegar/subir texto.")
        modo = st.radio("Modo", ["Por tema", "Pegar guion"], horizontal=True, label_visibility="collapsed", key="ma_modo")
        if modo == "Por tema":
            t = st.text_input("Tema", key="ma_tema")
            d = st.number_input("Duración (min)", 1, 15, 2, key="ma_duracion")
            if st.button("Generar guion", key="ma_btn_guion") and t:
                with st.spinner("Generando..."):
                    texto = generar_guion(t.strip(), duracion_min=d)
                    st.session_state.guion_texto = texto
                    st.session_state.nombre_proyecto = (t[:30].replace(" ", "_"))
                    guardar_guion(texto, st.session_state.nombre_proyecto)
                st.success("Listo. Pasá a Escenas.")
        else:
            g = st.text_area("Guion", value=st.session_state.get("guion_texto", ""), height=180, key="ma_guion")
            f = st.file_uploader("O .txt", type=["txt"], key="ma_file")
            if f:
                st.session_state.guion_texto = f.read().decode("utf-8")
                st.rerun()
            if st.button("Usar este guion", key="ma_use") and g:
                st.session_state.guion_texto = g
                st.success("Listo.")
                st.rerun()
        if st.session_state.get("guion_texto"):
            st.text(st.session_state.guion_texto[:300] + ("..." if len(st.session_state.guion_texto) > 300 else ""))

    with tab2:
        st.caption("Dividir guion en escenas (5 s cada una).")
        txt = st.text_area("Guion", value=st.session_state.get("guion_texto", ""), height=160, key="ma_escenas_txt")
        if st.button("Dividir en escenas", key="ma_dividir") and txt:
            st.session_state.guion_texto = txt.strip()
            st.rerun()
        if st.session_state.get("guion_texto"):
            escenas = dividir_en_escenas(st.session_state.guion_texto)
            for e in escenas:
                st.markdown(f"**#{e.numero}** ({e.duracion_segundos:.0f}s) {e.texto[:80]}…")

    with tab3:
        st.caption("Generar voz (narración) del guion.")
        escenas_v = dividir_en_escenas(st.session_state.guion_texto) if st.session_state.get("guion_texto") else []
        texto_voz = escenas_a_texto_continuo(escenas_v) if escenas_v else ""
        tv = st.text_area("Texto para voz", value=texto_voz, height=140, key="ma_texto_voz")
        if st.button("Generar voz", key="ma_btn_voz") and tv:
            with st.spinner("Generando audio..."):
                path = generar_voz(tv.strip(), nombre_archivo=st.session_state.get("nombre_proyecto") or "narracion")
                st.session_state.audio_path = path
            st.success("Listo.")
        if st.session_state.get("audio_path"):
            p = st.session_state.audio_path
            p = Path(p) if isinstance(p, str) else p
            if p.exists() and p.stat().st_size > 0:
                st.audio(str(p))
                st.download_button("Descargar audio", data=p.read_bytes(), file_name=p.name, mime="audio/mpeg", key="ma_dl_audio")

    with tab4:
        st.caption("Generar imágenes y montar video.")
        if not st.session_state.get("guion_texto"):
            st.info("Cargá un guion en la pestaña Guion.")
        else:
            proy = st.text_input("Proyecto", value=st.session_state.get("nombre_proyecto") or "mi_video", key="ma_proy")
            if st.button("Generar imágenes y video", key="ma_btn_vid"):
                nombre = (proy or "mi_video").strip() or "mi_video"
                escenas = dividir_en_escenas(st.session_state.guion_texto)
                escenas_con_prompts = prompts_para_escenas(escenas)
                guardar_prompts_por_escena(escenas_con_prompts, nombre)
                with st.spinner("Imágenes..."):
                    generar_lote(escenas_con_prompts, subcarpeta=nombre)
                imgs = sorted((OUTPUT_IMAGES / nombre).glob("escena_*.png"))
                audio_p = st.session_state.get("audio_path")
                if audio_p:
                    audio_p = Path(audio_p) if isinstance(audio_p, str) else audio_p
                    if not audio_p.exists() or audio_p.stat().st_size == 0:
                        audio_p = None
                with st.spinner("Montando video..."):
                    vp = montar_video(imgs, audio_p, None, nombre_salida=nombre)
                st.success(f"Video: {vp}")
                st.video(str(vp))
                st.download_button("Descargar MP4", data=vp.read_bytes(), file_name=vp.name, mime="video/mp4", key="ma_dl_vid")
