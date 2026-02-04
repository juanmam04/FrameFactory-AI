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

from src.config_loader import BASE, get_narrative_rules, get_plantillas_guion, get_instrucciones_descripcion, get_instrucciones_miniatura, get_instrucciones_imagenes
from src.pipeline import run, sanitizar_nombre_proyecto
import yaml

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


def verificar_ffmpeg():
    """Verifica si FFmpeg está instalado, buscando en ubicaciones comunes de WinGet."""
    import shutil
    import os
    from pathlib import Path
    
    # Primero intentar con shutil.which (usa PATH actual)
    if shutil.which("ffmpeg"):
        return True
    
    # Si no está en PATH, buscar en ubicaciones comunes de WinGet
    posibles_rutas = [
        Path.home() / "AppData" / "Local" / "Microsoft" / "WinGet" / "Packages" / "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe",
        Path("C:/Program Files/ffmpeg/bin"),
        Path("C:/ffmpeg/bin"),
    ]
    
    for base_path in posibles_rutas:
        if base_path.exists():
            # Buscar ffmpeg.exe en subdirectorios
            for ffmpeg_exe in base_path.rglob("ffmpeg.exe"):
                if ffmpeg_exe.exists():
                    # Agregar al PATH del proceso actual
                    bin_dir = str(ffmpeg_exe.parent)
                    if bin_dir not in os.environ.get("PATH", ""):
                        os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
                    return True
    
    return False


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

# ─── Aviso si falta FFmpeg ──────────────────────────────────────────────────
if not verificar_ffmpeg():
    st.markdown(
        '<div class="cred-warn"><strong>⚠️ FFmpeg no está instalado</strong><br>'
        'FFmpeg es necesario para montar los videos. Instalalo desde: '
        '<a href="https://ffmpeg.org/download.html" target="_blank">https://ffmpeg.org/download.html</a><br>'
        'O usa: <code>winget install ffmpeg</code> o <code>choco install ffmpeg</code><br>'
        '<strong>IMPORTANTE:</strong> Agrega FFmpeg al PATH del sistema y reinicia la aplicación.</div>',
        unsafe_allow_html=True,
    )

# ─── Generar video completo (un solo lugar) ──────────────────────────────────
st.markdown('<div class="one-click"><strong>Generar video completo</strong></div>', unsafe_allow_html=True)
tema = st.text_input("Tema o idea del video", placeholder="Ej: Historia de la inteligencia artificial en 2 minutos", key="tema_todo")
nombre_proyecto = st.text_input("Nombre del proyecto (opcional)", placeholder="Para carpetas y archivos. Si está vacío se usa el tema.", key="nombre_todo")

# Configuración del video
col1, col2, col3 = st.columns(3)
with col1:
    duracion_min = st.number_input(
        "Duración mínima (minutos)",
        min_value=1,
        max_value=30,
        value=2,
        help="Duración mínima del video. El guion se generará para esta duración como mínimo.",
        key="duracion_min_todo"
    )
with col2:
    duracion_max = st.number_input(
        "Duración máxima (minutos)",
        min_value=1,
        max_value=60,
        value=5,
        help="Duración máxima del video. El guion no excederá esta duración.",
        key="duracion_max_todo"
    )
with col3:
    velocidad_voz = st.slider(
        "Velocidad de la voz",
        min_value=0.5,
        max_value=2.0,
        value=1.2,
        step=0.1,
        help="1.0 = normal, 1.2 = 20% más rápido, 0.8 = 20% más lento",
        key="velocidad_voz_todo"
    )

# Validar que duracion_max >= duracion_min
if duracion_max < duracion_min:
    st.warning(f"⚠️ La duración máxima ({duracion_max} min) debe ser mayor o igual a la mínima ({duracion_min} min). Se ajustará automáticamente.")
    duracion_max = duracion_min

# Formato del video
st.markdown("**📐 Formato del video:**")
formato_video = st.selectbox(
    "Selecciona el formato",
    options=[
        "YouTube (16:9) - 1920x1080",
        "YouTube Shorts (9:16) - 1080x1920",
        "TikTok (9:16) - 1080x1920",
        "Instagram Reels (9:16) - 1080x1920",
        "Instagram Stories (9:16) - 1080x1920",
        "Personalizado",
    ],
    index=0,
    help="El tamaño de las imágenes y el video se ajustará según el formato seleccionado.",
    key="formato_video_todo"
)

