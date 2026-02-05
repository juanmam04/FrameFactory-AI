#!/usr/bin/env python3
"""
Script para ejecutar todos los tests y verificar el código
"""
import subprocess
import sys
from pathlib import Path

def main():
    print("=" * 70)
    print("🧪 EJECUTANDO TESTS UNITARIOS - FrameFactory-AI")
    print("=" * 70)
    print()
    
    # Verificar que pytest esté instalado
    try:
        import pytest
    except ImportError:
        print("❌ pytest no está instalado")
        print("   Instala con: pip install pytest pytest-cov")
        return 1
    
    # Ejecutar tests
    print("📋 Ejecutando tests...")
    print()
    
    result = subprocess.run(
        ["pytest", "tests/", "-v", "--tb=short", "--color=yes"],
        cwd=Path(__file__).parent
    )
    
    print()
    print("=" * 70)
    if result.returncode == 0:
        print("✅ TODOS LOS TESTS PASARON")
    else:
        print("❌ ALGUNOS TESTS FALLARON")
    print("=" * 70)
    
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())
