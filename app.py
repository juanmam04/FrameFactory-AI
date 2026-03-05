"""
FrameFactory-AI – Un solo lugar para generar el video completo.
Solo hace falta completar las credenciales en .env
Ejecutar: streamlit run app.py
"""
import os
import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st
from dotenv import load_dotenv

from src.config_loader import BASE, get_narrative_rules, get_plantillas_guion, get_instrucciones_descripcion, get_instrucciones_miniatura, get_instrucciones_imagenes
from src.image_generator import COMFY_URL, _comfyui_disponible, comfyui_es_remoto, _usar_openai_imagenes
from src.pipeline import run, sanitizar_nombre_proyecto
from src.history import cargar_historial, obtener_video_por_id, eliminar_del_historial
from src.script_generator import guardar_guion
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
    backend = (os.getenv("IMAGE_BACKEND") or "openai").strip().lower()
    if backend == "comfyui" and not os.getenv("COMFYUI_URL", "").strip() and not os.getenv("SD_API_URL", "").strip():
        faltan.append("COMFYUI_URL (ej. http://127.0.0.1:8188) para generar imágenes")
    if backend == "openai" and not os.getenv("OPENAI_API_KEY", "").strip():
        # OPENAI_API_KEY ya se pide para guiones; si solo quieren imágenes con DALL-E, igual lo necesitan
        pass  # ya listado como OPENAI_API_KEY (guiones)
    return faltan


def generar_descripcion_breve_desde_titulo(titulo: str) -> str:
    """
    Devuelve una descripción corta (1–3 frases) para el video usando IA.
    Describe qué ES el video (formato POV, vida completa), sin lenguaje promocional.
    """
    titulo = (titulo or "").strip()
    if not titulo:
        return ""

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return f"POV: vivís la vida completa del personaje según el título. Narración en segunda persona, estilo mini-película."

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        system_prompt = (
            "Escribís descripciones breves (1–3 frases) en español para videos POV. "
            "La descripción debe decir QUÉ ES el video: formato (POV, segunda persona, vida completa del personaje), no promocionarlo. "
            "PROHIBIDO usar frases como: 'Sumérgete en...', 'No te lo pierdas', 'Este video te llevará...', 'vivirás la adrenalina...'. "
            "Sí decir de forma neutra: que es una historia en segunda persona donde el espectador vive la vida completa del personaje (infancia, obstáculos, gloria, caídas). "
            "Sin emojis, sin hashtags, sin listas."
        )
        user_prompt = (
            f"Título del video: {titulo}\n\n"
            "Escribí 1–3 frases que describan qué es el video: formato POV, vida completa del personaje, narración en segunda persona. "
            "Tono neutro e informativo. No promociones ni invites a verlo; solo describe el contenido."
        )

        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=200,
            temperature=0.4,
        )
        desc = (response.choices[0].message.content or "").strip()
        return desc
    except Exception as e:
        print(f"⚠️ Error generando descripción breve: {e}")
        return f"POV: vivís la vida completa del personaje según el título. Narración en segunda persona, estilo mini-película."