# Dimensiones según formato
FORMATOS = {
    "YouTube (16:9) - 1920x1080": (1920, 1080),
    "YouTube Shorts (9:16) - 1080x1920": (1080, 1920),
    "TikTok (9:16) - 1080x1920": (1080, 1920),
    "Instagram Reels (9:16) - 1080x1920": (1080, 1920),
    "Instagram Stories (9:16) - 1080x1920": (1080, 1920),
}

if formato_video == "Personalizado":
    col_w, col_h = st.columns(2)
    with col_w:
        width_custom = st.number_input(
            "Ancho (width)",
            min_value=256,
            max_value=4096,
            value=1920,
            step=64,
            key="width_custom_todo"
        )
    with col_h:
        height_custom = st.number_input(
            "Alto (height)",
            min_value=256,
            max_value=4096,
            value=1080,
            step=64,
            key="height_custom_todo"
        )
    video_width, video_height = width_custom, height_custom
else:
    video_width, video_height = FORMATOS[formato_video]

# Opciones avanzadas
with st.expander("⚙️ Opciones avanzadas"):
    skip_imagenes = st.checkbox(
        "Saltar generación de imágenes (video negro con voz)",
        value=False,
        help="Útil para probar el pipeline sin Stable Diffusion. Genera un video negro con la narración.",
        key="skip_imgs_todo"
    )
    
    if not skip_imagenes:
        segundos_por_imagen = st.number_input(
            "Segundos por imagen",
            min_value=1.0,
            max_value=10.0,
            value=5.0,
            step=0.5,
            help="Cuántos segundos dura cada imagen en el video.",
            key="seg_por_img_todo"
        )
    else:
        segundos_por_imagen = 5.0
    
    skip_miniatura = st.checkbox(
        "Saltar generación de miniatura",
        value=False,
        help="No generar miniatura automáticamente.",
        key="skip_thumb_todo"
    )

col1, col2 = st.columns([1, 2])
with col1:
    generar = st.button("Generar video completo", type="primary", key="btn_generar_todo")

