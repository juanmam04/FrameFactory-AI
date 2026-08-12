"""FASE 11: Script maestro – ejecuta todo el pipeline con un solo comando."""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from .config_loader import BASE, get_subtitle_styles, get_visual_bible

try:
    from .config_loader import get_background_music_path
except ImportError:
    def get_background_music_path():
        return None
from .script_generator import generar_guion, guardar_guion, count_words
from .scene_splitter import dividir_en_escenas, escenas_a_texto_continuo, Escena
from .prompt_builder import get_outfit_key_for_beat
from .image_generator import OUTPUT_IMAGES
from .voice_generator import generar_voz
from .video_assembler import montar_video
from .regeneration import guardar_prompts_por_escena
from .metadata_youtube import generar_metadata_completa
from .history import guardar_en_historial
from .visual_beats import generar_beats_para_escenas, guardar_beats, generar_subtitulos_srt
from .frame_director import beats_a_frame_specs
from .frame_prompt_builder import prompt_desde_frame_spec
from .frame_spec import guardar_frame_specs
from .frame_image_pipeline import generar_imagenes_desde_frame_specs
from .catalog_service import (
    VOICES,
    ensure_catalog_dirs,
    ensure_default_catalog_assets,
    materialize_background_image,
    resolve_background_id,
    resolve_character_id,
    resolve_saas_character_image_path,
    resolve_voice_id,
)
from .gameplay_background_service import probe_media_duration_seconds, render_gameplay_block_clip
from .image_generator import generar_imagen_apoyo_replicate
from .scene_planner import plan_scenes, plan_scenes_reddit_segments
from .reddit_story_mode import is_reddit_story_profile, words_per_reddit_segment
from .scene_visual_intent import enrich_blocks_with_visual_intent
from .reddit_publication_bundle import generar_bundle_publicacion_youtube
from .character_video_provider import render_block, reset_heygen_runtime_state
from .saas_creative_profile import merge_profile_disk, profile_to_script_context
from .saas_edit_planner import annotate_blocks_with_editing
from .saas_full_package import write_saas_full_package
from .saas_subtitles import burn_subtitles_on_video, list_subtitle_style_keys, write_ass_from_block_audios
from .saas_viral_idea_engine import generate_viral_idea_for_profile, generate_viral_story_idea_three_pick_best