def iniciar_comfyui_background() -> tuple[bool, str | None]:
    """
    Inicia ComfyUI en segundo plano (puerto 8188) usando scripts/start_comfyui.ps1.
    Retorna (True, None) si se lanzó bien, o (False, mensaje_error).
    """
    script_path = BASE / "scripts" / "start_comfyui.ps1"
    if not script_path.exists():
        return False, "No se encontró scripts/start_comfyui.ps1"
    try:
        env = os.environ.copy()
        if os.getenv("COMFYUI_PATH"):
            env["COMFYUI_PATH"] = os.environ["COMFYUI_PATH"]
        creationflags = 0
        if sys.platform == "win32":
            detach = getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | detach
        subprocess.Popen(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(script_path)],
            cwd=str(BASE),
            env=env,
            creationflags=creationflags,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True, None
    except FileNotFoundError:
        return False, "No se encontró PowerShell. Iniciá ComfyUI manualmente en una terminal."
    except Exception as e:
        return False, str(e)


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
    ("word_count", None),
    ("estimated_minutes", None),
    ("target_words", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default


def clear_result():
    st.session_state.video_path = None
    st.session_state.video_bytes = None
    st.session_state.video_name = None
    st.session_state.metadata_path = None
    st.session_state.metadata_text = None
    st.session_state.word_count = None
    st.session_state.estimated_minutes = None
    st.session_state.target_words = None


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
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; max-width: 1200px; padding-left: 2rem; padding-right: 2rem; }
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
    _ffmpeg_cmd = "brew install ffmpeg" if sys.platform == "darwin" else "winget install ffmpeg o choco install ffmpeg"
    st.markdown(
        '<div class="cred-warn"><strong>⚠️ FFmpeg no está instalado</strong><br>'
        'FFmpeg es necesario para montar los videos.<br>'
        f'<strong>En esta PC:</strong> <code>{_ffmpeg_cmd}</code><br>'
        'O descargá desde: <a href="https://ffmpeg.org/download.html" target="_blank">ffmpeg.org</a>. '
        'Reiniciá la aplicación después de instalar.</div>',
        unsafe_allow_html=True,
    )

# ─── Generar video completo (un solo lugar) ──────────────────────────────────
st.markdown('<div class="one-click"><strong>Generar video completo</strong></div>', unsafe_allow_html=True)
titulo_video = st.text_input(
    "Título del video",
    placeholder="Ej: La historia de la inteligencia artificial en 2 minutos",
    key="titulo_todo",
)

col_desc1, col_desc2 = st.columns([3, 1])
# Sugerencia con IA: guardamos en una clave auxiliar y al rerun la copiamos al widget ANTES de crearlo
if "_descripcion_sugerida" in st.session_state:
    st.session_state.descripcion_breve_text = st.session_state._descripcion_sugerida
    del st.session_state._descripcion_sugerida
if "descripcion_breve_text" not in st.session_state:
    st.session_state.descripcion_breve_text = ""
with col_desc1:
    descripcion_breve = st.text_area(
        "Descripción breve del video",
        placeholder="Ej: Un recorrido rápido y claro por los hitos clave de la inteligencia artificial, desde sus orígenes hasta hoy.",
        help="Usá 1–3 frases para contar de qué va el video y qué promete al espectador.",
        key="descripcion_breve_text",
    )
with col_desc2:
    st.caption("Podés dejarlo vacío y generarlo con IA.")
    if st.button("Sugerir descripción con IA", key="btn_sugerir_desc"):
        if not (titulo_video or "").strip():
            st.warning("Escribí primero un título para sugerir una descripción.")
        else:
            sugerida = generar_descripcion_breve_desde_titulo(titulo_video)
            if sugerida:
                st.session_state._descripcion_sugerida = sugerida
                st.rerun()

nombre_proyecto = st.text_input(
    "Nombre del proyecto (opcional)",
    placeholder="Para carpetas y archivos. Si está vacío se usa el título.",
    key="nombre_todo",
)

# Tema interno para el pipeline: combina título + descripción
if (titulo_video or "").strip() and (descripcion_breve or "").strip():
    tema = f"{titulo_video.strip()}. {descripcion_breve.strip()}"
elif (titulo_video or "").strip():
    tema = titulo_video.strip()
else:
    tema = ""

# Configuración del video
col1, col2, col3 = st.columns(3)
with col1:
    target_words = st.number_input(
        "Palabras objetivo",
        min_value=80,
        max_value=3000,
        value=280,
        step=10,
        help="Número objetivo de palabras para el guion. La historia será completa pero ajustada a este límite.",
        key="target_words_todo"
    )
    
    # Calcular y mostrar estimado de minutos en tiempo real (considerando velocidad de voz)
    words_per_minute = 140
    estimated_minutes_base = target_words / words_per_minute
    # Usar velocidad de voz del session state o valor por defecto
    velocidad_voz_default = st.session_state.get("velocidad_voz_todo", 1.2)
    estimated_minutes_ajustado = estimated_minutes_base / velocidad_voz_default
    estimated_seconds = int((estimated_minutes_ajustado % 1) * 60)
    estimated_minutes_int = int(estimated_minutes_ajustado)
    
    if estimated_minutes_ajustado < 2:
        st.caption(f"≈ {estimated_minutes_int} min {estimated_seconds} s")
    else:
        st.caption(f"≈ {estimated_minutes_ajustado:.1f} min")

