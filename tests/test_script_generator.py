"""Tests para script_generator.py"""
import pytest
from src.script_generator import count_words, generar_guion


def test_count_words_basico():
    """Test: Cuenta palabras correctamente"""
    texto = "Este es un texto de prueba con diez palabras exactas aquí"
    assert count_words(texto) == 10


def test_count_words_con_espacios_multiples():
    """Test: Maneja espacios múltiples correctamente"""
    texto = "Palabra1    Palabra2\n\nPalabra3"
    assert count_words(texto) == 3


def test_count_words_vacio():
    """Test: Maneja texto vacío"""
    assert count_words("") == 0
    assert count_words("   ") == 0
    assert count_words("\n\n") == 0


def test_count_words_con_puntuacion():
    """Test: Cuenta palabras con puntuación"""
    texto = "Hola, mundo! ¿Cómo estás? Bien, gracias."
    # "Hola" "mundo" "Cómo" "estás" "Bien" "gracias" = 6 palabras
    assert count_words(texto) == 6


def test_generar_guion_fallback_sin_api():
    """Test: Genera guion fallback cuando no hay API"""
    import os
    api_key_original = os.getenv("OPENAI_API_KEY")
    
    try:
        # Temporalmente quitar la API key
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]
        
        guion, word_count, estimated_minutes = generar_guion(
            tema="Test tema",
            target_words=200,
        )
        
        assert guion is not None
        assert len(guion) > 0
        assert word_count > 0
        assert estimated_minutes > 0
        # El guion fallback debería tener aproximadamente las palabras objetivo
        assert word_count >= 150  # Al menos 75% del objetivo
        assert word_count <= 250  # Máximo 125% del objetivo
        
    finally:
        # Restaurar API key
        if api_key_original:
            os.environ["OPENAI_API_KEY"] = api_key_original


def test_generar_guion_respeta_target_words():
    """Test: El guion generado está cerca del target_words"""
    import os
    
    # Solo correr si hay API key
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("No hay OPENAI_API_KEY configurada")
    
    target = 300
    guion, word_count, estimated_minutes = generar_guion(
        tema="Historia corta de prueba",
        target_words=target,
    )
    
    # Verificar que esté dentro del rango aceptable (80%-120%)
    assert word_count >= int(target * 0.8), f"Guion muy corto: {word_count} < {int(target * 0.8)}"
    assert word_count <= int(target * 1.2), f"Guion muy largo: {word_count} > {int(target * 1.2)}"
    
    # Verificar que el guion no esté cortado (debe terminar con puntuación)
    assert guion.strip()[-1] in ".!?", f"Guion puede estar cortado, termina en: {guion.strip()[-1]}"
    
    # Verificar que estimated_minutes sea razonable
    assert estimated_minutes > 0
    assert estimated_minutes < 30  # No debería ser más de 30 minutos para 300 palabras


def test_generar_guion_historia_completa():
    """Test: El guion generado tiene inicio, desarrollo y final"""
    import os
    
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("No hay OPENAI_API_KEY configurada")
    
    guion, word_count, _ = generar_guion(
        tema="Una aventura épica",
        target_words=200,
    )
    
    # Verificar que tenga contenido sustancial
    assert len(guion) > 500  # Al menos 500 caracteres
    
    # Verificar que tenga múltiples oraciones (indica desarrollo)
    oraciones = guion.count(".") + guion.count("!") + guion.count("?")
    assert oraciones >= 3, "El guion debería tener al menos 3 oraciones"
    
    # Verificar que no esté cortado abruptamente
    assert not guion.strip().endswith("..."), "El guion parece estar cortado"
