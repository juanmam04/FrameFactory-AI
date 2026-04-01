"""FASE 9: Montaje automático de video con FFmpeg (imágenes + narración + música opcional)."""
import subprocess
import shutil
import sys
from pathlib import Path

from .config_loader import BASE, get_duracion_por_imagen

OUTPUT_VIDEO = BASE / "output" / "videos"


def verificar_ffmpeg() -> bool:
    """Verifica si FFmpeg está instalado y disponible en el PATH."""
    return shutil.which("ffmpeg") is not None


def verificar_ffprobe() -> bool:
    """Verifica si ffprobe está instalado y disponible en el PATH."""
    return shutil.which("ffprobe") is not None


def _montar_video_con_zoom_y_transiciones(
    lista_imagenes: list[Path],
    seg: float,
    width: int,
    height: int,
    video_solo: Path,
    fade_segundos: float = 0.25,
    zoom_final: float = 1.06,
) -> None:
    """
    Genera el video de imágenes con zoom suave (Ken Burns) y fundidos cortos entre escenas.
    Una sola llamada a FFmpeg: N entradas (una por imagen) + filter_complex con zoompan + fade + concat.
    """
    imagenes = [p for p in lista_imagenes if p.exists()]
    if not imagenes:
        return
    fps = 24
    frames_clip = max(1, int(seg * fps))
    # Zoom muy sutil: de 1.0 a zoom_final en frames_clip frames. Incremento por frame:
    zoom_inc = (zoom_final - 1.0) / frames_clip if frames_clip else 0
    # Fade in en frames (fade_segundos). OJO: evitamos fade out completo para no dejar el último clip totalmente negro,
    # porque luego el pipeline puede extender el video repitiendo el último tramo para igualar la duración del audio.
    # Si el último frame termina 100% negro, la extensión produce varios segundos/minutos de pantalla negra.
    fade_frames = max(1, int(fade_segundos * fps))

    # Rutas con barras normales para filter_complex (evitar problemas en Windows)
    def path_ff(v: Path) -> str:
        return str(v.resolve()).replace("\\", "/")

    # Construir filter_complex: [0:v] scale,crop,zoompan,fade in,fade out [v0]; [1:v] ... [v1]; ... [v0][v1]... concat
    partes = []
    for i in range(len(imagenes)):
        # zoompan: z='min(zoom+inc,zoom_final)':d=frames_clip:s=WxH
        # fade=t=in:st=0:d=fade_segundos
        scale_crop = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}"
        zp = f"zoompan=z='min(zoom+{zoom_inc:.6f},{zoom_final})':d={frames_clip}:s={width}x{height}:fps={fps}"
        fi = f"fade=t=in:st=0:d={fade_segundos}"
        # IMPORTANTÍSIMO: NO aplicamos fade out a negro aquí. Si el último clip termina en negro
        # y luego extendemos el video (stream_loop) para igualar la duración del audio,
        # el usuario ve muchos segundos de pantalla negra. Mejor dejar la última imagen visible.
        partes.append(f"[{i}:v]{scale_crop},{zp},{fi}[v{i}]")
    concat_inputs = "".join(f"[v{i}]" for i in range(len(imagenes)))
    concat_n = len(imagenes)
    filter_complex = ";".join(partes) + f";{concat_inputs}concat=n={concat_n}:v=1:a=0[out]"

    cmd = ["ffmpeg", "-y"]
    for p in imagenes:
        cmd.extend(["-loop", "1", "-t", "1", "-i", path_ff(p)])
    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-r", str(fps),
        "-pix_fmt", "yuv420p",
        str(video_solo),
    ])
    try:
        # Timeout de seguridad: si FFmpeg se cuelga (por filtros o archivos raros),
        # no bloquear todo el pipeline; lanzamos error y el caller hará fallback a montaje estático.
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"FFmpeg (zoom+transiciones) excedió el tiempo límite: {e}")

    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg (zoom+transiciones) falló: {result.stderr[:500]}")