if generar:
    if not tema or not tema.strip():
        st.error("Escribí un tema o idea.")
    elif faltan:
        st.error("Completá las credenciales en .env y volvé a intentar.")
    else:
        mensaje_spinner = "Generando… guion → escenas"
        if not skip_imagenes:
            mensaje_spinner += " → imágenes"
        mensaje_spinner += " → voz → video → metadata YouTube"
        with st.spinner(mensaje_spinner):
            try:
                video_path, metadata_path, thumbnail_path = run(
                    tema=tema.strip(),
                    duracion_min=duracion_min,
                    duracion_max=duracion_max,
                    plantilla="explicativo",
                    nombre_proyecto=(nombre_proyecto or "").strip() or None,
                    skip_imagenes=skip_imagenes,
                    skip_voz=False,
                    musica_fondo=None,
                    generar_metadata=True,
                    velocidad_voz=velocidad_voz,
                    segundos_por_imagen=segundos_por_imagen if not skip_imagenes else None,
                    width=video_width,
                    height=video_height,
                    skip_miniatura=skip_miniatura,
                )
                clear_result()
                st.session_state.video_path = video_path
                st.session_state.video_bytes = video_path.read_bytes()
                st.session_state.video_name = video_path.name
                if metadata_path and metadata_path.exists():
                    st.session_state.metadata_path = metadata_path
                    st.session_state.metadata_text = metadata_path.read_text(encoding="utf-8")
                if thumbnail_path and thumbnail_path.exists():
                    st.session_state.thumbnail_path = thumbnail_path
                    st.session_state.thumbnail_bytes = thumbnail_path.read_bytes()
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
    
    # Mostrar miniatura si se generó
    if st.session_state.get("thumbnail_path") and st.session_state.get("thumbnail_bytes"):
        st.subheader("🖼️ Miniatura generada")
        st.image(st.session_state.thumbnail_bytes, caption="Miniatura del video")
        st.download_button(
            "Descargar miniatura",
            data=st.session_state.thumbnail_bytes,
            file_name=st.session_state.thumbnail_path.name if st.session_state.get("thumbnail_path") else "thumbnail.png",
            mime="image/png",
            key="dl_thumbnail",
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

# ─── Editor de Instrucciones ────────────────────────────────────────────────
st.markdown("---")
with st.expander("⚙️ Editor de Instrucciones (Personalizar cómo se genera cada parte)"):
    st.markdown("### Personalizá las instrucciones para cada paso de generación")
    tab_guion, tab_descripcion, tab_miniatura, tab_imagenes = st.tabs(["📝 Guion", "📄 Descripción YouTube", "🖼️ Miniatura", "🎨 Imágenes"])
    
    with tab_guion:
        st.markdown("#### Instrucciones para generar guiones")
        rules = get_narrative_rules()
        plantillas = get_plantillas_guion()
        st.markdown("**Instrucciones generales (system_extra):**")
        system_extra_editado = st.text_area("Instrucciones que se agregan al prompt del sistema", value=rules.get("system_extra", ""), height=150, key="edit_system_extra")
        st.markdown("**Plantilla 'Explicativo' (sistema):**")
        explicativo_sistema = st.text_area("Prompt del sistema", value=plantillas.get("plantillas", {}).get("explicativo", {}).get("sistema", ""), height=100, key="edit_explicativo_sistema")
        st.markdown("**Plantilla 'Explicativo' (usuario):**")
        explicativo_usuario = st.text_area("Prompt del usuario (usa {tema} y {duracion_min})", value=plantillas.get("plantillas", {}).get("explicativo", {}).get("usuario", ""), height=200, key="edit_explicativo_usuario")
        if st.button("💾 Guardar instrucciones de guion", key="save_guion"):
            try:
                rules["system_extra"] = system_extra_editado
                with open(BASE / "config" / "narrative_rules.yaml", "w", encoding="utf-8") as f:
                    yaml.dump(rules, f, allow_unicode=True, default_flow_style=False)
                if "plantillas" not in plantillas:
                    plantillas["plantillas"] = {}
                if "explicativo" not in plantillas["plantillas"]:
                    plantillas["plantillas"]["explicativo"] = {}
                plantillas["plantillas"]["explicativo"]["sistema"] = explicativo_sistema
                plantillas["plantillas"]["explicativo"]["usuario"] = explicativo_usuario
                with open(BASE / "config" / "plantillas_guion.yaml", "w", encoding="utf-8") as f:
                    yaml.dump(plantillas, f, allow_unicode=True, default_flow_style=False)
                st.success("✅ Instrucciones de guion guardadas")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
    
    with tab_descripcion:
        st.markdown("#### Instrucciones para generar descripción de YouTube")
        instrucciones_desc = get_instrucciones_descripcion()
        desc_system = st.text_area("Prompt del sistema", value=instrucciones_desc.get("system_prompt", ""), height=200, key="edit_desc_system")
        desc_user = st.text_area("Template (usa {titulo}, {guion_resumen}, {capítulos_texto}, {hook}, {cta})", value=instrucciones_desc.get("user_prompt_template", ""), height=200, key="edit_desc_user")
        if st.button("💾 Guardar instrucciones de descripción", key="save_desc"):
            try:
                instrucciones_desc["system_prompt"] = desc_system
                instrucciones_desc["user_prompt_template"] = desc_user
                with open(BASE / "config" / "instrucciones_descripcion.yaml", "w", encoding="utf-8") as f:
                    yaml.dump(instrucciones_desc, f, allow_unicode=True, default_flow_style=False)
                st.success("✅ Instrucciones de descripción guardadas")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
    
    with tab_miniatura:
        st.markdown("#### Instrucciones para generar miniatura")
        instrucciones_thumb = get_instrucciones_miniatura()
        thumb_system = st.text_area("Prompt del sistema", value=instrucciones_thumb.get("system_prompt", ""), height=200, key="edit_thumb_system")
        thumb_user = st.text_area("Template (usa {titulo}, {tema}, {guion_resumen})", value=instrucciones_thumb.get("user_prompt_template", ""), height=200, key="edit_thumb_user")
        if st.button("💾 Guardar instrucciones de miniatura", key="save_thumb"):
            try:
                instrucciones_thumb["system_prompt"] = thumb_system
                instrucciones_thumb["user_prompt_template"] = thumb_user
                with open(BASE / "config" / "instrucciones_miniatura.yaml", "w", encoding="utf-8") as f:
                    yaml.dump(instrucciones_thumb, f, allow_unicode=True, default_flow_style=False)
                st.success("✅ Instrucciones de miniatura guardadas")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
    
    with tab_imagenes:
        st.markdown("#### Instrucciones para generación masiva de imágenes")
        st.caption("Configura cómo se generan las imágenes para cada escena del video.")
        instrucciones_img = get_instrucciones_imagenes()
        
        st.markdown("**Template del prompt:**")
        st.caption("Usa {plano}, {accion}, {estilo} como variables. El plano se selecciona automáticamente, la acción viene de la escena, y el estilo de visual_bible.yaml")
        prompt_template = st.text_area(
            "Template del prompt para cada imagen",
            value=instrucciones_img.get("prompt_template", "{plano}, {accion}, {estilo}, luz suave, fondo simple, alta calidad"),
            height=100,
            key="edit_img_template"
        )
        
        st.markdown("**Parámetros de Stable Diffusion:**")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            steps = st.number_input("Steps", min_value=1, max_value=100, value=instrucciones_img.get("parametros_sd", {}).get("steps", 25), key="edit_img_steps")
        with col2:
            width = st.number_input("Width", min_value=256, max_value=2048, value=instrucciones_img.get("parametros_sd", {}).get("width", 1024), key="edit_img_width")
        with col3:
            height = st.number_input("Height", min_value=256, max_value=2048, value=instrucciones_img.get("parametros_sd", {}).get("height", 576), key="edit_img_height")
        with col4:
            cfg_scale = st.number_input("CFG Scale", min_value=1.0, max_value=20.0, value=float(instrucciones_img.get("parametros_sd", {}).get("cfg_scale", 7)), step=0.5, key="edit_img_cfg")
        
        st.markdown("**Configuración de reintentos:**")
        col1, col2 = st.columns(2)
        with col1:
            max_reintentos = st.number_input("Máximo de reintentos", min_value=1, max_value=10, value=instrucciones_img.get("reintentos", {}).get("max_reintentos", 3), key="edit_img_max_retry")
        with col2:
            pausa_reintentos = st.number_input("Pausa entre reintentos (segundos)", min_value=1, max_value=30, value=instrucciones_img.get("reintentos", {}).get("pausa_segundos", 5), key="edit_img_pause")
        
        if st.button("💾 Guardar instrucciones de imágenes", key="save_img"):
            try:
                if "parametros_sd" not in instrucciones_img:
                    instrucciones_img["parametros_sd"] = {}
                if "reintentos" not in instrucciones_img:
                    instrucciones_img["reintentos"] = {}
                
                instrucciones_img["prompt_template"] = prompt_template
                instrucciones_img["parametros_sd"]["steps"] = steps
                instrucciones_img["parametros_sd"]["width"] = width
                instrucciones_img["parametros_sd"]["height"] = height
                instrucciones_img["parametros_sd"]["cfg_scale"] = cfg_scale
                instrucciones_img["reintentos"]["max_reintentos"] = max_reintentos
                instrucciones_img["reintentos"]["pausa_segundos"] = pausa_reintentos
                
                with open(BASE / "config" / "instrucciones_imagenes.yaml", "w", encoding="utf-8") as f:
                    yaml.dump(instrucciones_img, f, allow_unicode=True, default_flow_style=False)
                st.success("✅ Instrucciones de imágenes guardadas")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")


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
                    nombre_temp = (t[:30].replace(" ", "_"))
                    st.session_state.nombre_proyecto = sanitizar_nombre_proyecto(nombre_temp)
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
                nombre = sanitizar_nombre_proyecto((proy or "mi_video").strip() or "mi_video")
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
