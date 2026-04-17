"""Tests para scene_splitter.py"""
import pytest
from src.scene_splitter import dividir_en_escenas, escenas_a_texto_continuo, Escena


def test_dividir_en_escenas_por_parrafos_dobles():
    """Test: Divide correctamente por párrafos dobles"""
    guion = "Primer párrafo.\n\nSegundo párrafo.\n\nTercer párrafo."
    escenas = dividir_en_escenas(guion, segundos_por_imagen=5.0)
    
    assert len(escenas) == 3
    assert escenas[0].numero == 1
    assert escenas[0].texto == "Primer párrafo."
    assert escenas[0].duracion_segundos == 5.0
    assert escenas[1].texto == "Segundo párrafo."
    assert escenas[2].texto == "Tercer párrafo."


def test_dividir_en_escenas_por_parrafos_simples():
    """Test: Si no hay párrafos dobles, divide por simples"""
    guion = "Primera línea.\nSegunda línea.\nTercera línea."
    escenas = dividir_en_escenas(guion, segundos_por_imagen=3.0)
    
    assert len(escenas) >= 1
    assert escenas[0].duracion_segundos == 3.0


def test_dividir_en_escenas_texto_completo():
    """Test: Si no hay saltos de línea, usa el texto completo"""
    guion = "Este es un texto completo sin saltos de línea."
    escenas = dividir_en_escenas(guion)
    
    assert len(escenas) == 1
    assert escenas[0].texto == guion


def test_escenas_a_texto_continuo():
    """Test: Une todas las escenas correctamente"""
    escenas = [
        Escena(1, "Primera escena.", 5.0),
        Escena(2, "Segunda escena.", 5.0),
        Escena(3, "Tercera escena.", 5.0),
    ]
    
    texto = escenas_a_texto_continuo(escenas)
    
    assert "Primera escena" in texto
    assert "Segunda escena" in texto
    assert "Tercera escena" in texto
    assert len(texto) > 0


def test_escenas_a_texto_continuo_vacio():
    """Test: Maneja lista vacía correctamente"""
    texto = escenas_a_texto_continuo([])
    assert texto == ""


def test_escenas_a_texto_continuo_preserva_todo():
    """Test: No pierde texto al unir escenas"""
    guion_completo = "Primera parte.\n\nSegunda parte.\n\nTercera parte."
    escenas = dividir_en_escenas(guion_completo)
    texto_reconstruido = escenas_a_texto_continuo(escenas)
    
    # Verificar que todas las palabras estén presentes
    palabras_originales = set(guion_completo.lower().split())
    palabras_reconstruidas = set(texto_reconstruido.lower().split())
    
    # Debe tener al menos el 90% de las palabras (puede haber espacios diferentes)
    assert len(palabras_reconstruidas & palabras_originales) >= len(palabras_originales) * 0.9


def test_plan_scenes_reddit_segments_chunking():
    from src.scene_planner import plan_scenes_reddit_segments

    words = " ".join([f"w{i}" for i in range(25)])
    blocks = plan_scenes_reddit_segments(words, words_per_segment=10)
    assert len(blocks) == 3
    assert all("text" in b and "id" in b for b in blocks)


def test_is_reddit_story_profile():
    from src.reddit_story_mode import is_reddit_story_profile

    assert is_reddit_story_profile({"content_type": "reddit stories"}) is True
    assert is_reddit_story_profile({"video": {"narration_format": "reddit_background"}}) is True
    assert is_reddit_story_profile({"content_type": "educativo"}) is False