def montar_video(
    lista_imagenes: list[Path],
    audio_narracion: Path | None,
    musica_fondo: Path | None = None,
    segundos_por_imagen: float | None = None,
    nombre_salida: str = "video_final",
    width: int = 1920,
    height: int = 1080,
    duracion_maxima_segundos: float | None = None,
    subtitles_path: Path | None = None,
    subtitle_style: str | None = None,
    transiciones_suaves: bool = False,
) -> Path:
    """
    Une imágenes en secuencia (duración por imagen configurable),
    agrega narración como pista principal y música de fondo opcional.
    Si transiciones_suaves=True, aplica zoom suave (Ken Burns) y fundidos cortos entre imágenes.
    Si no hay imágenes, genera un video negro con la duración del audio.
    """
    seg = segundos_por_imagen or get_duracion_por_imagen()
    OUTPUT_VIDEO.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_VIDEO / f"{nombre_salida}.mp4"

    # Verificar FFmpeg antes de continuar
    if not verificar_ffmpeg():
        cmd = "brew install ffmpeg" if sys.platform == "darwin" else "winget install ffmpeg o choco install ffmpeg"
        raise RuntimeError(
            "FFmpeg no está instalado o no está en el PATH del sistema.\n\n"
            f"Para instalar: {cmd}\n"
            "O descargá desde: https://ffmpeg.org/download.html\n\n"
            "Después de instalar, reiniciá la aplicación."
        )
    
    # Calcular duración del audio para video negro
    duracion_audio = None
    if audio_narracion and audio_narracion.exists() and audio_narracion.stat().st_size > 0:
        if verificar_ffprobe():
            try:
                # Obtener duración del audio con ffprobe
                cmd_probe = [
                    "ffprobe", "-v", "error", "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1", str(audio_narracion)
                ]
                result = subprocess.run(cmd_probe, capture_output=True, text=True, check=True)
                duracion_audio = float(result.stdout.strip())
            except Exception:
                # Si falla, usar duración estimada basada en imágenes o default
                duracion_audio = len(lista_imagenes) * seg if lista_imagenes else 60.0
        else:
            # Si no hay ffprobe, usar duración estimada
            duracion_audio = len(lista_imagenes) * seg if lista_imagenes else 60.0

    # Si no hay imágenes, generar video negro
    if not lista_imagenes or all(not p.exists() for p in lista_imagenes):
        video_solo = out.with_stem(out.stem + "_solo_video")
        # Generar video negro con la duración del audio o 60 segundos por defecto
        duracion = duracion_audio or 60.0
        cmd_video_negro = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"color=c=black:s={width}x{height}:d={duracion}",
            "-r", "24",
            "-pix_fmt", "yuv420p",
            str(video_solo),
        ]
        subprocess.run(cmd_video_negro, check=True, capture_output=True)
    else:
        video_solo = out.with_stem(out.stem + "_solo_video")
        if transiciones_suaves and len([p for p in lista_imagenes if p.exists()]) > 0:
            try:
                print("🎬 Aplicando zoom suave y transiciones entre imágenes...")
                _montar_video_con_zoom_y_transiciones(
                    lista_imagenes=lista_imagenes,
                    seg=seg,
                    width=width,
                    height=height,
                    video_solo=video_solo,
                    fade_segundos=0.25,
                    zoom_final=1.06,
                )
            except Exception as e:
                print(f"⚠️ Falló video con zoom/transiciones ({e}), usando montaje estático.")
                transiciones_suaves = False
        if not transiciones_suaves:
            # Montaje estático: concat de imágenes con leve fade inicial
            list_file = out.with_suffix(".list.txt")
            with open(list_file, "w") as f:
                for p in lista_imagenes:
                    if p.exists():
                        f.write(f"file '{p.absolute()}'\nduration {seg}\n")
                if lista_imagenes:
                    f.write(f"file '{lista_imagenes[-1].absolute()}'\n")
            cmd_video = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", str(list_file),
                "-vf",
                (
                    f"scale={width}:{height}:force_original_aspect_ratio=increase,"
                    f"crop={width}:{height},"
                    f"fade=t=in:st=0:d=0.5"
                ),
                "-r", "24",
                "-pix_fmt", "yuv420p",
                str(video_solo),
            ]
            subprocess.run(cmd_video, check=True, capture_output=True)
            if list_file.exists():
                list_file.unlink()

    # Mezclar con audio
    if audio_narracion and audio_narracion.exists() and audio_narracion.stat().st_size > 0:
        if musica_fondo and musica_fondo.exists():
            # Dos pistas: narración + música baja
            mix = out.with_stem(out.stem + "_mix")
            cmd_mix = [
                "ffmpeg", "-y",
                "-i", str(audio_narracion),
                "-i", str(musica_fondo),
                "-filter_complex", "[0:a]volume=1[a1];[1:a]volume=0.2[a2];[a1][a2]amix=inputs=2:duration=first",
                "-shortest", str(mix),
            ]
            subprocess.run(cmd_mix, check=True, capture_output=True)
            audio_final = mix
        else:
            audio_final = audio_narracion

        # Obtener duración del audio para asegurar que el video tenga esa duración
        duracion_audio_final = None
        print(f"🔍 Obteniendo duración del audio final...")
        if verificar_ffprobe():
            try:
                cmd_probe_audio = [
                    "ffprobe", "-v", "error", "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1", str(audio_final)
                ]
                result_audio = subprocess.run(cmd_probe_audio, capture_output=True, text=True, check=True)
                duracion_audio_final = float(result_audio.stdout.strip())
                print(f"📊 Duración del audio final: {duracion_audio_final:.1f} segundos ({duracion_audio_final/60:.1f} minutos)")
            except Exception as e:
                print(f"⚠️ No se pudo obtener duración del audio final: {e}")
                print(f"   Intentando método alternativo...")
                # Método alternativo: calcular desde el tamaño del archivo (aproximado)
                if audio_final.exists():
                    size_mb = audio_final.stat().st_size / (1024 * 1024)
                    # Estimación aproximada: 1 MB ≈ 1 minuto de audio MP3
                    duracion_audio_final = size_mb * 60
                    print(f"   Estimación aproximada: {duracion_audio_final:.1f} segundos")
        else:
            print(f"⚠️ ffprobe no disponible, no se puede obtener duración exacta del audio")
        
        # Obtener duración del video de imágenes
        duracion_video_imagenes = None
        print(f"🔍 Obteniendo duración del video de imágenes...")
        if verificar_ffprobe():
            try:
                cmd_probe_video = [
                    "ffprobe", "-v", "error", "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1", str(video_solo)
                ]
                result_video = subprocess.run(cmd_probe_video, capture_output=True, text=True, check=True)
                duracion_video_imagenes = float(result_video.stdout.strip())
                print(f"📊 Duración del video de imágenes: {duracion_video_imagenes:.1f} segundos ({duracion_video_imagenes/60:.1f} minutos)")
            except Exception as e:
                print(f"⚠️ No se pudo obtener duración del video: {e}")
                # Calcular duración estimada desde imágenes
                num_imagenes = len([p for p in lista_imagenes if p.exists()]) if lista_imagenes else 0
                duracion_video_imagenes = num_imagenes * seg
                print(f"   Estimación desde imágenes: {num_imagenes} imágenes × {seg}s = {duracion_video_imagenes:.1f} segundos")
        else:
            # Calcular duración estimada desde imágenes
            num_imagenes = len([p for p in lista_imagenes if p.exists()]) if lista_imagenes else 0
            duracion_video_imagenes = num_imagenes * seg
            print(f"📊 Duración estimada del video (sin ffprobe): {num_imagenes} imágenes × {seg}s = {duracion_video_imagenes:.1f} segundos")
        
        # Asegurar que siempre tengamos ambas duraciones antes de comparar
        if not duracion_video_imagenes and lista_imagenes:
            num_imagenes = len([p for p in lista_imagenes if p.exists()])
            duracion_video_imagenes = num_imagenes * seg
            print(f"📊 Duración estimada del video (fallback): {num_imagenes} imágenes × {seg}s = {duracion_video_imagenes:.1f}s")
        
        # Si el video es más corto que el audio, extenderlo
        print(f"🔍 Comparando duraciones:")
        print(f"   Video de imágenes: {duracion_video_imagenes}")
        print(f"   Audio final: {duracion_audio_final}")
        
        if duracion_audio_final and duracion_video_imagenes:
            diferencia = duracion_audio_final - duracion_video_imagenes
            print(f"   Diferencia: {diferencia:.1f} segundos")
            if duracion_video_imagenes < duracion_audio_final:
                print(f"⚠️ El video de imágenes ({duracion_video_imagenes:.1f}s) es más corto que el audio ({duracion_audio_final:.1f}s)")
                print(f"   Extendiendo el video para que coincida con el audio...")
                
                # Extender el video repitiendo el último frame
                video_extendido = out.with_stem(out.stem + "_extendido")
                
                # Usar loop del video existente y limitar a la duración del audio
                cmd_extend = [
                    "ffmpeg", "-y",
                    "-stream_loop", "-1",  # Loop infinito
                    "-i", str(video_solo),
                    "-t", str(duracion_audio_final),  # Limitar a la duración del audio
                    "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                    "-pix_fmt", "yuv420p",
                    "-avoid_negative_ts", "make_zero",
                    str(video_extendido)
                ]
                result_extend = subprocess.run(cmd_extend, capture_output=True, text=True)
                if result_extend.returncode != 0:
                    print(f"⚠️ Error al extender video: {result_extend.stderr}")
                    print(f"   Intentando método alternativo...")
                    # Método alternativo: concatenar el video consigo mismo
                    list_loop = out.with_suffix(".loop.txt")
                    num_loops = int(duracion_audio_final / duracion_video_imagenes) + 1
                    with open(list_loop, "w") as f:
                        for _ in range(num_loops):
                            f.write(f"file '{video_solo.absolute()}'\n")
                    cmd_concat = [
                        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                        "-i", str(list_loop),
                        "-t", str(duracion_audio_final),
                        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                        "-pix_fmt", "yuv420p",
                        str(video_extendido)
                    ]
                    subprocess.run(cmd_concat, check=True, capture_output=True)
                    if list_loop.exists():
                        list_loop.unlink()
                else:
                    print(f"   ✅ Video extendido a {duracion_audio_final:.1f} segundos")
                
                # Verificar que el video extendido existe y tiene la duración correcta
                if video_extendido.exists():
                    video_solo = video_extendido
                    # Verificar duración del video extendido
                    if verificar_ffprobe():
                        try:
                            cmd_check = [
                                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                                "-of", "default=noprint_wrappers=1:nokey=1", str(video_extendido)
                            ]
                            result_check = subprocess.run(cmd_check, capture_output=True, text=True, check=True)
                            duracion_extendido = float(result_check.stdout.strip())
                            print(f"   ✅ Video extendido verificado: {duracion_extendido:.1f}s (objetivo: {duracion_audio_final:.1f}s)")
                        except:
                            pass
        
        # Limitar duración si se especifica
        cmd_final = [
            "ffmpeg", "-y",
            "-i", str(video_solo),
            "-i", str(audio_final),
        ]

        # Subtítulos opcionales (SRT/ASS) con estilo configurable (ASS force_style)
        if subtitles_path and subtitles_path.exists():
            sub_filter = f"subtitles='{subtitles_path.as_posix()}'"
            if subtitle_style:
                sub_filter += f":force_style='{subtitle_style}'"
            cmd_final.extend(["-vf", sub_filter])

        cmd_final.extend([
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",  # Re-encodear video para mejor control
            "-c:a", "aac", "-b:a", "192k",
        ])
        
        # NUNCA usar -shortest porque puede cortar el audio
        # Siempre usar la duración del audio como referencia
        print(f"🔧 Configurando duración final del video...")
        print(f"   duracion_audio_final: {duracion_audio_final}")
        print(f"   duracion_maxima_segundos: {duracion_maxima_segundos}")
        
        # Asegurar que siempre tengamos la duración del audio
        if not duracion_audio_final:
            print(f"⚠️ No se obtuvo duración del audio antes, obteniéndola ahora...")
            if verificar_ffprobe():
                try:
                    cmd_probe_ahora = [
                        "ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1", str(audio_final)
                    ]
                    result_ahora = subprocess.run(cmd_probe_ahora, capture_output=True, text=True, check=True)
                    duracion_audio_final = float(result_ahora.stdout.strip())
                    print(f"   ✅ Duración del audio obtenida: {duracion_audio_final:.1f} segundos")
                except Exception as e:
                    print(f"   ⚠️ Error al obtener duración: {e}")
                    # Estimar desde tamaño del archivo
                    if audio_final.exists():
                        size_mb = audio_final.stat().st_size / (1024 * 1024)
                        duracion_audio_final = size_mb * 60  # 1 MB ≈ 1 minuto
                        print(f"   📊 Estimación desde tamaño: {duracion_audio_final:.1f} segundos")
        
        if duracion_maxima_segundos is not None:
            # Si hay límite máximo, usar el menor entre audio y límite
            duracion_final = min(duracion_audio_final or float('inf'), duracion_maxima_segundos)
            cmd_final.extend(["-t", str(duracion_final)])
            print(f"📹 Limitando video a {duracion_final:.1f} segundos (máximo especificado)")
        elif duracion_audio_final:
            # Usar la duración del audio como referencia
            cmd_final.extend(["-t", str(duracion_audio_final)])
            print(f"📹 Combinando video y audio con duración: {duracion_audio_final:.1f} segundos ({duracion_audio_final/60:.1f} minutos)")
            print(f"   ⚠️ IMPORTANTE: El video se limitará a esta duración. Si el video es más corto, debería haberse extendido antes.")
        else:
            # Último recurso: usar duración muy larga para no cortar
            print(f"⚠️ ADVERTENCIA CRÍTICA: No se puede determinar duración del audio")
            print(f"   Usando 10 minutos (600s) como seguridad para NO cortar el audio")
            cmd_final.extend(["-t", "600"])  # 10 minutos como seguridad
        
        cmd_final.append(str(out))
        print(f"🔧 Comando FFmpeg: {' '.join(cmd_final)}")
        result = subprocess.run(cmd_final, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"⚠️ Error al combinar video y audio:")
            print(f"   {result.stderr}")
            raise RuntimeError(f"Error al montar video: {result.stderr}")
        
        # Verificar duración final del video
        if verificar_ffprobe() and out.exists():
            try:
                cmd_verify = [
                    "ffprobe", "-v", "error", "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1", str(out)
                ]
                result_verify = subprocess.run(cmd_verify, capture_output=True, text=True, check=True)
                duracion_final_video = float(result_verify.stdout.strip())
                print(f"✅ Video final generado: {duracion_final_video:.1f} segundos")
                if duracion_audio_final and abs(duracion_final_video - duracion_audio_final) > 2.0:
                    print(f"⚠️ ADVERTENCIA: Duración del video ({duracion_final_video:.1f}s) no coincide con audio ({duracion_audio_final:.1f}s)")
            except:
                pass
    else:
        # Si no hay audio, copiar el video solo (negro o con imágenes)
        out.write_bytes(video_solo.read_bytes())

    return out
