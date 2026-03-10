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

from src.config_loader import BASE, get_narrative_rules, get_plantillas_guion, get_instrucciones_descripcion, get_instrucciones_miniatura, get_instrucciones_imagenes, get_subtitle_styles, get_instrucciones_titulo
from src.image_generator import COMFY_URL, _comfyui_disponible, comfyui_es_remoto, _replicate_disponible, generar_lote, OUTPUT_IMAGES
from src.pipeline import run, sanitizar_nombre_proyecto
from src.history import cargar_historial, obtener_video_por_id, eliminar_del_historial
from src.script_generator import guardar_guion, generar_guion
from src.scene_splitter import dividir_en_escenas, Escena
from src.prompt_builder import prompts_para_escenas, prompts_para_beats, emotion_to_expression_key
from src.regeneration import guardar_prompts_por_escena
from src.visual_beats import generar_beats_para_escenas, guardar_beats
from src.title_generator import sugerir_titulos_virales
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
        pass  # OPENAI_API_KEY ya se pide para guiones/voz
    return faltan


def generar_descripcion_breve_desde_titulo(titulo: str) -> str:
    """
    Devuelve una descripción tipo "trailer" (3–6 frases) para el video usando IA.
    Debe adelantar el tipo de vida/historia que se verá, sin volverse un copy promocional vacío.
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
            "Escribís descripciones tipo TRÁILER en español para videos POV. "
            "La descripción debe contar, en pocas líneas, qué tipo de vida/historia va a vivir el espectador: origen, conflicto principal, ambiente, tono emocional y posibles consecuencias. "
            "Debe leerse como la sinopsis intensa de una película, no como un copy de marketing ni un resumen frío de Wikipedia. "
            "PROHIBIDO usar frases vacías como: 'Sumérgete en...', 'No te lo pierdas', 'Este video te llevará...', 'vivirás la adrenalina...'. "
            "En su lugar, describe directamente la situación: qué tipo de persona es, en qué mundo se mueve, qué decisiones extremas enfrenta y qué está en juego. "
            "Siempre en ESPAÑOL NEUTRO, sin emojis, sin hashtags, sin listas y sin dirigirte al espectador con 'suscríbete' o similares."
        )
        user_prompt = (
            f"Título del video: {titulo}\n\n"
            "Escribí una descripción tipo tráiler, rica y desarrollada: varios párrafos o líneas separadas (no todo en un solo renglón). "
            "Debe dejar claro que el video es un POV en segunda persona donde el espectador vive la vida COMPLETA del personaje del título: infancia, ascenso, momentos de gloria, caídas y consecuencias finales. "
            "Incluí detalles del entorno (época, lugar, mundo en el que se mueve), del tipo de conflictos que va a enfrentar (familia, dinero, poder, culpa, cárcel, soledad, etc.) y del tono general (crudo, tenso, esperanzador, trágico, etc.). "
            "No invites a 'ver el video' ni escribas llamados a la acción; solo cuenta, como si fuera la contraportada de una película muy intensa, qué clase de viaje va a vivir el espectador. "
            "Podés usar 2 o 3 párrafos cortos si ayuda a dar ritmo y claridad."
        )

        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=700,
            temperature=0.6,
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


def preparar_imagenes_para_revision(
    tema: str,
    nombre_proyecto: str | None,
    target_words: int,
    min_words: int | None,
    max_words: int | None,
    plantilla: str,
    segundos_por_imagen: float,
    width: int,
    height: int,
    on_progress_imagenes=None,
) -> tuple[str, Path, list[Path]]:
    """
    Genera guion, escenas, prompts e IMÁGENES, pero no voz ni video.
    Devuelve (nombre_proyecto_sanitizado, ruta_guion, lista_imagenes).
    """
    from src.script_generator import count_words  # import local para evitar ciclos raros

    seg_por_img = segundos_por_imagen or 5.0

    guion_texto, word_count, estimated_minutes = generar_guion(
        tema,
        target_words=target_words,
        min_words=min_words,
        max_words=max_words,
        plantilla=plantilla,
        segundos_por_imagen=seg_por_img,
    )
    proy = nombre_proyecto or tema[:30].replace(" ", "_")
    proy = sanitizar_nombre_proyecto(proy)
    guardar_guion(guion_texto, proy)
    guion_path = BASE / "output" / "guiones" / f"{proy}.txt"

    escenas = dividir_en_escenas(guion_texto, segundos_por_imagen=seg_por_img)
    tema_para_desc = tema or proy

    # Usar beats visuales también en modo revisión (misma lógica que pipeline.run)
    beats = generar_beats_para_escenas(escenas, tema=tema_para_desc)
    guardar_beats(beats, proy)
    beats_con_prompts = prompts_para_beats(beats)
    escenas_con_prompts: list[tuple[Escena, str, str | None]] = [
        (
            Escena(
                numero=beat.beat_id,
                texto=beat.original_text,
                duracion_segundos=seg_por_img,
            ),
            prompt,
            emotion_to_expression_key(beat.emotion),
        )
        for beat, prompt in beats_con_prompts
    ]
    guardar_prompts_por_escena(escenas_con_prompts, proy)

    # Generar imágenes (igual que pipeline.run, pero solo esta fase)
    n_imgs = len(escenas_con_prompts)
    print(f"🖼️ [Revisión] Generando {n_imgs} imágenes (puede tardar varios minutos)...")
    lista_imagenes = generar_lote(
        escenas_con_prompts,
        subcarpeta=proy,
        width=width,
        height=height,
        on_progress=on_progress_imagenes,
    )
    print(f"✅ [Revisión] Imágenes generadas: {len(lista_imagenes)}")

    # Info básica por si hace falta mostrar algo antes del video
    texto_narracion = " ".join(e.texto for e in escenas)
    palabras_narracion = len(texto_narracion.split())
    info_dict = {
        "word_count": word_count or count_words(guion_texto),
        "estimated_minutes": estimated_minutes,
        "palabras_narracion": palabras_narracion,
        "target_words": target_words,
    }
    # Guardar info mínima en session_state
    st.session_state.word_count = info_dict["word_count"]
    st.session_state.estimated_minutes = info_dict["estimated_minutes"]
    st.session_state.target_words = info_dict["target_words"]

    return proy, guion_path, lista_imagenes


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
st.markdown('<p class="tagline">Generá el video completo automáticamente.</p>', unsafe_allow_html=True)

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

# Si hay un título sugerido pendiente, aplicarlo ANTES de instanciar el widget
if "_titulo_sugerido_val" in st.session_state:
    st.session_state.titulo_todo = st.session_state._titulo_sugerido_val
    del st.session_state._titulo_sugerido_val

col_t1, col_t2 = st.columns([3, 1])
with col_t1:
    titulo_video = st.text_input(
        "Título del video",
        placeholder="Ej: La historia de la inteligencia artificial en 2 minutos",
        key="titulo_todo",
    )
with col_t2:
    st.caption("Podés pedir títulos sugeridos con IA.")
    if st.button("Sugerir títulos con IA", key="btn_sugerir_titulo"):
        # Usar el tema si ya existe (título + descripción) como contexto; si no, IA inventa ideas POV
        contexto_tema = (titulo_video or "").strip()
        desc_actual = (st.session_state.get("descripcion_breve_text") or "").strip()
        if desc_actual:
            contexto_tema = f"{contexto_tema}. {desc_actual}" if contexto_tema else desc_actual
        titulos = sugerir_titulos_virales(
            tema=contexto_tema,
            guion_resumen="",
            notas_creador="Títulos tipo POV que puedan ser virales.",
            titulo_actual=titulo_video or "",
        )
        if titulos:
            # Mostrar en un selectbox emergente usando session_state
            st.session_state._titulos_sugeridos = titulos
        else:
            st.warning("No se pudieron generar títulos. Revisá tu OPENAI_API_KEY.")

if "_titulos_sugeridos" in st.session_state:
    st.markdown("**Títulos sugeridos:**")
    elegido = st.radio(
        "Elegí uno o úsalo como inspiración",
        options=st.session_state._titulos_sugeridos,
        index=0,
        key="titulo_sugerido_radio",
    )
    col_apply1, col_apply2 = st.columns(2)
    with col_apply1:
        if st.button("Usar este título", key="btn_usar_titulo_sugerido"):
            st.session_state._titulo_sugerido_val = elegido
            del st.session_state._titulos_sugeridos
            st.rerun()
    with col_apply2:
        if st.button("Descartar sugerencias", key="btn_descartar_titulos_sugeridos"):
            del st.session_state._titulos_sugeridos

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
        max_value=5000,
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
            max_value=5000,
            value=int(target_words * 0.8),
            step=10,
            help="Mínimo de palabras aceptable (por defecto 80% del objetivo)",
            key="min_words_todo"
        )
        max_words = st.number_input(
            "Máx palabras",
            min_value=80,
            max_value=5000,
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
        # Solo Replicate (FLUX) como backend principal.
        if not _replicate_disponible():
            st.error("Falta REPLICATE_API_TOKEN en .env. Configurá ese token para generar imágenes con FLUX.")
        imagen_backend = "Replicate (FLUX, ~$0.003/imagen)"
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
        # Si se salta la generación de imágenes, el backend es irrelevante.
        imagen_backend = "sin_imagenes"
        segundos_por_imagen = 5.0

    # Subtítulos (especialmente útiles para Shorts/Reels/TikTok)
    estilos_sub = get_subtitle_styles()
    nombres_estilos = list(estilos_sub.keys()) if estilos_sub else []
    es_vertical = formato_video != "YouTube (16:9) - 1920x1080"
    usar_subtitulos = st.checkbox(
        "Agregar subtítulos quemados en el video (recomendado para Shorts/Reels/TikTok)",
        value=es_vertical,
        help="Genera un archivo de subtítulos sincronizado por beat y lo quema en el video final.",
        key="usar_subs_todo",
    )
    estilo_subtitulos = None
    if usar_subtitulos and nombres_estilos:
        default_idx = 0
        if es_vertical and "tiktok_karaoke" in nombres_estilos:
            default_idx = nombres_estilos.index("tiktok_karaoke")
        estilo_subtitulos = st.selectbox(
            "Estilo de subtítulo",
            options=nombres_estilos,
            index=default_idx,
            format_func=lambda k: f"{k} – {estilos_sub.get(k, {}).get('description', '')}",
            key="estilo_subs_todo",
        )
    
    skip_miniatura = st.checkbox(
        "Saltar generación de miniatura",
        value=False,
        help="No generar miniatura automáticamente.",
        key="skip_thumb_todo"
    )

    revisar_imagenes_antes_video = st.checkbox(
        "Revisar y aprobar imágenes antes de montar el video",
        value=True,
        help="Si está activo, primero se generan las imágenes y podrás aceptarlas/regenerarlas antes de crear el video final.",
        key="revisar_imagenes_todo",
    )

if not skip_imagenes:
    usar_replicate = _replicate_disponible()
    if usar_replicate:
        st.success("Imágenes con **Replicate FLUX** (~$0.003/imagen). No hace falta ComfyUI.")
    else:
        # Solo si NO hay Replicate disponible, se permite/avisa sobre ComfyUI como opción legacy.
        comfy_ok = _comfyui_disponible()
        if comfy_ok:
            donde = "remoto (RunPod/nube)" if comfyui_es_remoto() else "local"
            st.success(f"ComfyUI: disponible ({donde}). Las imágenes se generarían con ComfyUI — {COMFY_URL}")
        else:
            st.warning(
                "ComfyUI no está corriendo. Iniciá ComfyUI en el puerto 8188 (local o RunPod) o configurá REPLICATE_API_TOKEN en .env para usar FLUX."
            )
            if st.button("▶️ Iniciar ComfyUI en segundo plano", key="btn_iniciar_comfy"):
                ok, err = iniciar_comfyui_background()
                if ok:
                    st.success("ComfyUI se está iniciando. Esperá 30–60 segundos y recargá la página (F5). Si no aparece, abrí el log abajo o ejecutá en terminal: bash scripts/start_comfyui.sh")
                else:
                    st.error(f"No se pudo iniciar ComfyUI: {err}. Verificá que tengas ComfyUI instalado y, si está en otra ruta, definí COMFYUI_PATH en .env.")

col1, col2 = st.columns([1, 2])
with col1:
    generar = st.button("Generar video completo", type="primary", key="btn_generar_todo")

if generar:
    bloqueado = False
    # Limpiar el video anterior para que no siga viéndose en pantalla mientras se genera el nuevo
    clear_result()
    if not tema or not tema.strip():
        st.error("Escribí un tema o idea.")
        bloqueado = True
    elif faltan:
        st.error("Completá las credenciales en .env y volvé a intentar.")
    elif not skip_imagenes and not usar_replicate and not _replicate_disponible() and not _comfyui_disponible():
        # Solo bloquear si NO hay Replicate y TAMPOCO ComfyUI disponible.
        st.error("No hay backend de imágenes disponible. Configurá REPLICATE_API_TOKEN en .env o levantá ComfyUI en el puerto 8188.")
    else:
        revisar_imagenes_antes_video = st.session_state.get("revisar_imagenes_todo", False)
        # Barra de progreso para imágenes (así se ve que avanza y no está trancado)
        progress_bar = st.progress(0) if not skip_imagenes else None
        progress_status = st.empty() if not skip_imagenes else None

        def on_progress_imagenes(current: int, total: int):
            if progress_bar is not None:
                progress_bar.progress(current / total if total else 0)
            if progress_status is not None:
                progress_status.caption(f"Generando imagen **{current}** de **{total}**… (cada una puede tardar 20–60 s)")

        if not skip_imagenes and revisar_imagenes_antes_video:
            mensaje_spinner = "Generando… guion → escenas → imágenes para revisión"
            with st.spinner(mensaje_spinner):
                try:
                    os.environ["USE_OPENAI_IMAGES"] = "false"
                    os.environ["IMAGE_BACKEND"] = "replicate" if (st.session_state.get("imagen_backend_todo") == "Replicate (FLUX, ~$0.003/imagen)") else "comfyui"
                    proy, guion_path, lista_imagenes = preparar_imagenes_para_revision(
                        tema=tema.strip(),
                        nombre_proyecto=(nombre_proyecto or "").strip() or None,
                        target_words=target_words,
                        min_words=min_words,
                        max_words=max_words,
                        plantilla="explicativo",
                        segundos_por_imagen=segundos_por_imagen,
                        width=video_width,
                        height=video_height,
                        on_progress_imagenes=on_progress_imagenes,
                    )
                    st.session_state.modo_revision_imagenes = True
                    st.session_state.proyecto_revision = proy
                    st.session_state.guion_path_revision = str(guion_path)
                    st.success("Imágenes generadas. Revisá cada una en **🎞️ Escenas por imagen** (abajo) y aceptá o regenerá antes de montar el video.")
                except Exception as e:
                    st.exception(e)
        else:
            mensaje_spinner = "Generando… guion → escenas"
            if not skip_imagenes:
                mensaje_spinner += " → imágenes"
            mensaje_spinner += " → voz → video → metadata YouTube"
            with st.spinner(mensaje_spinner):
                try:
                    os.environ["USE_OPENAI_IMAGES"] = "false"
                    os.environ["IMAGE_BACKEND"] = "replicate" if (st.session_state.get("imagen_backend_todo") == "Replicate (FLUX, ~$0.003/imagen)") else "comfyui"
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
                        usar_subtitulos=usar_subtitulos,
                        estilo_subtitulos=estilo_subtitulos,
                    )
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

# ─── Resultado: video + metadata O imágenes para revisión ─────────────────────
tiene_video = bool(st.session_state.video_path and st.session_state.video_bytes)
es_revision_imagenes = bool(
    st.session_state.get("modo_revision_imagenes") and st.session_state.get("proyecto_revision")
)

if tiene_video:
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
    
    # Video (solo si ya hay video generado)
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

if es_revision_imagenes and not tiene_video:
    st.success("Imágenes generadas para revisión. Revisá cada una en la pestaña **🎞️ Escenas por imagen**, aceptá o regenerá las que quieras, y cuando todas estén aceptadas usá **Generar video con imágenes aceptadas**.")

if tiene_video or es_revision_imagenes:
    # Archivos generados - Tabs (Guion, Escenas por imagen con Aceptar/Regenerar, etc.)
    st.subheader("📁 Archivos generados" if tiene_video else "📁 Revisar imágenes")
    tabs_archivos = st.tabs(["📝 Guion", "🎞️ Escenas por imagen", "🖼️ Miniatura", "📄 Metadata YouTube", "📂 Todos los archivos"])
    
    with tabs_archivos[0]:  # Guion
        guion_texto = st.session_state.get("guion_completo")
        if not guion_texto and es_revision_imagenes:
            guion_path_rev = st.session_state.get("guion_path_revision")
            if guion_path_rev and Path(guion_path_rev).exists():
                guion_texto = Path(guion_path_rev).read_text(encoding="utf-8")
        nombre_proy_guion = (st.session_state.video_name or "").replace(".mp4", "") if tiene_video else sanitizar_nombre_proyecto(st.session_state.get("proyecto_revision", ""))
        if guion_texto:
            st.markdown("**Guion completo generado:**")
            st.text_area(
                "Guion",
                value=guion_texto,
                height=400,
                key="guion_completo_display",
                label_visibility="collapsed"
            )
            st.download_button(
                "📥 Descargar guion completo (.txt)",
                data=guion_texto,
                file_name=f"{nombre_proy_guion}_guion.txt",
                mime="text/plain",
                key="dl_guion_completo"
            )
            guion_path = BASE / "output" / "guiones" / f"{nombre_proy_guion}.txt"
            if guion_path.exists():
                st.caption(f"💾 Guardado en: `{guion_path.relative_to(BASE)}`")
        else:
            st.info("El guion no está disponible en la sesión actual.")
    
    with tabs_archivos[1]:  # Escenas por imagen
        modo_revision = st.session_state.get("modo_revision_imagenes", False)
        if modo_revision and st.session_state.get("proyecto_revision"):
            nombre_proy_sanit_escenas = sanitizar_nombre_proyecto(st.session_state.proyecto_revision)
        else:
            nombre_proy_escenas = st.session_state.video_name.replace('.mp4', '')
            nombre_proy_sanit_escenas = sanitizar_nombre_proyecto(nombre_proy_escenas)
        imagenes_dir_escenas = BASE / "output" / "imagenes" / nombre_proy_sanit_escenas
        try:
            from src.regeneration import cargar_prompts, regenerar_escenas
            escenas_con_prompts = cargar_prompts(nombre_proy_sanit_escenas)
        except Exception:
            escenas_con_prompts = []
        if escenas_con_prompts and imagenes_dir_escenas.exists():
            st.markdown("**Escena del guion usada para cada imagen:**")
            if modo_revision:
                st.caption("Revisá cada imagen antes de montar el video. Podés regenerar escenas individuales.")
                total = len(escenas_con_prompts)
                aceptadas = 0
                for item in escenas_con_prompts:
                    escena = item[0]
                    key_estado = f"estado_escena_{nombre_proy_sanit_escenas}_{escena.numero}"
                    if st.session_state.get(key_estado) == "aceptada":
                        aceptadas += 1
                st.caption(f"Escenas aceptadas: **{aceptadas} / {total}**")
                if st.button("✅ Aceptar todas las imágenes", key="btn_aceptar_todas"):
                    for item in escenas_con_prompts:
                        escena = item[0]
                        st.session_state[f"estado_escena_{nombre_proy_sanit_escenas}_{escena.numero}"] = "aceptada"
                    st.rerun()
                if st.button("🎬 Generar video con imágenes aceptadas", key="btn_video_desde_revision"):
                    if aceptadas < total:
                        st.error("Aceptá todas las escenas antes de generar el video.")
                    else:
                        clear_result()
                        try:
                            from src.pipeline import run as run_pipeline
                            guion_path = Path(st.session_state.get("guion_path_revision", ""))
                            if not guion_path.exists():
                                st.error("No se encontró el guion para este proyecto. Volvé a generar las imágenes.")
                            else:
                                video_path, metadata_path, thumbnail_path, info_dict = run_pipeline(
                                    tema=None,
                                    guion_path=guion_path,
                                    target_words=st.session_state.get("target_words_todo", 280),
                                    min_words=st.session_state.get("min_words_todo"),
                                    max_words=st.session_state.get("max_words_todo"),
                                    plantilla="explicativo",
                                    nombre_proyecto=st.session_state.get("proyecto_revision"),
                                    skip_imagenes=True,
                                    skip_voz=False,
                                    musica_fondo=None,
                                    generar_metadata=True,
                                    velocidad_voz=st.session_state.get("velocidad_voz_todo", 1.2),
                                    segundos_por_imagen=st.session_state.get("seg_por_img_todo", 5.0),
                                    width=video_width,
                                    height=video_height,
                                    skip_miniatura=st.session_state.get("skip_thumb_todo", False),
                                )
                                clear_result()
                                st.session_state.video_path = video_path
                                st.session_state.video_bytes = video_path.read_bytes()
                                st.session_state.video_name = video_path.name
                                st.session_state.modo_revision_imagenes = False
                                st.success("Video generado con las imágenes aprobadas.")
                                st.rerun()
                        except Exception as e:
                            st.exception(e)
            else:
                st.caption("Cada imagen del video se generó a partir del texto de la escena (y su descripción visual).")
            for item in escenas_con_prompts:
                escena, prompt = item[0], item[1]
                img_path = imagenes_dir_escenas / f"escena_{escena.numero:04d}.png"
                with st.expander(f"Escena {escena.numero} — {escena.duracion_segundos:.0f}s", expanded=(escena.numero <= 3)):
                    if img_path.exists():
                        st.image(str(img_path), caption=f"Imagen escena {escena.numero}", width="stretch")
                    else:
                        st.caption(f"🖼️ Imagen no encontrada: `{img_path.name}`")
                    if modo_revision:
                        estado_key = f"estado_escena_{nombre_proy_sanit_escenas}_{escena.numero}"
                        estado_actual = st.session_state.get(estado_key, "pendiente")
                        st.caption(f"Estado: **{estado_actual}**")
                        feedback_key = f"feedback_regen_{nombre_proy_sanit_escenas}_{escena.numero}"
                        st.markdown("**1. Escribí qué no te gusta (antes de regenerar):**")
                        st.text_input(
                            "La nueva imagen se generará usando esta corrección",
                            placeholder="Ej: más oscuro, menos personajes, otro ángulo, que se vea más el rostro…",
                            key=feedback_key,
                            label_visibility="collapsed",
                            help="Primero escribí acá tu corrección. Cuando toques Regenerar, la próxima imagen ya incluirá lo que pediste.",
                        )
                        st.caption("La IA usa tu texto para mejorar el prompt; así la nueva imagen ya incorpora lo que querés.")
                        cols_btn = st.columns([1, 1])
                        with cols_btn[0]:
                            if st.button("✅ Aceptar", key=f"aceptar_escena_{nombre_proy_sanit_escenas}_{escena.numero}"):
                                st.session_state[estado_key] = "aceptada"
                                st.rerun()
                        with cols_btn[1]:
                            if st.button("♻️ Regenerar", key=f"regen_escena_{nombre_proy_sanit_escenas}_{escena.numero}"):
                                feedback_text = (st.session_state.get(feedback_key) or "").strip()
                                if not feedback_text:
                                    st.warning("Escribí arriba qué no te gusta o qué querés cambiar. La nueva imagen se generará usando esa corrección.")
                                else:
                                    try:
                                        regenerar_escenas(
                                            [escena.numero],
                                            proyecto=nombre_proy_sanit_escenas,
                                            carpeta_imagenes=nombre_proy_sanit_escenas,
                                            feedback_por_escena={escena.numero: feedback_text},
                                        )
                                        st.session_state[estado_key] = "pendiente"
                                        st.success("Imagen regenerada con tu corrección.")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"No se pudo regenerar la escena {escena.numero}: {e}")
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
            st.image(st.session_state.thumbnail_bytes, caption="Miniatura del video", width="stretch")
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
        if st.session_state.get("metadata_text"):
            st.markdown("**Metadata para YouTube (descripción y capítulos):**")
            st.text_area(
                "Descripción y capítulos",
                value=st.session_state.metadata_text,
                height=400,
                key="meta_display",
                label_visibility="collapsed",
                help="Copiá este texto y pegalo en la descripción de YouTube"
            )
            meta_path = st.session_state.get("metadata_path")
            st.download_button(
                "📥 Descargar metadata (.txt)",
                data=st.session_state.metadata_text,
                file_name=(Path(meta_path).name if meta_path else "youtube_metadata.txt"),
                mime="text/plain",
                key="dl_meta",
            )
            if meta_path:
                st.caption(f"💾 Guardado en: `{Path(meta_path).relative_to(BASE)}`")
        else:
            st.info("No se generó metadata para este video.")
    
    with tabs_archivos[4]:  # Todos los archivos
        st.markdown("**Ubicación de todos los archivos generados:**")
        
        nombre_proy_todos = (st.session_state.video_name or "").replace(".mp4", "") or sanitizar_nombre_proyecto(st.session_state.get("proyecto_revision", ""))
        nombre_proy_sanitizado = sanitizar_nombre_proyecto(nombre_proy_todos) if nombre_proy_todos else ""
        
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
        meta_path_lista = st.session_state.get("metadata_path")
        if meta_path_lista:
            archivos_info.append(("📄 Metadata", Path(meta_path_lista).relative_to(BASE), "TXT"))
        
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
    tab_guion, tab_titulo, tab_descripcion, tab_miniatura, tab_imagenes = st.tabs(["📝 Guion", "🏷️ Título", "📄 Descripción YouTube", "🖼️ Miniatura", "🎨 Imágenes"])
    
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
    
    with tab_titulo:
        st.markdown("#### Instrucciones para generar TÍTULOS")
        instrucciones_titulo = get_instrucciones_titulo()
        titulo_system = st.text_area("Prompt del sistema", value=instrucciones_titulo.get("system_prompt", ""), height=200, key="edit_title_system")
        titulo_user = st.text_area("Template (usa {tema}, {guion_resumen}, {notas_creador})", value=instrucciones_titulo.get("user_prompt_template", ""), height=200, key="edit_title_user")
        if st.button("💾 Guardar instrucciones de título", key="save_title"):
            try:
                instrucciones_titulo["system_prompt"] = titulo_system
                instrucciones_titulo["user_prompt_template"] = titulo_user
                with open(BASE / "config" / "instrucciones_titulo.yaml", "w", encoding="utf-8") as f:
                    yaml.dump(instrucciones_titulo, f, allow_unicode=True, default_flow_style=False)
                st.success("✅ Instrucciones de título guardadas")
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
with st.expander("Modo avanzado (paso a paso: Guion → Escenas/Beats → Voz → Video)"):
    from src.script_generator import generar_guion, guardar_guion
    from src.scene_splitter import dividir_en_escenas, escenas_a_texto_continuo, Escena as EscenaMA
    from src.visual_beats import generar_beats_para_escenas, guardar_beats
    from src.prompt_builder import prompts_para_beats
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
            tw = st.number_input("Palabras objetivo", 80, 5000, 280, 10, key="ma_target_words")
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
        st.caption("Dividir guion en escenas y beats visuales (~5 s cada una).")
        txt = st.text_area("Guion", value=st.session_state.get("guion_texto", ""), height=160, key="ma_escenas_txt")
        if st.button("Dividir en escenas", key="ma_dividir") and txt:
            st.session_state.guion_texto = txt.strip()
            st.rerun()
        if st.session_state.get("guion_texto"):
            escenas = dividir_en_escenas(st.session_state.guion_texto)
            beats_prev = generar_beats_para_escenas(escenas, tema=st.session_state.get("ma_tema") or "")
            st.markdown(f"**Escenas:** {len(escenas)}  |  **Beats visuales:** {len(beats_prev)}")
            for e in escenas:
                st.markdown(f"**Escena #{e.numero}** ({e.duracion_segundos:.0f}s) {e.texto[:80]}…")

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
                # Usar el mismo sistema de beats que el pipeline principal
                beats = generar_beats_para_escenas(escenas, tema=tema_ctx)
                guardar_beats(beats, nombre)
                beats_con_prompts = prompts_para_beats(beats)
                escenas_con_prompts: list[tuple[EscenaMA, str, str | None]] = [
                    (
                        EscenaMA(
                            numero=beat.beat_id,
                            texto=beat.original_text,
                            duracion_segundos=5.0,
                        ),
                        prompt,
                        emotion_to_expression_key(beat.emotion),
                    )
                    for beat, prompt in beats_con_prompts
                ]
                guardar_prompts_por_escena(escenas_con_prompts, nombre)
                # Limpiar imágenes viejas de este proyecto; una por beat
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
