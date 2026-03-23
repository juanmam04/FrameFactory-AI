"""FASE 11: Script maestro – ejecuta todo el pipeline con un solo comando."""
import argparse
import re
from pathlib import Path

from .config_loader import BASE, get_subtitle_styles, get_visual_bible

try:
    from .config_loader import get_background_music_path
except ImportError:
    def get_background_music_path():
        return None
from .script_generator import generar_guion, guardar_guion, count_words
from .scene_splitter import dividir_en_escenas, escenas_a_texto_continuo, Escena
from .prompt_builder import prompts_para_escenas, prompts_para_beats, emotion_to_expression_key, get_outfit_key_for_beat
from .image_generator import generar_lote, OUTPUT_IMAGES
from .voice_generator import generar_voz
from .video_assembler import montar_video
from .regeneration import guardar_prompts_por_escena
from .metadata_youtube import generar_metadata_completa
from .history import guardar_en_historial
from .visual_beats import generar_beats_para_escenas, guardar_beats, generar_subtitulos_srt


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
    Caracteres inválidos: < > : " | ? * \
    """
    # Caracteres inválidos en Windows
    caracteres_invalidos = r'[<>:"|?*\\]'
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
    - info_dict contiene: word_count, estimated_minutes
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
    beats_con_prompts = prompts_para_beats(
        beats, video_theme=tema_para_desc, project_id=proy
    )

    # Adaptar beats → estructura Escena para reutilizar regeneración y montaje; expression_key y outfit_key para Kontext/outfit ref
    escenas_con_prompts: list[tuple[Escena, str, str | None, str, str]] = [
        (
            Escena(
                numero=beat.beat_id,
                texto=beat.original_text,
                duracion_segundos=seg_por_img,
            ),
            prompt,
            emotion_to_expression_key(beat.emotion),
            get_outfit_key_for_beat(beat),
            (gen_meta or {}).get("seed_material", ""),
        )
        for beat, prompt, gen_meta in beats_con_prompts
    ]
    guardar_prompts_por_escena(escenas_con_prompts, proy)

    lista_imagenes: list[Path] = []
    if not skip_imagenes:
        n_imgs = len(escenas_con_prompts)
        print(f"🖼️ Generando {n_imgs} imágenes (puede tardar varios minutos)...")
        lista_imagenes = generar_lote(escenas_con_prompts, subcarpeta=proy, width=width, height=height)
        print(f"✅ Imágenes generadas: {len(lista_imagenes)}")
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
    video_path, metadata_path = run(
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


if __name__ == "__main__":
    main()