def _recortar_audio_por_duracion(audio_path: Path, duracion_max_segundos: float) -> Path:
    """Recorta el audio para que no exceda la duración máxima usando FFmpeg."""
    import subprocess
    import shutil
    
    if not shutil.which("ffmpeg"):
        return audio_path
    
    try:
        # Crear archivo temporal
        audio_recortado = audio_path.parent / f"{audio_path.stem}_recortado{audio_path.suffix}"
        
        cmd = [
            "ffmpeg", "-y", "-i", str(audio_path),
            "-t", str(duracion_max_segundos),  # Limitar duración
            "-c", "copy",  # Copiar sin re-encodear si es posible
            str(audio_recortado),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        
        # Reemplazar el archivo original
        if audio_recortado.exists():
            audio_path.unlink()
            audio_recortado.rename(audio_path)
        
        return audio_path
    except Exception as e:
        print(f"⚠️ Error al recortar audio: {e}, usando audio original")
        return audio_path


def sanitizar_nombre_proyecto(nombre: str) -> str:
    """
    Sanitiza el nombre del proyecto eliminando caracteres inválidos para Windows.
    Caracteres inválidos: < > : " | ? * \\ /
    """
    # Caracteres inválidos en Windows (y / para rutas seguras en cualquier SO)
    caracteres_invalidos = r'[<>:"|?*\\/]'
    # Reemplazar caracteres inválidos con guión bajo
    nombre_limpio = re.sub(caracteres_invalidos, '_', nombre)
    # Reemplazar espacios múltiples con uno solo
    nombre_limpio = re.sub(r'\s+', '_', nombre_limpio)
    # Eliminar guiones bajos múltiples
    nombre_limpio = re.sub(r'_+', '_', nombre_limpio)
    # Eliminar guiones bajos al inicio y final
    nombre_limpio = nombre_limpio.strip('_')
    # Limitar longitud y asegurar que no esté vacío
    if not nombre_limpio:
        nombre_limpio = "proyecto"
    return nombre_limpio[:50]  # Limitar a 50 caracteres


def run(
    tema: str | None = None,
    guion_path: Path | None = None,
    target_words: int | None = None,
    min_words: int | None = None,
    max_words: int | None = None,
    plantilla: str = "explicativo",
    nombre_proyecto: str | None = None,
    skip_imagenes: bool = False,
    skip_voz: bool = False,
    musica_fondo: Path | None = None,
    generar_metadata: bool = True,
    velocidad_voz: float = 1.0,
    segundos_por_imagen: float | None = None,
    width: int = 1920,
    height: int = 1080,
    skip_miniatura: bool = False,
    on_progress_imagenes=None,  # callable(current_1based, total) para UI (ej. "Escena 5 de 25")
    usar_subtitulos: bool = False,
    estilo_subtitulos: str | None = None,
    # Parámetros legacy (deprecated, usar target_words)
    duracion_min: int | None = None,
    duracion_max: int | None = None,
) -> tuple[Path, Path | None, Path | None, dict]:
    """
    Pipeline completo:
    Entrada: tema (para generar guion) o ruta a guion existente.
    Salida: (video_path, metadata_path, thumbnail_path, info_dict)
    - info_dict contiene: word_count, estimated_minutes, frame_metrics (si se generaron imágenes)
    """
    # Compatibilidad con parámetros legacy: convertir duración a palabras
    if target_words is None:
        if duracion_min is not None:
            # Convertir minutos a palabras objetivo (140 palabras por minuto)
            words_per_minute = 140
            target_words = int(duracion_min * words_per_minute)
            if duracion_max is not None and duracion_max != duracion_min:
                max_words = int(duracion_max * words_per_minute)
        else:
            # Default: 280 palabras (2 minutos)
            target_words = 280
    
    if target_words < 80:
        target_words = 80
    if target_words > 5000:
        target_words = 5000
    
    # Obtener segundos por imagen
    seg_por_img = segundos_por_imagen or 5.0
    
    attempts_per_frame = int(os.getenv("ATTEMPTS_PER_FRAME", "4"))
    if attempts_per_frame < 1:
        attempts_per_frame = 1
    word_count = 0
    estimated_minutes = 0.0
    
    if tema:
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
    elif guion_path and guion_path.exists():
        guion_texto = guion_path.read_text(encoding="utf-8")
        word_count = count_words(guion_texto)
        estimated_minutes = word_count / 140.0
        proy = nombre_proyecto or guion_path.stem
        proy = sanitizar_nombre_proyecto(proy)
    else:
        raise ValueError("Indica --tema o --guion con un archivo existente.")

    escenas = dividir_en_escenas(guion_texto, segundos_por_imagen=seg_por_img)

    # ─── NUEVO: beats visuales cinematográficos ────────────────────────────────
    tema_para_desc = tema if tema else (nombre_proyecto or proy or "")
    # Calcular un máximo razonable de beats según duración estimada y densidad configurada
    max_beats_total: int | None = None
    try:
        vb = get_visual_bible()
        dens = vb.get("densidad_imagenes") or {}
        shorts_min, shorts_max = dens.get("shorts_30_60_seg", [30, 60])
        v10_min, v10_max = dens.get("video_10_min", [120, 160])
        v20_min, v20_max = dens.get("video_20_min", [200, 260])
        v40_min, v40_max = dens.get("video_40_min", [350, 450])
        # Categorizar por duración estimada del guion
        if estimated_minutes <= 1.0:
            rango_min, rango_max = shorts_min, shorts_max
        elif estimated_minutes <= 12.0:
            rango_min, rango_max = v10_min, v10_max
        elif estimated_minutes <= 24.0:
            rango_min, rango_max = v20_min, v20_max
        else:
            rango_min, rango_max = v40_min, v40_max
        # Estimar número de imágenes según duración y segundos por imagen
        if estimated_minutes > 0:
            estimado_imgs = int((estimated_minutes * 60.0) / seg_por_img)
            max_beats_total = max(rango_min, min(estimado_imgs, rango_max))
    except Exception as e:
        print(f"⚠️ No se pudo calcular densidad de beats desde visual_bible.yaml: {e}")
        max_beats_total = None

    beats = generar_beats_para_escenas(escenas, tema=tema_para_desc, max_beats_total=max_beats_total)
    guardar_beats(beats, proy)
    # V2: beat -> FrameSpec -> prompt; prompts JSON sigue llevando outfit/seed por compatibilidad con la UI
    frame_specs = beats_a_frame_specs(beats)
    guardar_frame_specs(frame_specs, proy)

    escenas_con_prompts: list[tuple[Escena, str, str | None, str, str]] = [
        (
            Escena(
                numero=spec.frame_id,
                texto=spec.story_step or spec.action,
                duracion_segundos=seg_por_img,
            ),
            prompt_desde_frame_spec(spec),
            spec.expression_key,
            get_outfit_key_for_beat(beat),
            "",
        )
        for spec, beat in zip(frame_specs, beats, strict=True)
    ]
    guardar_prompts_por_escena(escenas_con_prompts, proy)

    lista_imagenes: list[Path] = []
    frame_metrics: list[dict] = []
    if not skip_imagenes:
        lista_imagenes, frame_metrics, frame_specs = generar_imagenes_desde_frame_specs(
            frame_specs,
            proy,
            width=width,
            height=height,
            attempts_per_frame=attempts_per_frame,
            on_progress_imagenes=on_progress_imagenes,
        )
    else:
        lista_imagenes = sorted((OUTPUT_IMAGES / proy).glob("escena_*.png"))

    texto_narracion = escenas_a_texto_continuo(escenas)
    
    # Verificar que el texto de narración no esté vacío o cortado
    if not texto_narracion or len(texto_narracion.strip()) < 50:
        print(f"⚠️ ADVERTENCIA: Texto de narración muy corto ({len(texto_narracion)} caracteres)")
        print(f"   Guion original: {len(guion_texto)} caracteres")
        print(f"   Número de escenas: {len(escenas)}")
        print(f"   Primeros 200 caracteres del guion: {guion_texto[:200]}")
        print(f"   Últimos 200 caracteres del guion: {guion_texto[-200:]}")
    
    # Verificar que el texto de narración coincida con el guion
    palabras_narracion = len(texto_narracion.split())
    palabras_guion = len(guion_texto.split())
    
    print(f"📊 Comparación de texto:")
    print(f"   Guion original: {palabras_guion} palabras, {len(guion_texto)} caracteres")
    print(f"   Texto narración: {palabras_narracion} palabras, {len(texto_narracion)} caracteres")
    
    if abs(palabras_narracion - word_count) > 50:
        print(f"⚠️ ADVERTENCIA: Diferencia grande entre palabras del guion ({word_count}) y narración ({palabras_narracion})")
    
    if abs(palabras_narracion - palabras_guion) > 50:
        print(f"⚠️ ADVERTENCIA CRÍTICA: El texto de narración tiene {palabras_narracion} palabras pero el guion tiene {palabras_guion} palabras")
        print(f"   Esto significa que parte del guion NO se está usando para generar el audio")
        print(f"   Verificando escenas...")
        for i, escena in enumerate(escenas):
            print(f"   Escena {escena.numero}: {len(escena.texto)} caracteres, {len(escena.texto.split())} palabras")
            print(f"      Texto: {escena.texto[:100]}...")
    
    audio_path = None
    duracion_audio_segundos = None
    if not skip_voz:
        print(f"🔊 Generando voz con {len(texto_narracion)} caracteres, {palabras_narracion} palabras estimadas")
        audio_path = generar_voz(texto_narracion, nombre_archivo=proy, velocidad=velocidad_voz)
        if audio_path.exists() and audio_path.stat().st_size > 0:
            # Obtener duración real del audio
            import subprocess
            import shutil
            if shutil.which("ffprobe"):
                try:
                    cmd_probe = [
                        "ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)
                    ]
                    result = subprocess.run(cmd_probe, capture_output=True, text=True, check=True)
                    duracion_audio_segundos = float(result.stdout.strip())
                    duracion_audio_min = duracion_audio_segundos / 60.0
                    print(f"🔊 Duración real del audio: {duracion_audio_segundos:.1f} segundos ({duracion_audio_min:.1f} minutos)")
                    
                    # Comparar con estimado
                    estimated_audio_min = palabras_narracion / 140.0 / velocidad_voz
                    diferencia_audio = duracion_audio_min - estimated_audio_min
                    print(f"   📊 Comparación:")
                    print(f"      Estimado: {estimated_audio_min:.1f} min ({estimated_audio_min*60:.0f}s)")
                    print(f"      Real: {duracion_audio_min:.1f} min ({duracion_audio_segundos:.0f}s)")
                    print(f"      Diferencia: {diferencia_audio:+.1f} min ({diferencia_audio*60:+.0f}s)")
                    
                    if abs(diferencia_audio) > 1.0:
                        print(f"   ⚠️ ADVERTENCIA: Gran diferencia entre audio estimado y real")
                        print(f"      Posibles causas:")
                        print(f"      - El TTS habla más rápido/lento que 140 palabras/min")
                        print(f"      - El texto se cortó al generar el audio")
                        print(f"      - Problemas con la velocidad aplicada")
                except Exception as e:
                    print(f"⚠️ No se pudo obtener duración del audio: {e}")
            # NO recortar audio - el guion debe ser del tamaño correcto
            # Solo validar duración del audio
            if tema and duracion_max is not None:
                import subprocess
                import shutil
                if shutil.which("ffprobe"):
                    try:
                        cmd_probe = [
                            "ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)
                        ]
                        result = subprocess.run(cmd_probe, capture_output=True, text=True, check=True)
                        duracion_audio = float(result.stdout.strip())
                        if duracion_audio > (duracion_max * 60 * 1.2):
                            print(f"⚠️ ADVERTENCIA: Audio tiene {duracion_audio:.1f}s, objetivo: {duracion_max * 60:.1f}s. El guion debería haber sido del tamaño correcto.")
                    except Exception:
                        pass
        else:
            audio_path = None

    # Subtítulos opcionales (por ahora 1 beat = 1 subtítulo, sincronizado con imágenes)
    subtitles_path = None
    subtitle_style_force = None
    if usar_subtitulos and beats:
        try:
            subtitles_path = generar_subtitulos_srt(beats, proy, seg_por_img)
            styles = get_subtitle_styles()
            if estilo_subtitulos and isinstance(styles.get(estilo_subtitulos), dict):
                subtitle_style_force = styles[estilo_subtitulos].get("force_style")
            elif isinstance(styles.get("default"), dict):
                subtitle_style_force = styles["default"].get("force_style")
        except Exception as e:
            print(f"⚠️ Error al generar subtítulos: {e}")
            subtitles_path = None
            subtitle_style_force = None

    # Música: parámetro > .env BACKGROUND_MUSIC_PATH
    if musica_fondo is None:
        musica_fondo = get_background_music_path()
    if musica_fondo is not None and not musica_fondo.exists():
        musica_fondo = None

    # NO limitar duración del video - el guion debe ser del tamaño correcto
    print(f"🎬 Montando video con {len(lista_imagenes)} imágenes y audio...")
    video_path = montar_video(
        lista_imagenes=lista_imagenes,
        audio_narracion=audio_path,
        musica_fondo=musica_fondo,
        nombre_salida=proy,
        segundos_por_imagen=segundos_por_imagen,
        width=width,
        height=height,
        duracion_maxima_segundos=None,  # No limitar - confiar en que el guion es del tamaño correcto
        subtitles_path=subtitles_path,
        subtitle_style=subtitle_style_force,
    )

    metadata_path = None
    thumbnail_path = None
    if generar_metadata:
        metadata_path, thumbnail_path = generar_metadata_completa(
            proy, tema or proy, escenas, guion_texto,
            usar_ia_descripcion=True,
            generar_miniatura_flag=not skip_miniatura,  # Llama a generar_miniatura (ahora retorna None; sin DALL-E)
        )
    
    # Obtener duración real del video
    duracion_real_segundos = None
    if video_path.exists():
        import subprocess
        import shutil
        if shutil.which("ffprobe"):
            try:
                cmd_probe = [
                    "ffprobe", "-v", "error", "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)
                ]
                result = subprocess.run(cmd_probe, capture_output=True, text=True, check=True)
                duracion_real_segundos = float(result.stdout.strip())
                print(f"📹 Duración real del video: {duracion_real_segundos:.1f} segundos ({duracion_real_segundos/60:.1f} minutos)")
            except Exception as e:
                print(f"⚠️ No se pudo obtener duración del video: {e}")
    
    # Calcular duración estimada ajustada por velocidad
    estimated_minutes_ajustado = estimated_minutes / velocidad_voz if velocidad_voz > 0 else estimated_minutes
    
    # Información adicional sobre el guion generado
    info_dict = {
        "word_count": word_count,
        "estimated_minutes": estimated_minutes,
        "estimated_minutes_ajustado": estimated_minutes_ajustado,
        "target_words": target_words,
        "duracion_real_segundos": duracion_real_segundos,
        "duracion_audio_segundos": duracion_audio_segundos,
        "velocidad_voz_usada": velocidad_voz,
        "palabras_narracion": palabras_narracion,
        "frame_metrics": frame_metrics,
    }
    
    # Guardar en historial (con guion completo, no cortado)
    try:
        guardar_en_historial(
            nombre_proyecto=proy,
            tema=tema or proy,
            guion_texto=guion_texto,  # Guion completo, sin cortar
            video_path=video_path,
            metadata_path=metadata_path,
            thumbnail_path=thumbnail_path,
            audio_path=audio_path,
            word_count=word_count,
            estimated_minutes=estimated_minutes_ajustado,
            target_words=target_words,
            width=width,
            height=height,
            velocidad_voz=velocidad_voz,
            segundos_por_imagen=seg_por_img,
        )
    except Exception as e:
        print(f"⚠️ Error al guardar en historial: {e}")

    return video_path, metadata_path, thumbnail_path, info_dict


def _saas_support_image_prompt(block: dict) -> str:
    """Prompt solo-texto para Replicate (B-roll sin personaje)."""
    vis_story = (block.get("visual") or "").strip()
    if vis_story:
        core = vis_story
    else:
        vd = (block.get("visual_direction") or "").strip()
        br = (block.get("b_roll_suggestion") or "").strip()
        parts = [x for x in (vd, br) if x]
        core = ". ".join(parts) if parts else (block.get("text") or "").strip()[:280]
    suffix = (
        " Dark realistic B-roll, uneasy night mood, cinematic low-key lighting, "
        "empty interior or object close-up, implied tension, "
        "no people, no faces, no characters, no text, no watermark, no logos, no cheerful stock look."
    )
    return (core + ". " + suffix).strip()[:3500]


def _saas_post_mix_ambient(
    video_path: Path,
    music: Path | None,
    sfx: Path | None,
    music_volume: float,
    sfx_volume: float,
) -> Path:
    """
    Mezcla la pista de audio del MP4 (narración) con música y/o SFX de ambiente.
    Si falla FFmpeg, devuelve el video original sin modificar.
    """
    if not music and not sfx:
        return video_path
    if not shutil.which("ffmpeg"):
        print("⚠️ [MVP] FFmpeg ausente: no se mezcla música/SFX.")
        return video_path
    if not video_path.exists():
        return video_path

    music_ok = bool(music and music.exists())
    sfx_ok = bool(sfx and sfx.exists())
    if not music_ok and not sfx_ok:
        return video_path

    out = video_path.with_name(video_path.stem + "_audio.mp4")
    cmd: list[str] = ["ffmpeg", "-y", "-i", str(video_path.resolve())]
    n_extra = 0
    if music_ok:
        cmd.extend(["-i", str(music.resolve())])
        n_extra += 1
    if sfx_ok:
        cmd.extend(["-i", str(sfx.resolve())])
        n_extra += 1

    if music_ok and sfx_ok:
        fc = (
            f"[1:a]volume={music_volume:.3f}[m];"
            f"[2:a]volume={sfx_volume:.3f}[s];"
            f"[m][s]amix=inputs=2:duration=longest[bg];"
            f"[0:a][bg]amix=inputs=2:duration=first[aout]"
        )
    elif music_ok:
        fc = f"[1:a]volume={music_volume:.3f}[m];[0:a][m]amix=inputs=2:duration=first[aout]"
    else:
        fc = f"[1:a]volume={sfx_volume:.3f}[s];[0:a][s]amix=inputs=2:duration=first[aout]"

    cmd.extend(
        [
            "-filter_complex",
            fc,
            "-map",
            "0:v",
            "-map",
            "[aout]",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            str(out.resolve()),
        ]
    )
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"⚠️ [MVP] Mezcla música/SFX falló, se deja video sin post-mix: {(e.stderr or '')[-400:]}")
        return video_path
    if out.exists() and out.stat().st_size > 0:
        return out
    return video_path


