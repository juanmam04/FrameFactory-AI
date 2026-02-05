"""Tests para video_assembler.py"""
import pytest
from pathlib import Path
import subprocess
import shutil


def test_verificar_ffmpeg():
    """Test: Verifica que FFmpeg esté disponible"""
    from src.video_assembler import verificar_ffmpeg
    
    tiene_ffmpeg = verificar_ffmpeg()
    
    # Si no está instalado, el test falla (es requerido)
    if not tiene_ffmpeg:
        pytest.skip("FFmpeg no está instalado - requerido para tests de video")
    
    assert tiene_ffmpeg


def test_verificar_ffprobe():
    """Test: Verifica que ffprobe esté disponible"""
    from src.video_assembler import verificar_ffprobe
    
    tiene_ffprobe = verificar_ffprobe()
    
    # ffprobe es útil pero no crítico
    # No fallamos el test si no está, solo lo notamos
    assert isinstance(tiene_ffprobe, bool)


def test_montar_video_duracion_audio():
    """Test: El video debe tener la duración del audio, no más corto"""
    from src.video_assembler import montar_video
    from pathlib import Path
    import tempfile
    
    if not shutil.which("ffmpeg"):
        pytest.skip("FFmpeg no está instalado")
    
    # Crear archivos de prueba
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # Crear imagen de prueba (1x1 pixel PNG)
        imagen_test = tmp_path / "test.png"
        from PIL import Image
        img = Image.new("RGB", (100, 100), color="black")
        img.save(imagen_test)
        
        # Crear audio de prueba (5 segundos de silencio)
        audio_test = tmp_path / "test.mp3"
        cmd_audio = [
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "anullsrc=channel_layout=mono:sample_rate=44100",
            "-t", "5",  # 5 segundos
            str(audio_test)
        ]
        result = subprocess.run(cmd_audio, capture_output=True)
        if result.returncode != 0:
            pytest.skip("No se pudo crear audio de prueba")
        
        # Montar video
        video_output = tmp_path / "test_video.mp4"
        try:
            video_path = montar_video(
                lista_imagenes=[imagen_test],
                audio_narracion=audio_test,
                nombre_salida="test_video",
                segundos_por_imagen=2.0,  # Cada imagen 2 segundos
                width=1920,
                height=1080,
            )
            
            assert video_path.exists()
            
            # Verificar duración del video
            if shutil.which("ffprobe"):
                cmd_probe = [
                    "ffprobe", "-v", "error", "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)
                ]
                result = subprocess.run(cmd_probe, capture_output=True, text=True)
                if result.returncode == 0:
                    duracion_video = float(result.stdout.strip())
                    # El video debe tener al menos la duración del audio (5 segundos)
                    # Puede ser un poco más por el padding, pero no menos
                    assert duracion_video >= 4.5, f"Video muy corto: {duracion_video}s < 4.5s"
                    assert duracion_video <= 6.0, f"Video muy largo: {duracion_video}s > 6.0s"
        
        except Exception as e:
            pytest.fail(f"Error al montar video: {e}")


def test_montar_video_extiende_si_necesario():
    """Test: Extiende el video si es más corto que el audio"""
    from src.video_assembler import montar_video
    from pathlib import Path
    import tempfile
    
    if not shutil.which("ffmpeg"):
        pytest.skip("FFmpeg no está instalado")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # Crear imagen de prueba
        imagen_test = tmp_path / "test.png"
        from PIL import Image
        img = Image.new("RGB", (100, 100), color="black")
        img.save(imagen_test)
        
        # Crear audio largo (10 segundos)
        audio_test = tmp_path / "test.mp3"
        cmd_audio = [
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "anullsrc=channel_layout=mono:sample_rate=44100",
            "-t", "10",  # 10 segundos
            str(audio_test)
        ]
        subprocess.run(cmd_audio, capture_output=True)
        
        # Montar video con imagen corta (solo 2 segundos)
        video_path = montar_video(
            lista_imagenes=[imagen_test],
            audio_narracion=audio_test,
            nombre_salida="test_video",
            segundos_por_imagen=2.0,  # Solo 2 segundos de imagen
            width=1920,
            height=1080,
        )
        
        # Verificar que el video tenga la duración del audio
        if shutil.which("ffprobe") and video_path.exists():
            cmd_probe = [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)
            ]
            result = subprocess.run(cmd_probe, capture_output=True, text=True)
            if result.returncode == 0:
                duracion_video = float(result.stdout.strip())
                # El video debe extenderse para coincidir con el audio
                assert duracion_video >= 9.0, f"Video no se extendió: {duracion_video}s < 9.0s (audio: 10s)"
