"""FASE 8: Generación de voz IA para narración del guion."""
import os
from pathlib import Path

from dotenv import load_dotenv

from .config_loader import BASE

load_dotenv(BASE / ".env")

OUTPUT_AUDIO = BASE / "output" / "audio"


def generar_voz(texto: str, nombre_archivo: str = "narracion", formato: str = "mp3", velocidad: float = 1.0) -> Path:
    """
    Genera audio de narración con API de voz IA (ElevenLabs o OpenAI TTS).
    Exporta en mp3 o wav.
    velocidad: 1.0 = normal, 1.2 = 20% más rápido, 0.8 = 20% más lento
    """
    OUTPUT_AUDIO.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_AUDIO / f"{nombre_archivo}.{formato}"

    # Generar audio base
    audio_base = None
    
    # ElevenLabs (con fallback a OpenAI si falla)
    api_key = os.getenv("ELEVENLABS_API_KEY")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
    if api_key:
        try:
            audio_base = _elevenlabs(texto, path, api_key, voice_id)
        except Exception as e:
            # Si ElevenLabs falla (pago requerido, etc.), usar OpenAI como fallback
            print(f"⚠️ ElevenLabs falló ({e}), usando OpenAI TTS como alternativa...")
            openai_key = os.getenv("OPENAI_API_KEY")
            if openai_key:
                audio_base = _openai_tts(texto, path, formato)
    else:
        # OpenAI TTS
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            audio_base = _openai_tts(texto, path, formato)

    if not audio_base:
        # Sin API: crear archivo vacío o avisar
        path.write_bytes(b"")
        return path
    
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
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
    }
    data = {"text": texto, "model_id": "eleven_multilingual_v2"}
    r = requests.post(url, json=data, headers=headers, timeout=60)
    r.raise_for_status()
    path.write_bytes(r.content)
    return path


def _openai_tts(texto: str, path: Path, formato: str) -> Path:
    from openai import OpenAI
    client = OpenAI()
    ext = "mp3" if formato == "mp3" else "wav"
    response = client.audio.speech.create(
        model=os.getenv("OPENAI_TTS_MODEL", "tts-1-hd"),
        voice=os.getenv("OPENAI_TTS_VOICE", "alloy"),
        input=texto,
    )
    path = path.with_suffix(f".{ext}")
    response.stream_to_file(path)
    return path