def _saas_write_progress(progress_path: Path | None, step: str, pct: float) -> None:
    if not progress_path:
        return
    try:
        progress_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = progress_path.with_suffix(progress_path.suffix + ".tmp")
        tmp.write_text(
            json.dumps({"step": step, "pct": max(0.0, min(100.0, pct))}, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp.replace(progress_path)
    except Exception:
        pass


def run_saas_mvp(
    topic: str,
    progress_path: Path | None = None,
    music_path: Path | None = None,
    sfx_path: Path | None = None,
    music_volume: float | None = None,
    sfx_volume: float | None = None,
    use_env_music_if_no_upload: bool = True,
    creative_profile: dict | None = None,
    session_context: str | None = None,
    target_words: int = 420,
    voice_speed: float = 1.0,
    subtitles_enabled: bool = True,
    subtitle_style_key: str = "default",
    character_id: str | None = None,
    background_id: str | None = None,
    voice_id: str | None = None,
    workspace_subdir: str | None = None,
    auto_viral_idea: bool = False,
    story_background_video: bool = False,
    gameplay_video_path: str | Path | None = None,
    video_aspect: str = "16:9",
    overlay_text: dict | None = None,
    skip_support_images: bool = False,
) -> Path:
    """
    MVP SaaS mínimo:
    guion -> bloques -> audio -> clips por bloque (imagen fija + audio) -> concat final.
    progress_path: si se pasa, escribe JSON {step, pct} para UI de progreso.
    music_path / sfx_path: archivos opcionales mezclados bajo la narración al final.
    Si music_path es None y use_env_music_if_no_upload, usa BACKGROUND_MUSIC_PATH del .env.
    creative_profile: perfil SaaS (guion, visual, montaje); guía al LLM y al plan por bloque.
    session_context: texto con memoria y chat de la sesión (congelado al iniciar el render).
    target_words: objetivo de palabras del guion (80–10000; se acota internamente).
    voice_speed: velocidad TTS (0.5–2.0); 1.0 = normal.
    subtitles_enabled: si True, quema subtítulos sincronizados por bloque (tras el concat).
    subtitle_style_key: clave en config/subtitle_styles.yaml (force_style ASS).
    character_id / background_id / voice_id: elecciones del Studio SaaS (catálogo).
    workspace_subdir: si se indica, toda la salida va a output/<subdir>/ (evita colisiones entre renders).
    auto_viral_idea: si True, genera idea + brief de guion desde el Creative Profile (topic puede ir vacío o como nota opcional).
    story_background_video: si True, fuerza narración solo sobre fondo/B-roll (sin personaje en pantalla), aunque el perfil no sea Reddit.
    gameplay_video_path: si se indica, clips = segmento de este video (loop/trim) + voz; sin Replicate; idea viral 3+mejor; subtítulos forzados.
    video_aspect: "16:9" (YouTube) o "9:16" (TikTok) cuando hay gameplay.
    overlay_text: dict opcional {text, x, y, size, color} para drawtext en el primer clip (FFmpeg).
    skip_support_images: si True (y no hay gameplay), no llama a Replicate por bloque: solo personaje + fondo del catálogo.
        También se fuerza si SAAS_SKIP_SUPPORT_IMAGES=1 en el entorno.
    """
    print("🚀 [MVP] Iniciando run_saas_mvp...")
    _saas_write_progress(progress_path, "Inicio", 0.0)
    if os.getenv("SAAS_SKIP_SUPPORT_IMAGES", "").strip().lower() in ("1", "true", "yes", "on"):
        skip_support_images = True
        print("🖼️ [MVP] SAAS_SKIP_SUPPORT_IMAGES activo — sin imágenes de apoyo (Replicate)")

    tw = int(target_words) if target_words is not None else 420
    tw = max(80, min(10000, tw))
    vs = float(voice_speed) if voice_speed is not None else 1.0
    vs = max(0.5, min(2.0, vs))

    gp_path: Path | None = None
    if gameplay_video_path and str(gameplay_video_path).strip():
        gp_path = Path(str(gameplay_video_path)).expanduser().resolve()
        if not gp_path.is_file():
            raise FileNotFoundError(f"[MVP] gameplay_video_path no es un archivo: {gameplay_video_path}")
    gameplay_mode = gp_path is not None
    if gameplay_mode and gp_path is not None:
        print(f"🎮 [MVP] Gameplay activo — video fuente: {gp_path.resolve()}")
    aspect_out = str(video_aspect or "16:9").strip()

    sub_on = bool(subtitles_enabled)
    sub_style = str(subtitle_style_key or "default").strip()
    if gameplay_mode:
        sub_on = True
        styles0 = get_subtitle_styles()
        valid0 = list_subtitle_style_keys(styles0)
        if "reddit_gameplay_center" in valid0:
            sub_style = "reddit_gameplay_center"
        elif "tiktok_karaoke" in valid0:
            sub_style = "tiktok_karaoke"
        elif sub_style not in valid0:
            sub_style = valid0[0] if valid0 else "default"

    prof = merge_profile_disk(creative_profile or {})
    script_ctx = profile_to_script_context(prof)
    if session_context and str(session_context).strip():
        script_ctx = (
            script_ctx
            + "\n\n=== LO HABLADO EN ESTA SESIÓN (prioridad con el tema del video) ===\n"
            + str(session_context).strip()[:24000]
        )
    viral_pkg: dict | None = None
    tema_core = (topic or "").strip()
    if gameplay_mode:
        _saas_write_progress(progress_path, "Idea viral (3)", 4.0)
        viral_pkg = generate_viral_story_idea_three_pick_best(prof, session_context)
        tema_core = (viral_pkg.get("script_seed") or "").strip()
        if not tema_core:
            tema_core = (viral_pkg.get("idea") or "").strip()
        if (topic or "").strip():
            tema_core = (
                f"{tema_core}\n\nNotas opcionales del creador (baja prioridad si chocan con la idea central):\n"
                f"{(topic or '').strip()}"
            )[:12000]
        if not tema_core.strip():
            raise RuntimeError("[MVP] gameplay: la idea viral no produjo un brief de guion utilizable.")
    elif auto_viral_idea:
        _saas_write_progress(progress_path, "Idea viral", 4.0)
        viral_pkg = generate_viral_idea_for_profile(prof, session_context)
        tema_core = (viral_pkg.get("script_seed") or "").strip()
        if not tema_core:
            tema_core = (viral_pkg.get("idea") or "").strip()
        if (topic or "").strip():
            tema_core = (
                f"{tema_core}\n\nNotas opcionales del creador (baja prioridad si chocan con la idea central):\n"
                f"{(topic or '').strip()}"
            )[:12000]
        if not tema_core.strip():
            raise RuntimeError("[MVP] auto_viral_idea no produjo un brief de guion utilizable.")
    elif not tema_core:
        raise ValueError("topic es obligatorio para run_saas_mvp (salvo auto_viral_idea=True o gameplay_video_path).")

    pub_topic_one_line = (
        (viral_pkg.get("idea") or viral_pkg.get("selected_idea") or "").strip() if viral_pkg else ""
    )
    if not pub_topic_one_line:
        pub_topic_one_line = (tema_core.split("\n")[0] or tema_core).strip()[:500]
    if viral_pkg and (viral_pkg.get("selected_idea") or viral_pkg.get("idea")):
        print(f"💡 [MVP] Idea viral seleccionada: {(viral_pkg.get('selected_idea') or viral_pkg.get('idea') or '')[:200]}")

    script_opening = (prof.get("script") or {}).get("opening_style") or ""
    force_pov = not bool(str(script_opening).strip())
    reddit_mode = bool(is_reddit_story_profile(prof)) or bool(story_background_video) or gameplay_mode
    if reddit_mode:
        print("📖 [MVP] Modo historia viral: Reddit / storytime — segmentos cortos, solo fondo+B-roll.")
        force_pov = False

    # ─── Estructura mínima ───────────────────────────────────────────────────
    base_output = BASE / "output"
    base_output.mkdir(parents=True, exist_ok=True)
    if workspace_subdir and str(workspace_subdir).strip():
        safe = "".join(c for c in str(workspace_subdir).strip() if c.isalnum() or c in ("-", "_"))[:96]
        if not safe:
            safe = "workspace"
        output_dir = (base_output / safe).resolve()
        try:
            output_dir.relative_to(base_output.resolve())
        except ValueError as e:
            raise ValueError("workspace_subdir escapa de output/") from e
    else:
        output_dir = base_output
    output_dir.mkdir(parents=True, exist_ok=True)
    chars_dir, bgs_dir = ensure_catalog_dirs()
    _ = bgs_dir
    ensure_default_catalog_assets()

    character = resolve_character_id(character_id)
    background = resolve_background_id(background_id)
    pref_v = prof.get("narrator_preference")
    if (voice_id or "").strip():
        voice = resolve_voice_id(voice_id)
    elif isinstance(pref_v, str) and pref_v.strip() in VOICES:
        voice = resolve_voice_id(pref_v.strip())
    else:
        voice = resolve_voice_id("male_sharp")
    print(f"🎭 [MVP] Character: {character['id']}")
    print(f"🖼️ [MVP] Background catalog: {background['id']}")
    print(f"🎙️ [MVP] Voice catalog: {voice['id']} ({voice['provider']})")

    scratch_assets = output_dir / "_saas_scratch"
    scratch_assets.mkdir(parents=True, exist_ok=True)
    bg_static_path = materialize_background_image(background, scratch_assets)
    print(f"🖼️ [MVP] Fondo materializado: {bg_static_path.resolve()}")

    if reddit_mode:
        character_img = bg_static_path
        print("🎭 [MVP] Narración sin personaje en pantalla (solo fondo / apoyo).")
    else:
        catalog_char = BASE / character["base_image_uri"]
        character_img = resolve_saas_character_image_path(catalog_char)
        if character_img.resolve() != catalog_char.resolve():
            print(f"🎭 [MVP] Personaje desde .env o visual_bible: {character_img.resolve()}")
        # Solo el PNG del catálogo recibe placeholder automático; env/biblia deben apuntar a un archivo real.
        if character_img.resolve() == catalog_char.resolve() and (
            not character_img.exists() or character_img.stat().st_size == 0
        ):
            print(f"⚠️ [MVP] No hay PNG válido en {character_img}; creando placeholder mínimo.")
            from PIL import Image, ImageDraw

            character_img.parent.mkdir(parents=True, exist_ok=True)
            img = Image.new("RGB", (1280, 720), (24, 24, 24))
            draw = ImageDraw.Draw(img)
            draw.ellipse((500, 120, 780, 400), fill=(255, 255, 255), outline=(0, 0, 0), width=6)
            draw.text((430, 440), "Business Cartoon MVP", fill=(230, 230, 230))
            img.save(character_img)
        if not character_img.exists() or character_img.stat().st_size == 0:
            raise FileNotFoundError(f"[MVP] Imagen de personaje inválida o vacía: {character_img}")

    # ─── Script y escenas ────────────────────────────────────────────────────
    print("📝 [MVP] Generando guion...")
    _saas_write_progress(progress_path, "Guion", 12.0)
    plantilla_guion = "reddit_stories" if reddit_mode else "explicativo"
    script_text, word_count, _mins = generar_guion(
        tema=tema_core,
        target_words=tw,
        plantilla=plantilla_guion,
        segundos_por_imagen=4.0 if reddit_mode else 6.0,
        creative_context=script_ctx,
        force_este_eres_tu_opening=False if reddit_mode else force_pov,
    )
    print(f"📊 [MVP] Guion generado: {word_count} palabras")

    _saas_write_progress(progress_path, "Escenas", 26.0)
    if reddit_mode:
        blocks = plan_scenes_reddit_segments(script_text, words_per_segment=words_per_reddit_segment(prof))
    else:
        blocks = plan_scenes(script_text)
    if not blocks:
        raise RuntimeError("[MVP] planificador de escenas devolvió 0 bloques.")
    print(f"🎬 [MVP] Bloques: {len(blocks)}")
    _saas_write_progress(progress_path, "Montaje (IA)", 30.0)
    blocks = annotate_blocks_with_editing(
        blocks,
        prof,
        session_context=session_context,
    )
    if reddit_mode:
        blocks = enrich_blocks_with_visual_intent(blocks, prof)
    pub_bundle = generar_bundle_publicacion_youtube(
        topic=pub_topic_one_line,
        script_text=script_text,
        scenes=blocks,
        profile=prof,
        packaging_mode="viral_gameplay" if gameplay_mode else "default",
    )
    try:
        _meta_body: dict = {"script": script_text, "blocks": blocks, "word_count": word_count}
        if viral_pkg:
            _meta_body["viral_meta"] = viral_pkg
        if skip_support_images and not gameplay_mode:
            _meta_body["skip_support_images"] = True
        if gameplay_mode and gp_path:
            _meta_body["gameplay_video"] = str(gp_path).replace("\\", "/")
            _meta_body["video_aspect"] = aspect_out
        (output_dir / "saas_last_mvp_meta.json").write_text(
            json.dumps(_meta_body, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (output_dir / "saas_publication_bundle.json").write_text(
            json.dumps(
                {
                    "script": script_text,
                    "scenes": blocks,
                    "title": pub_bundle.get("title"),
                    "alt_titles": pub_bundle.get("alt_titles"),
                    "description": pub_bundle.get("description"),
                    "thumbnail": pub_bundle.get("thumbnail"),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    except Exception:
        pass

    # ─── Voz + clip POR BLOQUE (cada escena = audio distinto + video distinto) ─
    _saas_write_progress(progress_path, "Voz por bloque", 42.0)
    reset_heygen_runtime_state()

    def _safe_block_audio_stem(block: dict, index: int) -> str:
        bid = str(block.get("id") or f"block_{index:04d}")
        safe = re.sub(r"[^\w\-]+", "_", bid, flags=re.UNICODE).strip("_") or f"block_{index:04d}"
        return f"saas_mvp_{safe}"

    clips: list[Path] = []
    block_audios: list[Path] = []
    n_blocks = max(1, len(blocks))
    seg_cursor = 0.0
    gplen = probe_media_duration_seconds(gp_path) if gameplay_mode and gp_path else 0.0
    if gameplay_mode and gplen <= 0.1:
        raise RuntimeError("[MVP] No se pudo leer la duración del video de gameplay.")
    ot_dict = overlay_text if isinstance(overlay_text, dict) else None

    for i, block in enumerate(blocks, start=1):
        bid = block.get("id", f"scene_{i:04d}")
        btext = (block.get("text") or "").strip()
        if not btext:
            raise RuntimeError(f"[MVP] Bloque sin texto: id={bid!r}")

        audio_stem = _safe_block_audio_stem(block, i)
        print(f"🔊 [MVP] Bloque audio | id={bid} | chars={len(btext)} | stem={audio_stem}")
        print(f"    texto: {btext[:200]}{'…' if len(btext) > 200 else ''}")

        block_audio = generar_voz(
            btext,
            nombre_archivo=audio_stem,
            velocidad=vs,
            voice_catalog=voice,
        )
        if not block_audio.exists() or block_audio.stat().st_size == 0:
            raise RuntimeError(f"[MVP] Audio de bloque inválido o vacío: {block_audio}")
        print(f"    audio_path: {block_audio.resolve()}")
        block_audios.append(block_audio)

        sup_file: Path | None = None
        pct_img = 48.0 + (38.0 * (i - 1) / n_blocks)
        if gameplay_mode:
            _saas_write_progress(progress_path, f"Gameplay {i}/{len(blocks)}", min(86.0, pct_img))
            print("    gameplay: sin imagen apoyo (Replicate omitido)")
        elif skip_support_images:
            _saas_write_progress(progress_path, f"Clip {i}/{len(blocks)} (sin IA)", min(86.0, pct_img))
            print("    apoyo_replicate: omitido (skip_support_images)")
        else:
            sup_cand = output_dir / f"saas_support_{i:04d}.png"
            _saas_write_progress(progress_path, f"Imagen apoyo {i}/{len(blocks)}", min(86.0, pct_img))
            got = generar_imagen_apoyo_replicate(_saas_support_image_prompt(block), sup_cand, escena_num=i)
            if got and got.exists() and got.stat().st_size > 0:
                sup_file = got
                print(f"    apoyo_replicate: {sup_file.resolve()}")
            else:
                print("    apoyo_replicate: (omitida)")

        clip = output_dir / f"clip_{i:04d}.mp4"
        print(f"🎞️ [MVP] Render bloque {i}/{len(blocks)} -> {clip.name}")
        pct = 48.0 + (40.0 * (i - 1) / n_blocks)
        _saas_write_progress(
            progress_path,
            f"Escena {i}/{len(blocks)} (gameplay)" if gameplay_mode else f"Clip {i}/{len(blocks)}",
            pct,
        )
        if gameplay_mode and gp_path is not None:
            adur = probe_media_duration_seconds(block_audio)
            if adur <= 0.05:
                adur = max(2.0, len(btext.split()) / 2.2)
            start_seg = seg_cursor % gplen
            draw_ov = ot_dict if (ot_dict and i == 1) else None
            render_gameplay_block_clip(
                gp_path,
                block_audio,
                clip,
                segment_start_sec=start_seg,
                duration_sec=adur,
                aspect=aspect_out,
                motion=str(block.get("motion") or "static"),
                transition_in=str(block.get("transition_in") or "none"),
                transition_out=str(block.get("transition_out") or "none"),
                drawtext_overlay=draw_ov,
            )
            seg_cursor += adur
        else:
            render_block(
                block=block,
                audio_path=block_audio,
                character_image=character_img,
                output_path=clip,
                background_static=bg_static_path,
                support_image=sup_file,
                narration_background_only=reddit_mode,
            )
        if not clip.exists() or clip.stat().st_size == 0:
            raise RuntimeError(f"[MVP] Clip inválido: {clip}")
        clips.append(clip)

    if not clips:
        raise RuntimeError("[MVP] No se generaron clips.")

    # ─── Concat final ────────────────────────────────────────────────────────
    if not shutil.which("ffmpeg"):
        raise RuntimeError("[MVP] FFmpeg no está instalado o no está en PATH.")
    list_file = output_dir / "clips.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for c in clips:
            seg = str(c.resolve()).replace("\\", "/")
            f.write(f"file '{seg}'\n")

    final_path = output_dir / "final.mp4"
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_file.resolve()),
        "-c",
        "copy",
        str(final_path.resolve()),
    ]
    print(f"🏁 [MVP] Concatenando clips en {final_path.resolve()}...")
    _saas_write_progress(
        progress_path,
        "Uniendo escenas (gameplay)" if gameplay_mode else "Montaje final",
        94.0,
    )
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        msg = (e.stderr or e.stdout or str(e))[-500:]
        raise RuntimeError(f"[MVP] Error en concat final FFmpeg: {msg}") from e

    if not final_path.exists() or final_path.stat().st_size == 0:
        raise RuntimeError(f"[MVP] Video final no generado correctamente: {final_path}")
    print(f"✅ [MVP] Video final listo: {final_path.resolve()}")

    if sub_on:
        try:
            styles = get_subtitle_styles()
            sk = str(sub_style or "default").strip()
            valid = list_subtitle_style_keys(styles)
            if sk not in valid:
                sk = "default" if "default" in valid else (valid[0] if valid else "default")
            ass_path = output_dir / "saas_mvp_subs.ass"
            write_ass_from_block_audios(
                blocks,
                block_audios,
                ass_path,
                subtitle_style_key=sk,
            )
            if ass_path.exists() and ass_path.stat().st_size > 80:
                burned = output_dir / "final_subburn.mp4"
                _saas_write_progress(progress_path, "Subtítulos", 95.0)
                final_path = burn_subtitles_on_video(final_path, ass_path, None, burned)
                print(f"📝 [MVP] Subtítulos quemados: {final_path.resolve()}")
            else:
                print("⚠️ [MVP] SRT de subtítulos vacío; se omite quemado.")
        except Exception as e:
            print(f"⚠️ [MVP] Subtítulos omitidos (se deja video sin quemar): {e}")

    mv = 0.18 if music_volume is None else max(0.0, min(0.6, float(music_volume)))
    sv = 0.08 if sfx_volume is None else max(0.0, min(0.4, float(sfx_volume)))
    eff_music = music_path if (music_path and music_path.exists()) else None
    if eff_music is None and use_env_music_if_no_upload:
        eff_music = get_background_music_path()
        if eff_music is not None and not eff_music.exists():
            eff_music = None
    eff_sfx = sfx_path if (sfx_path and sfx_path.exists()) else None
    if eff_music or eff_sfx:
        _saas_write_progress(progress_path, "Música y ambiente", 97.0)
        final_path = _saas_post_mix_ambient(final_path, eff_music, eff_sfx, mv, sv)
        print(f"🎵 [MVP] Post-mix audio: {final_path.resolve()}")

    _saas_write_progress(progress_path, "Listo", 100.0)
    try:
        write_saas_full_package(
            output_dir,
            viral_meta=viral_pkg,
            script_text=script_text,
            blocks=blocks,
            pub_bundle=pub_bundle,
            final_video=final_path,
        )
    except Exception as e:
        print(f"⚠️ [MVP] No se pudo escribir saas_full_package.json: {e}")
    try:
        idea_line = ""
        if viral_pkg and isinstance(viral_pkg, dict):
            idea_line = str(viral_pkg.get("idea") or "").strip()
        if not idea_line:
            idea_line = pub_topic_one_line
        (output_dir / "saas_render_result.json").write_text(
            json.dumps(
                {
                    "idea": idea_line,
                    "idea_alternatives": (viral_pkg or {}).get("alternatives") if viral_pkg else [],
                    "viral_meta": viral_pkg,
                    "script": script_text,
                    "scenes": blocks,
                    "title": pub_bundle.get("title"),
                    "alt_titles": pub_bundle.get("alt_titles"),
                    "description": pub_bundle.get("description"),
                    "thumbnail": pub_bundle.get("thumbnail"),
                    "video_path": str(final_path.resolve()).replace("\\", "/"),
                    "video_aspect": aspect_out if gameplay_mode else None,
                    "gameplay_mode": gameplay_mode,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    except Exception as e:
        print(f"⚠️ [MVP] No se pudo escribir saas_render_result.json: {e}")
    return final_path


def main():
    parser = argparse.ArgumentParser(description="FrameFactory-AI: pipeline de video desde guion o tema")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--tema", type=str, help="Tema para generar guion y video")
    g.add_argument("--guion", type=Path, help="Ruta a archivo de guion .txt")
    parser.add_argument("--duracion", type=int, default=2, help="Duración objetivo en minutos (solo con --tema)")
    parser.add_argument("--plantilla", type=str, default="explicativo", choices=["explicativo", "historia", "listado"])
    parser.add_argument("--nombre", type=str, help="Nombre del proyecto (carpetas y archivos de salida)")
    parser.add_argument("--skip-imagenes", action="store_true", help="No generar imágenes (usar las existentes)")
    parser.add_argument("--skip-voz", action="store_true", help="No generar voz")
    parser.add_argument("--musica", type=Path, help="Ruta a archivo de música de fondo")
    args = parser.parse_args()

    musica = args.musica if args.musica and args.musica.exists() else None
    video_path, metadata_path, thumbnail_path, info_dict = run(
        tema=args.tema,
        guion_path=args.guion,
        duracion_min=args.duracion,
        plantilla=args.plantilla,
        nombre_proyecto=args.nombre,
        skip_imagenes=args.skip_imagenes,
        skip_voz=args.skip_voz,
        musica_fondo=musica,
    )
    print(f"Video generado: {video_path}")
    if metadata_path:
        print(f"Metadata YouTube: {metadata_path}")
    if thumbnail_path:
        print(f"Miniatura: {thumbnail_path}")
    if info_dict.get("frame_metrics"):
        print(f"Métricas por frame: {len(info_dict['frame_metrics'])} entradas")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main()
    else:
        run_saas_mvp("Why most people fail at making money")
