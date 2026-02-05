#!/usr/bin/env python3
"""
Script de validación completa del código
Verifica que todo funcione correctamente antes de generar videos
"""
import sys
from pathlib import Path
import subprocess
import importlib.util

def verificar_imports():
    """Verifica que todos los módulos se puedan importar"""
    print("🔍 Verificando imports...")
    errores = []
    
    modulos = [
        "src.script_generator",
        "src.scene_splitter",
        "src.voice_generator",
        "src.video_assembler",
        "src.pipeline",
        "src.image_generator",
    ]
    
    for modulo in modulos:
        try:
            spec = importlib.util.find_spec(modulo)
            if spec is None:
                errores.append(f"❌ No se encuentra: {modulo}")
            else:
                print(f"   ✅ {modulo}")
        except Exception as e:
            errores.append(f"❌ Error importando {modulo}: {e}")
    
    return errores


def verificar_funciones_criticas():
    """Verifica que las funciones críticas existan"""
    print("\n🔍 Verificando funciones críticas...")
    errores = []
    
    try:
        from src.script_generator import count_words, generar_guion
        from src.scene_splitter import dividir_en_escenas, escenas_a_texto_continuo
        from src.voice_generator import generar_voz
        from src.video_assembler import montar_video
        
        # Verificar que sean callables
        funciones = {
            "count_words": count_words,
            "generar_guion": generar_guion,
            "dividir_en_escenas": dividir_en_escenas,
            "escenas_a_texto_continuo": escenas_a_texto_continuo,
            "generar_voz": generar_voz,
            "montar_video": montar_video,
        }
        
        for nombre, func in funciones.items():
            if not callable(func):
                errores.append(f"❌ {nombre} no es callable")
            else:
                print(f"   ✅ {nombre}")
                
    except ImportError as e:
        errores.append(f"❌ Error importando funciones: {e}")
    
    return errores


def verificar_count_words():
    """Verifica que count_words funcione correctamente"""
    print("\n🔍 Verificando count_words...")
    errores = []
    
    from src.script_generator import count_words
    
    casos_prueba = [
        ("palabra", 1),
        ("Dos palabras", 2),
        ("Tres palabras con", 3),  # 3 palabras
        ("Cuatro\npalabras\ncon\nsaltos", 4),
        ("", 0),
        ("   ", 0),
    ]
    
    for texto, esperado in casos_prueba:
        resultado = count_words(texto)
        if resultado != esperado:
            errores.append(f"❌ count_words('{texto}') = {resultado}, esperado {esperado}")
        else:
            print(f"   ✅ count_words('{texto}') = {resultado}")
    
    return errores


def verificar_dividir_escenas():
    """Verifica que dividir_en_escenas funcione correctamente"""
    print("\n🔍 Verificando dividir_en_escenas...")
    errores = []
    
    from src.scene_splitter import dividir_en_escenas
    
    guion = "Primera escena.\n\nSegunda escena.\n\nTercera escena."
    escenas = dividir_en_escenas(guion)
    
    if len(escenas) != 3:
        errores.append(f"❌ Se esperaban 3 escenas, se obtuvieron {len(escenas)}")
    else:
        print(f"   ✅ Dividió correctamente en {len(escenas)} escenas")
    
    # Verificar que no haya escenas vacías
    escenas_vacias = [e for e in escenas if not e.texto.strip()]
    if escenas_vacias:
        errores.append(f"❌ Se encontraron {len(escenas_vacias)} escenas vacías")
    else:
        print(f"   ✅ No hay escenas vacías")
    
    return errores


def verificar_escenas_a_texto_continuo():
    """Verifica que escenas_a_texto_continuo preserve todo el texto"""
    print("\n🔍 Verificando escenas_a_texto_continuo...")
    errores = []
    
    from src.scene_splitter import dividir_en_escenas, escenas_a_texto_continuo
    from src.script_generator import count_words
    
    guion = "Primera parte del texto.\n\nSegunda parte del texto.\n\nTercera parte del texto."
    palabras_originales = count_words(guion)
    
    escenas = dividir_en_escenas(guion)
    texto_reconstruido = escenas_a_texto_continuo(escenas)
    palabras_reconstruidas = count_words(texto_reconstruido)
    
    # No debe perder más del 5% de las palabras
    if palabras_reconstruidas < palabras_originales * 0.95:
        errores.append(
            f"❌ Se perdió texto: {palabras_originales} -> {palabras_reconstruidas} "
            f"({(1 - palabras_reconstruidas/palabras_originales)*100:.1f}% pérdida)"
        )
    else:
        print(f"   ✅ Preservó {palabras_reconstruidas}/{palabras_originales} palabras ({palabras_reconstruidas/palabras_originales*100:.1f}%)")
    
    return errores


def verificar_ffmpeg():
    """Verifica que FFmpeg esté disponible"""
    print("\n🔍 Verificando FFmpeg...")
    errores = []
    
    import shutil
    
    if not shutil.which("ffmpeg"):
        errores.append("❌ FFmpeg no está instalado o no está en PATH")
    else:
        print("   ✅ FFmpeg encontrado")
    
    if not shutil.which("ffprobe"):
        print("   ⚠️ ffprobe no encontrado (recomendado pero no crítico)")
    else:
        print("   ✅ ffprobe encontrado")
    
    return errores


def ejecutar_tests():
    """Ejecuta los tests unitarios"""
    print("\n🧪 Ejecutando tests unitarios...")
    
    try:
        result = subprocess.run(
            ["pytest", "tests/", "-v", "--tb=short"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent
        )
        
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        
        if result.returncode != 0:
            return ["❌ Algunos tests fallaron"]
        else:
            print("   ✅ Todos los tests pasaron")
            return []
            
    except FileNotFoundError:
        return ["❌ pytest no está instalado. Instala con: pip install pytest"]
    except Exception as e:
        return [f"❌ Error ejecutando tests: {e}"]


def main():
    print("=" * 70)
    print("🔬 VALIDACIÓN COMPLETA DEL CÓDIGO - FrameFactory-AI")
    print("=" * 70)
    print()
    
    todos_errores = []
    
    # Verificaciones
    todos_errores.extend(verificar_imports())
    todos_errores.extend(verificar_funciones_criticas())
    todos_errores.extend(verificar_count_words())
    todos_errores.extend(verificar_dividir_escenas())
    todos_errores.extend(verificar_escenas_a_texto_continuo())
    todos_errores.extend(verificar_ffmpeg())
    todos_errores.extend(ejecutar_tests())
    
    print()
    print("=" * 70)
    if todos_errores:
        print("❌ VALIDACIÓN FALLIDA")
        print()
        print("Errores encontrados:")
        for error in todos_errores:
            print(f"  {error}")
        return 1
    else:
        print("✅ VALIDACIÓN EXITOSA - TODO FUNCIONA CORRECTAMENTE")
        return 0


if __name__ == "__main__":
    sys.exit(main())
