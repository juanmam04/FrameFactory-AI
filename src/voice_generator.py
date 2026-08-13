"""FASE 8: Generación de voz IA para narración del guion."""
import os
from pathlib import Path

from dotenv import load_dotenv

from .config_loader import BASE

load_dotenv(BASE / ".env")
for _env_local in (BASE / ".env.local", BASE / "env.local"):
    if _env_local.is_file():
        load_dotenv(_env_local, override=True)

OUTPUT_AUDIO = BASE / "output" / "audio"


def _audio_root() -> Path:
    if (os.getenv("VERCEL") or os.getenv("VERCEL_ENV") or "").strip():
        root = Path("/tmp/ff-audio")
    else:
        root = OUTPUT_AUDIO
    root.mkdir(parents=True, exist_ok=True)
    return root


def _concat_mp3(paths: list[Path], dest: Path) -> Path:
    """Join MP3 chunks without FFmpeg (same encoder → frames concatenate)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("wb") as out:
        for part in paths:
            out.write(part.read_bytes())
    return dest


def generar_voz(
    texto: str,
    nombre_archivo: str = "narracion",
    formato: str = "mp3",
    velocidad: float = 1.0,
    *,
    voice_catalog: dict | None = None,
    elevenlabs_voice_id: str | None = None,
    openai_tts_voice: str | None = None,
) -> Path:
    """
    Genera audio de narración con API de voz IA (ElevenLabs o OpenAI TTS).
    Exporta en mp3 o wav.
    velocidad: 1.0 = normal, 1.2 = 20% más rápido, 0.8 = 20% más lento
    elevenlabs_voice_id: si viene, sustituye a ELEVENLABS_VOICE_ID del .env (catálogo SaaS).
    openai_tts_voice: nombre de voz OpenAI TTS (p. ej. alloy, nova) si usás ese proveedor.
    voice_catalog: entrada del catálogo SaaS (provider openai|elevenlabs, openai_voice, elevenlabs_voice_id).
    """
    path = _audio_root() / f"{nombre_archivo}.{formato}"

    # Always re-read .env + .env.local (local wins) before calling providers.
    try:
        from src.documentary.openai_key import reload_env

        reload_env()
    except Exception:
        load_dotenv(BASE / ".env", override=True)
        for _extra in (BASE / ".env.local", BASE / "env.local"):
            if _extra.is_file():
                load_dotenv(_extra, override=True)

    # Generar audio base
    audio_base = None

    vc = voice_catalog if isinstance(voice_catalog, dict) else {}
    pref_openai = str(vc.get("provider") or "").lower() == "openai"
    el_cat = vc.get("elevenlabs_voice_id")
    if isinstance(el_cat, str) and el_cat.strip():
        elevenlabs_voice_id = el_cat.strip()
    oa_cat = vc.get("openai_voice")
    if isinstance(oa_cat, str) and oa_cat.strip():
        openai_tts_voice = oa_cat.strip()

    api_key = (os.getenv("ELEVENLABS_API_KEY") or "").strip()
    openai_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    voice_id = (elevenlabs_voice_id or os.getenv("ELEVENLABS_VOICE_ID") or "21m00Tcm4TlvDq8ikWAM").strip() or "21m00Tcm4TlvDq8ikWAM"
    solo_elevenlabs = os.getenv("ELEVENLABS_SOLO", "").strip().lower() in ("1", "true", "yes")
    caracteres = len(texto)

    if pref_openai:
        if openai_key:
            audio_base = _openai_tts(texto, path, formato, voice=openai_tts_voice)
        elif api_key:
            audio_base = _elevenlabs(texto, path, api_key, voice_id)
        else:
            audio_base = None
    elif api_key:
        try:
            audio_base = _elevenlabs(texto, path, api_key, voice_id)
        except Exception as e:
            if solo_elevenlabs:
                raise RuntimeError(
                    f"ElevenLabs falló y tenés ELEVENLABS_SOLO: se usa solo la voz de ElevenLabs. Error: {e}"
                ) from e
            print(f"⚠️ ElevenLabs falló ({e})")
            print(f"   💡 Usando OpenAI TTS como alternativa...")
            if openai_key:
                audio_base = _openai_tts(texto, path, formato, voice=openai_tts_voice)
            else:
                audio_base = None
    elif openai_key:
        audio_base = _openai_tts(texto, path, formato, voice=openai_tts_voice)

    if not audio_base:
        # FF100-P0-007: nunca marcar como éxito un MP3 vacío.
        raise RuntimeError(
            "No se pudo generar voz: falta ELEVENLABS_API_KEY y/o OPENAI_API_KEY "
            "(o el proveedor elegido falló). Configurá las keys en .env."
        )

    if not path.exists() or path.stat().st_size <= 0:
        raise RuntimeError(f"TTS devolvió audio vacío o inexistente: {path}")

    # Aplicar velocidad si es diferente de 1.0
    if velocidad != 1.0:
        return _aplicar_velocidad_audio(audio_base, velocidad, path)

    return audio_base


def _aplicar_velocidad_audio(audio_path: Path, velocidad: float, output_path: Path) -> Path:
    """Aplica velocidad al audio usando FFmpeg (atempo filter)."""
    import subprocess
    import shutil
    
    if not shutil.which("ffmpeg"):
        # Si no hay FFmpeg, retornar audio original
        return audio_path
    
    # FFmpeg atempo: valores entre 0.5 y 2.0
    # Para velocidades fuera de rango, usar múltiples atempo
    velocidad_clamp = max(0.5, min(2.0, velocidad))
    
    # Si velocidad > 2.0, usar múltiples filtros
    filtros = []
    vel_restante = velocidad_clamp
    while vel_restante > 2.0:
        filtros.append("atempo=2.0")
        vel_restante /= 2.0
    while vel_restante < 0.5:
        filtros.append("atempo=0.5")
        vel_restante /= 0.5
    if abs(vel_restante - 1.0) > 0.01:
        filtros.append(f"atempo={vel_restante:.2f}")
    
    filter_complex = ",".join(filtros) if filtros else "atempo=1.0"
    
    # Si la velocidad es 1.0, no hacer nada
    if abs(velocidad - 1.0) < 0.01:
        return audio_path
    
    try:
        # Crear archivo temporal para el audio procesado
        audio_velocidad = output_path.parent / f"{output_path.stem}_velocidad{output_path.suffix}"
        cmd = [
            "ffmpeg", "-y", "-i", str(audio_path),
            "-af", filter_complex,
            "-c:a", "libmp3lame", "-b:a", "192k",
            str(audio_velocidad),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        
        # Si el archivo temporal es diferente al original, reemplazarlo
        if audio_velocidad != output_path and audio_velocidad.exists():
            if output_path.exists():
                output_path.unlink()
            audio_velocidad.rename(output_path)
        
        return output_path
    except Exception as e:
        print(f"⚠️ Error al aplicar velocidad: {e}, usando audio original")
        return audio_path


def _elevenlabs(texto: str, path: Path, api_key: str, voice_id: str) -> Path:
    import requests
    import subprocess
    import shutil
    
    caracteres = len(texto)
    MAX_CHARS_ELEVENLABS = 5000  # Límite de ElevenLabs
    
    # Si el texto es muy largo, dividirlo en chunks
    if caracteres > MAX_CHARS_ELEVENLABS:
        print(f"   ⚠️ Texto muy largo ({caracteres} caracteres), dividiendo en chunks para ElevenLabs...")
        
        # Dividir por oraciones cuando sea posible
        oraciones = texto.replace("!", ".\n").replace("?", "?\n").split(".\n")
        oraciones = [o.strip() + "." for o in oraciones if o.strip()]
        
        chunks = []
        chunk_actual = []
        chars_actual = 0
        
        for oracion in oraciones:
            oracion_con_espacio = oracion + " "
            if chars_actual + len(oracion_con_espacio) > MAX_CHARS_ELEVENLABS:
                if chunk_actual:
                    chunks.append(" ".join(chunk_actual))
                    chunk_actual = [oracion]
                    chars_actual = len(oracion)
                else:
                    # Oración muy larga, dividirla por palabras
                    palabras_oracion = oracion.split()
                    for palabra in palabras_oracion:
                        palabra_con_espacio = palabra + " "
                        if chars_actual + len(palabra_con_espacio) > MAX_CHARS_ELEVENLABS:
                            if chunk_actual:
                                chunks.append(" ".join(chunk_actual))
                                chunk_actual = [palabra]
                                chars_actual = len(palabra)
                            else:
                                chunks.append(palabra)
                                chars_actual = 0
                        else:
                            chunk_actual.append(palabra)
                            chars_actual += len(palabra_con_espacio)
            else:
                chunk_actual.append(oracion)
                chars_actual += len(oracion_con_espacio)
        
        if chunk_actual:
            chunks.append(" ".join(chunk_actual))
        
        print(f"   📦 Texto dividido en {len(chunks)} chunks para ElevenLabs")
        
        # Generar audio para cada chunk
        archivos_audio = []
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json",
        }
        
        for i, chunk in enumerate(chunks):
            print(f"   🔄 Generando chunk {i+1}/{len(chunks)} con ElevenLabs ({len(chunk)} caracteres)...")
            chunk_path = path.parent / f"{path.stem}_chunk_{i}.mp3"
            
            # Calcular timeout dinámico
            timeout_base = 60
            timeout_estimado = max(timeout_base, int(len(chunk) / 100) + 30)
            timeout_final = min(timeout_estimado, 300)
            
            try:
                data = {"text": chunk, "model_id": "eleven_multilingual_v2"}
                r = requests.post(url, json=data, headers=headers, timeout=timeout_final)
                r.raise_for_status()
                chunk_path.write_bytes(r.content)
                archivos_audio.append(chunk_path)
            except Exception as e:
                print(f"   ⚠️ Error al generar chunk {i+1}: {e}")
                raise
        
        path_final = path.with_suffix(".mp3")
        if shutil.which("ffmpeg") and len(archivos_audio) > 1:
            print(f"   🔗 Combinando {len(archivos_audio)} archivos de audio de ElevenLabs...")
            list_file = path.parent / f"{path.stem}_concat.txt"
            with open(list_file, "w", encoding="utf-8") as f:
                for audio_file in archivos_audio:
                    ruta_abs = str(audio_file.absolute()).replace("\\", "/")
                    f.write(f"file '{ruta_abs}'\n")
            cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", str(list_file),
                "-c:a", "libmp3lame", "-b:a", "192k",
                "-af", "apad=pad_dur=0.1",
                str(path_final)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                cmd_simple = [
                    "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                    "-i", str(list_file),
                    "-c:a", "libmp3lame", "-b:a", "192k",
                    str(path_final)
                ]
                subprocess.run(cmd_simple, check=True, capture_output=True)
            list_file.unlink()
        else:
            _concat_mp3(archivos_audio, path_final)
        for audio_file in archivos_audio:
            if audio_file.exists():
                audio_file.unlink()
        return path_final
    
    # Texto normal, generar directamente
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
    }
    data = {"text": texto, "model_id": "eleven_multilingual_v2"}
    
    # Calcular timeout dinámico basado en la longitud del texto
    timeout_base = 60  # Mínimo 60 segundos
    timeout_estimado = max(timeout_base, int(caracteres / 100) + 30)  # +30 segundos de margen
    timeout_final = min(timeout_estimado, 300)  # Máximo 5 minutos
    
    print(f"   ⏱️ Timeout configurado: {timeout_final}s (texto: {caracteres} caracteres)")
    
    try:
        r = requests.post(url, json=data, headers=headers, timeout=timeout_final)
        r.raise_for_status()
        path.write_bytes(r.content)
        return path
    except requests.exceptions.Timeout as e:
        print(f"   ⚠️ ElevenLabs timeout después de {timeout_final}s")
        raise Exception(f"ElevenLabs timeout: el texto es muy largo ({caracteres} caracteres) o el servidor está lento") from e
    except requests.exceptions.RequestException as e:
        print(f"   ⚠️ Error de conexión con ElevenLabs: {e}")
        raise


def _openai_tts(texto: str, path: Path, formato: str, voice: str | None = None) -> Path:
    from openai import OpenAI
    client = OpenAI()
    ext = "mp3" if formato == "mp3" else "wav"
    
    # Verificar longitud del texto
    caracteres = len(texto)
    palabras = len(texto.split())
    print(f"   📝 Generando audio con {palabras} palabras ({caracteres} caracteres)")
    
    # OpenAI TTS tiene un límite de 4096 caracteres por request
    # Si el texto es muy largo, dividirlo en chunks
    MAX_CHARS = 4000  # Margen de seguridad
    
    if caracteres > MAX_CHARS:
        print(f"   ⚠️ Texto muy largo ({caracteres} caracteres), dividiendo en chunks...")
        
        # Obtener modelo y voz una sola vez para mantener consistencia
        modelo = os.getenv("OPENAI_TTS_MODEL", "tts-1-hd")
        voz = (voice or os.getenv("OPENAI_TTS_VOICE", "alloy")).strip() or "alloy"
        print(f"   🎤 Usando modelo: {modelo}, voz: {voz} (consistente para todos los chunks)")
        
        chunks = []
        palabras_chunk = texto.split()
        chunk_actual = []
        chars_actual = 0
        
        # Dividir por oraciones cuando sea posible para mantener naturalidad
        # Primero intentar dividir por oraciones completas
        oraciones = texto.replace("!", ".\n").replace("?", "?\n").split(".\n")
        oraciones = [o.strip() + "." for o in oraciones if o.strip()]
        
        if len(oraciones) > 1:
            # Dividir por oraciones
            for oracion in oraciones:
                oracion_con_espacio = oracion + " "
                if chars_actual + len(oracion_con_espacio) > MAX_CHARS:
                    if chunk_actual:
                        chunks.append(" ".join(chunk_actual))
                        chunk_actual = [oracion]
                        chars_actual = len(oracion)
                    else:
                        # Oración muy larga, dividirla por palabras
                        palabras_oracion = oracion.split()
                        for palabra in palabras_oracion:
                            palabra_con_espacio = palabra + " "
                            if chars_actual + len(palabra_con_espacio) > MAX_CHARS:
                                if chunk_actual:
                                    chunks.append(" ".join(chunk_actual))
                                    chunk_actual = [palabra]
                                    chars_actual = len(palabra)
                                else:
                                    chunks.append(palabra)
                                    chars_actual = 0
                            else:
                                chunk_actual.append(palabra)
                                chars_actual += len(palabra_con_espacio)
                else:
                    chunk_actual.append(oracion)
                    chars_actual += len(oracion_con_espacio)
        else:
            # Si no hay oraciones claras, dividir por palabras
            for palabra in palabras_chunk:
                palabra_con_espacio = palabra + " "
                if chars_actual + len(palabra_con_espacio) > MAX_CHARS:
                    if chunk_actual:
                        chunks.append(" ".join(chunk_actual))
                        chunk_actual = [palabra]
                        chars_actual = len(palabra)
                    else:
                        chunks.append(palabra)
                        chars_actual = 0
                else:
                    chunk_actual.append(palabra)
                    chars_actual += len(palabra_con_espacio)
        
        if chunk_actual:
            chunks.append(" ".join(chunk_actual))
        
        print(f"   📦 Texto dividido en {len(chunks)} chunks")
        for i, chunk in enumerate(chunks):
            print(f"      Chunk {i+1}: {len(chunk)} caracteres, {len(chunk.split())} palabras")
        
        # Generar audio para cada chunk y combinarlos
        import tempfile
        archivos_audio = []
        
        for i, chunk in enumerate(chunks):
            print(f"   🔄 Generando chunk {i+1}/{len(chunks)} ({len(chunk)} caracteres, voz: {voz})...")
            chunk_path = path.parent / f"{path.stem}_chunk_{i}.{ext}"
            
            # Asegurar que usamos exactamente el mismo modelo y voz
            response = client.audio.speech.create(
                model=modelo,  # Usar la variable, no os.getenv() de nuevo
                voice=voz,     # Usar la variable, no os.getenv() de nuevo
                input=chunk,
            )
            chunk_path = chunk_path.with_suffix(f".{ext}")
            response.stream_to_file(chunk_path)
            archivos_audio.append(chunk_path)
        
        # Combinar archivos de audio usando FFmpeg
        import subprocess
        import shutil
        
        path_final = path.with_suffix(f".{ext}")
        if shutil.which("ffmpeg") and len(archivos_audio) > 1:
            print(f"   🔗 Combinando {len(archivos_audio)} archivos de audio...")
            list_file = path.parent / f"{path.stem}_concat.txt"
            with open(list_file, "w", encoding="utf-8") as f:
                for audio_file in archivos_audio:
                    ruta_abs = str(audio_file.absolute()).replace("\\", "/")
                    f.write(f"file '{ruta_abs}'\n")
            cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", str(list_file),
                "-c:a", "libmp3lame", "-b:a", "192k",
                "-af", "apad=pad_dur=0.1",
                str(path_final)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                cmd_simple = [
                    "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                    "-i", str(list_file),
                    "-c:a", "libmp3lame", "-b:a", "192k",
                    str(path_final)
                ]
                subprocess.run(cmd_simple, check=True, capture_output=True)
            list_file.unlink()
        else:
            _concat_mp3(archivos_audio, path_final)
        for audio_file in archivos_audio:
            if audio_file.exists():
                audio_file.unlink()
        return path_final
    else:
        # Texto normal, generar directamente
        voz_single = (voice or os.getenv("OPENAI_TTS_VOICE", "alloy")).strip() or "alloy"
        response = client.audio.speech.create(
            model=os.getenv("OPENAI_TTS_MODEL", "tts-1-hd"),
            voice=voz_single,
            input=texto,
        )
        path = path.with_suffix(f".{ext}")
        response.stream_to_file(path)
        return path