with col2:
    velocidad_voz = st.slider(
        "Velocidad de la voz",
        min_value=0.5,
        max_value=2.0,
        value=1.2,
        step=0.1,
        help="1.0 = normal, 1.2 = 20% más rápido, 0.8 = 20% más lento",
        key="velocidad_voz_todo"
    )
    
    # Recalcular y mostrar estimado actualizado con la velocidad seleccionada
    if velocidad_voz != velocidad_voz_default:
        estimated_minutes_ajustado_actual = estimated_minutes_base / velocidad_voz
        estimated_seconds_actual = int((estimated_minutes_ajustado_actual % 1) * 60)
        estimated_minutes_int_actual = int(estimated_minutes_ajustado_actual)
        if estimated_minutes_ajustado_actual < 2:
            st.caption(f"≈ {estimated_minutes_int_actual} min {estimated_seconds_actual} s (con velocidad {velocidad_voz}x)")
        else:
            st.caption(f"≈ {estimated_minutes_ajustado_actual:.1f} min (con velocidad {velocidad_voz}x)")

with col3:
    # Opcional: rango de palabras (colapsado por defecto)
    show_range = st.checkbox("Mostrar rango de palabras (opcional)", value=False, key="show_range_todo")
    if show_range:
        min_words = st.number_input(
            "Mín palabras",
            min_value=80,
            max_value=3000,
            value=int(target_words * 0.8),
            step=10,
            help="Mínimo de palabras aceptable (por defecto 80% del objetivo)",
            key="min_words_todo"
        )
        max_words = st.number_input(
            "Máx palabras",
            min_value=80,
            max_value=3000,
            value=int(target_words * 1.2),
            step=10,
            help="Máximo de palabras aceptable (por defecto 120% del objetivo)",
            key="max_words_todo"
        )
    else:
        min_words = None
        max_words = None

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
        "Saltar generación de imágenes",
        value=False,
        help="Si lo marcás, el video se genera solo con voz (sin imágenes). Útil cuando ComfyUI no está corriendo; ver README o SETUP.",
        key="skip_imgs_todo"
    )
    
    if not skip_imagenes:
        imagen_ia = st.radio(
            "IA para generar imágenes",
            options=["ComfyUI (local o RunPod)", "OpenAI DALL-E"],
            index=0,
            help="ComfyUI: mejor calidad, requiere ComfyUI en 8188. DALL-E: probar sin ComfyUI, usa créditos OpenAI.",
            key="imagen_ia_todo",
        )
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
        imagen_ia = "ComfyUI (local o RunPod)"
        segundos_por_imagen = 5.0
    
    skip_miniatura = st.checkbox(
        "Saltar generación de miniatura",
        value=False,
        help="No generar miniatura automáticamente.",
        key="skip_thumb_todo"
    )

if not skip_imagenes:
    usar_dalle = imagen_ia == "OpenAI DALL-E"
    comfy_ok = _comfyui_disponible()
    if usar_dalle:
        st.success("Imágenes con **OpenAI DALL-E**. No hace falta ComfyUI (usa créditos OpenAI).")
    elif comfy_ok:
        donde = "remoto (RunPod/nube)" if comfyui_es_remoto() else "local"
        st.success(f"ComfyUI: disponible ({donde}). Las imágenes se generarán con IA — {COMFY_URL}")
    else:
        st.warning(
            "ComfyUI no está corriendo. Elegí **OpenAI DALL-E** en Opciones avanzadas para probar sin ComfyUI, "
            "o iniciá ComfyUI en el puerto 8188."
        )
        if st.button("▶️ Iniciar ComfyUI en segundo plano", key="btn_iniciar_comfy"):
            ok, err = iniciar_comfyui_background()
            if ok:
                st.success("ComfyUI se está iniciando. Esperá 20–30 segundos y recargá la página (F5) para que lo detecte.")
            else:
                st.error(f"No se pudo iniciar ComfyUI: {err}. Verificá que tengas ComfyUI instalado y, si está en otra ruta, definí COMFYUI_PATH en .env.")

