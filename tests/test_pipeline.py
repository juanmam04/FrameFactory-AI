"""Tests para pipeline.py - Validaciones críticas"""
import pytest
from pathlib import Path
from src.pipeline import sanitizar_nombre_proyecto
from src.script_generator import count_words


def test_sanitizar_nombre_proyecto():
    """Test: Sanitiza nombres de proyecto correctamente"""
    # Caracteres especiales
    assert sanitizar_nombre_proyecto("Test: Proyecto/Con\\Caracteres") == "Test_Proyecto_Con_Caracteres"
    
    # Espacios
    assert sanitizar_nombre_proyecto("Proyecto con espacios") == "Proyecto_con_espacios"
    
    # Límite de longitud
    nombre_largo = "A" * 100
    resultado = sanitizar_nombre_proyecto(nombre_largo)
    assert len(resultado) <= 50


def test_validacion_guion_completo():
    """Test: Verifica que el guion completo se preserve"""
    # Simular un guion completo
    guion_completo = """
    Este es el inicio de la historia.
    
    Aquí está el desarrollo con más detalles.
    
    Y finalmente, este es el final de la historia.
    """
    
    # Dividir en escenas
    from src.scene_splitter import dividir_en_escenas, escenas_a_texto_continuo
    
    escenas = dividir_en_escenas(guion_completo)
    texto_reconstruido = escenas_a_texto_continuo(escenas)
    
    # Verificar que no se perdió contenido crítico
    palabras_originales = count_words(guion_completo)
    palabras_reconstruidas = count_words(texto_reconstruido)
    
    # No debe perder más del 10% de las palabras
    assert palabras_reconstruidas >= palabras_originales * 0.9, \
        f"Se perdió demasiado texto: {palabras_originales} -> {palabras_reconstruidas}"


def test_validacion_palabras_objetivo():
    """Test: Verifica que el sistema respete el rango de palabras objetivo"""
    target_words = 500
    min_words = int(target_words * 0.8)  # 400
    max_words = int(target_words * 1.2)  # 600
    
    # Simular un guion generado
    import os
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("No hay OPENAI_API_KEY configurada")
    
    from src.script_generator import generar_guion
    
    guion, word_count, _ = generar_guion(
        tema="Test de validación",
        target_words=target_words,
        min_words=min_words,
        max_words=max_words,
    )
    
    # Verificar que esté en el rango
    assert word_count >= min_words, f"Guion muy corto: {word_count} < {min_words}"
    assert word_count <= max_words, f"Guion muy largo: {word_count} > {max_words}"


def test_validacion_guion_no_cortado():
    """Test: Verifica que el guion no esté cortado abruptamente"""
    import os
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("No hay OPENAI_API_KEY configurada")
    
    from src.script_generator import generar_guion
    
    guion, word_count, _ = generar_guion(
        tema="Historia completa de prueba",
        target_words=300,
    )
    
    # Verificar que termine con puntuación adecuada
    guion_limpio = guion.strip()
    assert len(guion_limpio) > 0, "Guion vacío"
    assert guion_limpio[-1] in ".!?", f"Guion cortado, termina en: '{guion_limpio[-1]}'"
    
    # Verificar que tenga contenido sustancial
    assert len(guion_limpio) > 200, "Guion muy corto"
    
    # Verificar que tenga múltiples oraciones
    oraciones = guion.count(".") + guion.count("!") + guion.count("?")
    assert oraciones >= 3, f"Guion debería tener al menos 3 oraciones, tiene {oraciones}"
