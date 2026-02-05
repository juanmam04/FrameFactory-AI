"""Tests de integración - Verifica el flujo completo"""
import pytest
from pathlib import Path
import os


def test_flujo_completo_sin_apis():
    """Test: Verifica que el flujo funcione sin APIs (usando fallbacks)"""
    from src.script_generator import generar_guion, count_words
    from src.scene_splitter import dividir_en_escenas, escenas_a_texto_continuo
    
    # Guardar API keys originales
    openai_key = os.getenv("OPENAI_API_KEY")
    
    try:
        # Temporalmente quitar API key para usar fallback
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]
        
        # Generar guion (usará fallback)
        guion, word_count, estimated_minutes = generar_guion(
            tema="Test de integración",
            target_words=200,
        )
        
        # Verificar guion
        assert guion is not None
        assert len(guion) > 0
        assert word_count > 0
        
        # Dividir en escenas
        escenas = dividir_en_escenas(guion)
        assert len(escenas) > 0
        
        # Reconstruir texto
        texto_narracion = escenas_a_texto_continuo(escenas)
        assert len(texto_narracion) > 0
        
        # Verificar que no se perdió contenido
        palabras_originales = count_words(guion)
        palabras_narracion = count_words(texto_narracion)
        
        # No debe perder más del 5% de las palabras
        assert palabras_narracion >= palabras_originales * 0.95, \
            f"Se perdió contenido: {palabras_originales} -> {palabras_narracion}"
        
    finally:
        # Restaurar API key
        if openai_key:
            os.environ["OPENAI_API_KEY"] = openai_key


def test_validacion_duracion_estimada():
    """Test: Verifica que la duración estimada sea razonable"""
    from src.script_generator import generar_guion
    
    target_words = 280  # 2 minutos a 140 palabras/min
    
    import os
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("No hay OPENAI_API_KEY configurada")
    
    guion, word_count, estimated_minutes = generar_guion(
        tema="Test de duración",
        target_words=target_words,
    )
    
    # Verificar que estimated_minutes sea razonable
    # Debería ser aproximadamente word_count / 140
    expected_minutes = word_count / 140.0
    
    # Permitir margen del 20%
    assert abs(estimated_minutes - expected_minutes) / expected_minutes < 0.2, \
        f"Duración estimada incorrecta: {estimated_minutes} vs {expected_minutes}"


def test_consistencia_palabras():
    """Test: Verifica consistencia en el conteo de palabras"""
    from src.script_generator import count_words
    
    textos_prueba = [
        "Una palabra",
        "Dos palabras aquí",
        "Tres palabras en total",
        "Cuatro palabras en este texto",
        "Cinco palabras en este texto completo",
    ]
    
    for i, texto in enumerate(textos_prueba, 1):
        palabras = count_words(texto)
        assert palabras == i, f"Conteo incorrecto: '{texto}' tiene {palabras} palabras, esperado {i}"
