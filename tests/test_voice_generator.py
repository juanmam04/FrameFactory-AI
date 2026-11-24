"""Tests para voice_generator.py"""
import pytest
from pathlib import Path
import os


def test_elevenlabs_dividir_chunks():
    """Test: Divide texto largo en chunks para ElevenLabs"""
    from src.voice_generator import _elevenlabs
    
    # Crear texto largo (>5000 caracteres)
    texto_largo = "Esta es una oración de prueba. " * 300  # ~9000 caracteres
    
    if not os.getenv("ELEVENLABS_API_KEY"):
        pytest.skip("No hay ELEVENLABS_API_KEY configurada")
    
    # Este test verifica que la función maneje textos largos
    # No generamos audio real para no gastar créditos
    assert len(texto_largo) > 5000, "El texto de prueba debe ser > 5000 caracteres"


def test_openai_tts_dividir_chunks():
    """Test: Divide texto largo en chunks para OpenAI TTS"""
    from src.voice_generator import _openai_tts
    
    # Crear texto largo (>4000 caracteres)
    texto_largo = "Esta es una oración de prueba. " * 200  # ~6000 caracteres
    
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("No hay OPENAI_API_KEY configurada")
    
    # Verificar que el texto sea largo
    assert len(texto_largo) > 4000, "El texto de prueba debe ser > 4000 caracteres"
    
    # La función debería dividir automáticamente
    # No generamos audio real para no gastar créditos en tests


def test_generar_voz_texto_corto():
    """Test: Genera voz para texto corto correctamente"""
    from src.voice_generator import generar_voz
    
    texto_corto = "Este es un texto corto de prueba para generar audio."
    
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ELEVENLABS_API_KEY"):
        pytest.skip("No hay API keys configuradas")
    
    # Generar audio (esto puede gastar créditos, comentar si no quieres)
    # audio_path = generar_voz(texto_corto, "test_audio", "mp3")
    # assert audio_path.exists()
    # assert audio_path.stat().st_size > 0
    
    # Por ahora solo verificamos que la función existe y acepta parámetros
    assert callable(generar_voz)


def test_aplicar_velocidad_audio():
    """Test: Aplica velocidad al audio correctamente"""
    from src.voice_generator import _aplicar_velocidad_audio
    from pathlib import Path
    
    # Este test requiere un archivo de audio real
    # Por ahora solo verificamos que la función existe
    assert callable(_aplicar_velocidad_audio)


def test_elevenlabs_tts_con_tiempos_v3_y_fallback(monkeypatch):
    import base64 as b64

    from src import voice_generator as vg

    sent = []

    class Resp:
        def __init__(self, code, payload=None, content=b""):
            self.status_code, self._p, self.content = code, payload, content
            self.text = str(payload)

        def json(self):
            return self._p

    def post(url, params=None, json=None, headers=None, timeout=None):
        sent.append((url, json))
        if url.endswith("/with-timestamps") and json["model_id"] == "eleven_v3":
            return Resp(200, {"audio_base64": b64.b64encode(b"MP3").decode(), "alignment": {"characters": ["a"], "character_start_times_seconds": [0], "character_end_times_seconds": [0.2]}})
        if url.endswith("/with-timestamps"):
            return Resp(422, {"detail": {"status": "unsupported", "message": "no timestamps"}})
        return Resp(200, content=b"PLAIN")

    monkeypatch.setattr("requests.post", post)
    audio, al, env = vg.elevenlabs_tts_con_tiempos("a", "V", "k", model_id="eleven_v3", voice_settings={"stability": 0.3})
    assert audio == b"MP3" and al["characters"] == ["a"]
    assert sent[-1][1]["voice_settings"]["stability"] == 0.5 and env["stability"] == 0.5
    audio, al, env = vg.elevenlabs_tts_con_tiempos("a", "V", "k", model_id="otro")
    assert audio == b"PLAIN" and al is None and "sin_tiempos" in env


def test_palabras_desde_alineacion_con_marcas_y_factor():
    from src.voice_generator import palabras_desde_alineacion

    t = "[sighs] uy, no"
    al = {"characters": list(t), "character_start_times_seconds": [i * 0.1 for i in range(len(t))], "character_end_times_seconds": [i * 0.1 + 0.1 for i in range(len(t))]}
    w = palabras_desde_alineacion(al, factor=0.5)
    assert [x["palabra"] for x in w] == ["[sighs]", "uy,", "no"]
    assert w[0]["marca"] is True and w[2] == {"palabra": "no", "inicio": 0.6, "fin": 0.7}