col1, col2 = st.columns([1, 2])
with col1:
    generar = st.button("Generar video completo", type="primary", key="btn_generar_todo")

if generar:
    bloqueado = False
    if not tema or not tema.strip():
        st.error("Escribí un tema o idea.")
        bloqueado = True
    elif faltan:
        st.error("Completá las credenciales en .env y volvé a intentar.")
    elif not skip_imagenes and imagen_ia != "OpenAI DALL-E" and not _comfyui_disponible():
        st.error("ComfyUI no está corriendo. Inicialo en el puerto 8188 o elegí «OpenAI DALL-E» en Opciones avanzadas.")
    else:
        mensaje_spinner = "Generando… guion → escenas"
        if not skip_imagenes:
            mensaje_spinner += " → imágenes"
        mensaje_spinner += " → voz → video → metadata YouTube"
        # Barra de progreso para imágenes (así se ve que avanza y no está trancado)
        progress_bar = st.progress(0) if not skip_imagenes else None
        progress_status = st.empty() if not skip_imagenes else None

        def on_progress_imagenes(current: int, total: int):
            if progress_bar is not None:
                progress_bar.progress(current / total if total else 0)
            if progress_status is not None:
                progress_status.caption(f"Generando imagen **{current}** de **{total}**… (cada una puede tardar 20–60 s)")

        with st.spinner(mensaje_spinner):
            try:
                # Aplicar elección de IA para imágenes (el pipeline lee USE_OPENAI_IMAGES)
                os.environ["USE_OPENAI_IMAGES"] = "true" if (not skip_imagenes and imagen_ia == "OpenAI DALL-E") else "false"
                video_path, metadata_path, thumbnail_path, info_dict = run(
                    tema=tema.strip(),
                    target_words=target_words,
                    min_words=min_words,
                    max_words=max_words,
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
                    on_progress_imagenes=on_progress_imagenes if not skip_imagenes else None,
                )
                clear_result()
                st.session_state.video_path = video_path
                st.session_state.video_bytes = video_path.read_bytes()
                st.session_state.video_name = video_path.name
                st.session_state.word_count = info_dict.get("word_count", 0)
                st.session_state.estimated_minutes = info_dict.get("estimated_minutes", 0.0)
                st.session_state.estimated_minutes_ajustado = info_dict.get("estimated_minutes_ajustado", 0.0)
                st.session_state.target_words = info_dict.get("target_words", target_words)
                st.session_state.duracion_real_segundos = info_dict.get("duracion_real_segundos", None)
                st.session_state.duracion_audio_segundos = info_dict.get("duracion_audio_segundos", None)
                st.session_state.velocidad_voz_usada = velocidad_voz
                st.session_state.palabras_narracion = info_dict.get("palabras_narracion", st.session_state.get("word_count", 0))
                
                # Guardar guion en session state para mostrarlo (desde el archivo guardado, completo)
                nombre_proy = (nombre_proyecto or tema[:30].replace(" ", "_")).strip() or None
                nombre_proy = sanitizar_nombre_proyecto(nombre_proy) if nombre_proy else sanitizar_nombre_proyecto(tema[:30].replace(" ", "_"))
                guion_path = BASE / "output" / "guiones" / f"{nombre_proy}.txt"
                if guion_path.exists():
                    guion_completo = guion_path.read_text(encoding="utf-8")
                    st.session_state.guion_completo = guion_completo
                    # Verificar que el guion no esté cortado
                    if len(guion_completo.strip()) < 100:
                        st.warning("⚠️ El guion guardado parece muy corto. Puede estar incompleto.")
                else:
                    st.warning(f"⚠️ No se encontró el archivo de guion en: {guion_path}")
                
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
    st.success("✅ Video generado exitosamente")
    
    # Mostrar información del guion generado
    if st.session_state.get("word_count") is not None:
        word_count = st.session_state.word_count
        target_words = st.session_state.get("target_words", word_count)
        estimated_minutes_base = st.session_state.get("estimated_minutes", 0.0)
        
        # Obtener velocidad de voz usada (si está disponible)
        velocidad_usada = st.session_state.get("velocidad_voz_usada", 1.2)
        estimated_minutes_real = estimated_minutes_base / velocidad_usada
        
        # Obtener duración real del video si está disponible
        duracion_real_segundos = st.session_state.get("duracion_real_segundos", None)
        
        col_info1, col_info2, col_info3, col_info4 = st.columns(4)
        with col_info1:
            st.metric("Palabras generadas", f"{word_count} / {target_words}")
        with col_info2:
            if duracion_real_segundos:
                duracion_real_min = duracion_real_segundos / 60.0
                st.metric("Duración real", f"{duracion_real_segundos:.0f}s ({duracion_real_min:.1f} min)")
            else:
                st.metric("Duración estimada", f"≈ {estimated_minutes_real:.1f} min")
        with col_info3:
            diferencia = word_count - target_words
            if abs(diferencia) <= 20:
                st.metric("Estado", "✅ Objetivo cumplido", delta=None)
            elif diferencia > 20:
                st.metric("Estado", f"⚠️ +{diferencia} palabras", delta=f"+{diferencia}")
            else:
                st.metric("Estado", f"⚠️ {diferencia} palabras", delta=diferencia)
        with col_info4:
            duracion_audio_segundos = st.session_state.get("duracion_audio_segundos", None)
            if duracion_real_segundos and estimated_minutes_base > 0:
                diferencia_duracion = (duracion_real_segundos / 60.0) - estimated_minutes_real
                if abs(diferencia_duracion) > 0.5:
                    st.metric("⚠️ Duración", f"Desviación: {diferencia_duracion:+.1f} min", delta=f"{diferencia_duracion:+.1f}")
                    # Mostrar información adicional si hay gran diferencia
                    if abs(diferencia_duracion) > 2.0:
                        palabras_narracion = st.session_state.get("palabras_narracion", word_count)
                        if duracion_audio_segundos:
                            palabras_por_min_real = (palabras_narracion / duracion_audio_segundos) * 60
                            st.caption(f"⚠️ Audio: {duracion_audio_segundos/60:.1f} min")
                            st.caption(f"📊 Velocidad real: {palabras_por_min_real:.0f} palabras/min")
                            st.caption(f"📊 Esperado: 140 palabras/min × {velocidad_usada:.1f}x = {140*velocidad_usada:.0f} palabras/min")
                else:
                    st.metric("✅ Duración", "Correcta", delta=None)
    
    # Video
    st.subheader("🎬 Video generado")
    st.video(st.session_state.video_path)
    st.caption("Si ves barra de reproducción o controles, es el reproductor de la app. El archivo MP4 descargado no los incluye; abrirlo en VLC o otro reproductor para ver solo el contenido.")
    st.download_button(
        "📥 Descargar video (MP4)",
        data=st.session_state.video_bytes,
        file_name=st.session_state.video_name or "video.mp4",
        mime="video/mp4",
        key="dl_video",
    )
    
    # Archivos generados - Tabs para organizar mejor
    st.subheader("📁 Archivos generados")
    tabs_archivos = st.tabs(["📝 Guion", "🎞️ Escenas por imagen", "🖼️ Miniatura", "📄 Metadata YouTube", "📂 Todos los archivos"])
    
    with tabs_archivos[0]:  # Guion
        if st.session_state.get("guion_completo"):
            st.markdown("**Guion completo generado:**")
            st.text_area(
                "Guion",
                value=st.session_state.guion_completo,
                height=400,
                key="guion_completo_display",
                label_visibility="collapsed"
            )
            st.download_button(
                "📥 Descargar guion completo (.txt)",
                data=st.session_state.guion_completo,
                file_name=f"{st.session_state.video_name.replace('.mp4', '')}_guion.txt",
                mime="text/plain",
                key="dl_guion_completo"
            )
            
            # Información del archivo guardado
            nombre_proy = st.session_state.video_name.replace('.mp4', '')
            guion_path = BASE / "output" / "guiones" / f"{nombre_proy}.txt"
            if guion_path.exists():
                st.caption(f"💾 Guardado en: `{guion_path.relative_to(BASE)}`")
        else:
            st.info("El guion no está disponible en la sesión actual.")
    
    with tabs_archivos[1]:  # Escenas por imagen
        nombre_proy_escenas = st.session_state.video_name.replace('.mp4', '')
        nombre_proy_sanit_escenas = sanitizar_nombre_proyecto(nombre_proy_escenas)
        imagenes_dir_escenas = BASE / "output" / "imagenes" / nombre_proy_sanit_escenas
        try:
            from src.regeneration import cargar_prompts
            escenas_con_prompts = cargar_prompts(nombre_proy_sanit_escenas)
        except Exception:
            escenas_con_prompts = []
        if escenas_con_prompts and imagenes_dir_escenas.exists():
            st.markdown("**Escena del guion usada para cada imagen:**")
            st.caption("Cada imagen del video se generó a partir del texto de la escena (y su descripción visual).")
            for escena, prompt in escenas_con_prompts:
                img_path = imagenes_dir_escenas / f"escena_{escena.numero:04d}.png"
                with st.expander(f"Escena {escena.numero} — {escena.duracion_segundos:.0f}s", expanded=(escena.numero <= 3)):
                    if img_path.exists():
                        st.image(str(img_path), caption=f"Imagen escena {escena.numero}", use_container_width=True)
                    else:
                        st.caption(f"🖼️ Imagen no encontrada: `{img_path.name}`")
                    st.markdown("**Texto de la escena (guion):**")
                    st.text_area(
                        f"Escena {escena.numero}",
                        value=escena.texto,
                        height=140,
                        key=f"escena_text_{nombre_proy_sanit_escenas}_{escena.numero}",
                        label_visibility="collapsed",
                    )
                    with st.expander("Ver prompt usado para la imagen"):
                        st.text(prompt)
        elif not escenas_con_prompts:
            st.info("No hay datos de escenas guardados para este proyecto (output/meta). Si generaste el video sin imágenes, no se guardaron escenas.")
        else:
            st.info("No se encontraron imágenes de escenas para este proyecto.")
    
    with tabs_archivos[2]:  # Miniatura (índice 2)
        if st.session_state.get("thumbnail_path") and st.session_state.get("thumbnail_bytes"):
            st.markdown("**Miniatura generada:**")
            st.image(st.session_state.thumbnail_bytes, caption="Miniatura del video", use_container_width=True)
            st.download_button(
                "📥 Descargar miniatura (PNG)",
                data=st.session_state.thumbnail_bytes,
                file_name=st.session_state.thumbnail_path.name if st.session_state.get("thumbnail_path") else "thumbnail.png",
                mime="image/png",
                key="dl_thumbnail",
            )
            if st.session_state.get("thumbnail_path"):
                st.caption(f"💾 Guardado en: `{Path(st.session_state.thumbnail_path).relative_to(BASE)}`")
        else:
            st.info("No se generó miniatura para este video.")
    
    with tabs_archivos[3]:  # Metadata YouTube
        if st.session_state.metadata_text:
            st.markdown("**Metadata para YouTube (descripción y capítulos):**")
            st.text_area(
                "Descripción y capítulos",
                value=st.session_state.metadata_text,
                height=400,
                key="meta_display",
                label_visibility="collapsed",
                help="Copiá este texto y pegalo en la descripción de YouTube"
            )
            st.download_button(
                "📥 Descargar metadata (.txt)",
                data=st.session_state.metadata_text,
                file_name=(Path(st.session_state.metadata_path).name if st.session_state.metadata_path else "youtube_metadata.txt"),
                mime="text/plain",
                key="dl_meta",
            )
            if st.session_state.metadata_path:
                st.caption(f"💾 Guardado en: `{Path(st.session_state.metadata_path).relative_to(BASE)}`")
        else:
            st.info("No se generó metadata para este video.")
    
    with tabs_archivos[4]:  # Todos los archivos
        st.markdown("**Ubicación de todos los archivos generados:**")
        
        nombre_proy = st.session_state.video_name.replace('.mp4', '')
        nombre_proy_sanitizado = sanitizar_nombre_proyecto(nombre_proy)
        
        # Listar archivos generados
        archivos_info = []
        
        # Video
        if st.session_state.video_path:
            archivos_info.append(("🎬 Video", st.session_state.video_path.relative_to(BASE), "MP4"))
        
        # Guion
        guion_path = BASE / "output" / "guiones" / f"{nombre_proy_sanitizado}.txt"
        if guion_path.exists():
            archivos_info.append(("📝 Guion", guion_path.relative_to(BASE), "TXT"))
        
        # Miniatura
        if st.session_state.get("thumbnail_path"):
            archivos_info.append(("🖼️ Miniatura", Path(st.session_state.thumbnail_path).relative_to(BASE), "PNG"))
        
        # Metadata
        if st.session_state.metadata_path:
            archivos_info.append(("📄 Metadata", Path(st.session_state.metadata_path).relative_to(BASE), "TXT"))
        
        # Audio
        audio_path = BASE / "output" / "audio" / f"{nombre_proy_sanitizado}.mp3"
        if audio_path.exists():
            archivos_info.append(("🔊 Audio", audio_path.relative_to(BASE), "MP3"))
        
        # Imágenes
        imagenes_dir = BASE / "output" / "imagenes" / nombre_proy_sanitizado
        if imagenes_dir.exists():
            imagenes = list(imagenes_dir.glob("escena_*.png"))
            if imagenes:
                archivos_info.append(("🎨 Imágenes", f"{imagenes_dir.relative_to(BASE)} ({len(imagenes)} archivos)", "PNG"))
        
        if archivos_info:
            for icono_nombre, ruta, tipo in archivos_info:
                st.markdown(f"**{icono_nombre}** - `{ruta}` ({tipo})")
        else:
            st.info("No se encontraron archivos adicionales.")
        
        st.markdown("---")
        st.markdown(f"**📂 Carpeta base del proyecto:** `output/{nombre_proy_sanitizado}/`")
    
    # Botón para generar otro video
    st.markdown("---")
    if st.button("🔄 Generar otro video", key="btn_otro", type="primary"):
        clear_result()
        st.rerun()

