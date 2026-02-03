"""FASE 8: Generación de voz IA para narración del guion."""
import os
from pathlib import Path

from dotenv import load_dotenv

from .config_loader import BASE

load_dotenv(BASE / ".env")

OUTPUT_AUDIO = BASE / "output" / "audio"


def generar_voz(texto: str, nombre_archivo: str = "narracion", formato: str = "mp3") -> Path:
    """
    Genera audio de narración con API de voz IA (ElevenLabs o OpenAI TTS).
    Exporta en mp3 o wav.
    """
    OUTPUT_AUDIO.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_AUDIO / f"{nombre_archivo}.{formato}"

    # ElevenLabs
    api_key = os.getenv("ELEVENLABS_API_KEY")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
    if api_key:
        return _elevenlabs(texto, path, api_key, voice_id)

    # OpenAI TTS
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        return _openai_tts(texto, path, formato)

    # Sin API: crear archivo vacío o avisar
    path.write_bytes(b"")
    return path


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