# ─── Historial de Videos ────────────────────────────────────────────────────
st.markdown("---")
with st.expander("📚 Historial de Videos Generados"):
    historial = cargar_historial()
    
    if not historial:
        st.info("Aún no has generado ningún video. ¡Crea tu primer video arriba!")
    else:
        st.markdown(f"**Total de videos generados: {len(historial)}**")
        
        # Filtros
        col_filtro1, col_filtro2 = st.columns(2)
        with col_filtro1:
            buscar_tema = st.text_input("🔍 Buscar por tema", key="historial_buscar", placeholder="Escribe para filtrar...")
        with col_filtro2:
            ordenar_por = st.selectbox("Ordenar por", ["Más reciente", "Más antiguo", "Tema (A-Z)"], key="historial_ordenar")
        
        # Filtrar y ordenar
        historial_filtrado = historial
        if buscar_tema:
            historial_filtrado = [h for h in historial_filtrado if buscar_tema.lower() in h.get("tema", "").lower() or buscar_tema.lower() in h.get("nombre_proyecto", "").lower()]
        
        if ordenar_por == "Más antiguo":
            historial_filtrado = list(reversed(historial_filtrado))
        elif ordenar_por == "Tema (A-Z)":
            historial_filtrado = sorted(historial_filtrado, key=lambda x: x.get("tema", "").lower())
        
        if not historial_filtrado:
            st.warning("No se encontraron videos con ese criterio de búsqueda.")
        else:
            st.markdown(f"**Mostrando {len(historial_filtrado)} de {len(historial)} videos**")
            
            # Mostrar cada video
            for idx, video in enumerate(historial_filtrado):
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        fecha = video.get("fecha", "")
                        if fecha:
                            try:
                                from datetime import datetime
                                fecha_obj = datetime.fromisoformat(fecha)
                                fecha_formateada = fecha_obj.strftime("%d/%m/%Y %H:%M")
                            except:
                                fecha_formateada = fecha[:16]
                        else:
                            fecha_formateada = "Fecha desconocida"
                        
                        st.markdown(f"### {video.get('nombre_proyecto', 'Sin nombre')}")
                        st.caption(f"📅 {fecha_formateada} | 🎯 {video.get('tema', 'Sin tema')}")
                        st.caption(f"📊 {video.get('word_count', 0)} palabras | ⏱️ ≈ {video.get('estimated_minutes', 0):.1f} min")
                    
                    with col2:
                        video_path_str = video.get("video_path")
                        if video_path_str and Path(video_path_str).exists():
                            if st.button("▶️ Ver", key=f"ver_{video.get('id')}_{idx}"):
                                st.session_state.video_path = Path(video_path_str)
                                st.session_state.video_bytes = Path(video_path_str).read_bytes()
                                st.session_state.video_name = Path(video_path_str).name
                                # Cargar guion
                                guion_texto = video.get("guion_texto", "")
                                if guion_texto:
                                    st.session_state.guion_completo = guion_texto
                                st.rerun()
                        else:
                            st.caption("⚠️ Video no encontrado")
                    
                    with col3:
                        if st.button("🗑️ Eliminar", key=f"eliminar_{video.get('id')}_{idx}"):
                            if eliminar_del_historial(video.get("id")):
                                st.success("Video eliminado del historial")
                                st.rerun()
                            else:
                                st.error("Error al eliminar")
                    
                    # Mostrar guion si está disponible
                    guion_texto = video.get("guion_texto", "")
                    if guion_texto:
                        with st.expander(f"📝 Ver guion completo - {video.get('nombre_proyecto', 'Sin nombre')}"):
                            st.text_area(
                                "Guion",
                                value=guion_texto,
                                height=200,
                                key=f"guion_text_{video.get('id')}_{idx}",
                                label_visibility="collapsed"
                            )
                            st.download_button(
                                "📥 Descargar guion",
                                data=guion_texto,
                                file_name=f"{video.get('nombre_proyecto', 'guion')}_guion.txt",
                                mime="text/plain",
                                key=f"dl_guion_{video.get('id')}_{idx}"
                            )
                    
                    st.markdown("---")

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
            tw = st.number_input("Palabras objetivo", 80, 3000, 280, 10, key="ma_target_words")
            if st.button("Generar guion", key="ma_btn_guion") and t:
                with st.spinner("Generando..."):
                    texto, word_count, estimated_minutes = generar_guion(t.strip(), target_words=tw)
                    st.session_state.guion_texto = texto
                    st.session_state.word_count_ma = word_count
                    st.session_state.estimated_minutes_ma = estimated_minutes
                    nombre_temp = (t[:30].replace(" ", "_"))
                    st.session_state.nombre_proyecto = sanitizar_nombre_proyecto(nombre_temp)
                    guardar_guion(texto, st.session_state.nombre_proyecto)
                st.success(f"Listo. {word_count} palabras, ≈ {estimated_minutes:.1f} min. Pasá a Escenas.")
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
                tema_ctx = st.session_state.get("ma_tema") or st.session_state.get("nombre_proyecto") or nombre or ""
                escenas_con_prompts = prompts_para_escenas(escenas, tema=tema_ctx, usar_descripciones_ia=True)
                guardar_prompts_por_escena(escenas_con_prompts, nombre)
                # Limpiar imágenes viejas de este proyecto; una por escena
                carpeta_imgs = OUTPUT_IMAGES / nombre
                if carpeta_imgs.exists():
                    for f in carpeta_imgs.glob("escena_*.png"):
                        try:
                            f.unlink()
                        except OSError:
                            pass
                with st.spinner("Imágenes..."):
                    imgs = generar_lote(escenas_con_prompts, subcarpeta=nombre)
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
