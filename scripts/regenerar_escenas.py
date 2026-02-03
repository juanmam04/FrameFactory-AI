#!/usr/bin/env python3
"""Regenerar solo escenas específicas de un proyecto (Fase 10)."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.regeneration import regenerar_escenas


def main():
    parser = argparse.ArgumentParser(description="Regenerar escenas de un proyecto")
    parser.add_argument("proyecto", type=str, help="Nombre del proyecto")
    parser.add_argument("escenas", type=int, nargs="+", help="Números de escena a regenerar (ej: 1 3 5)")
    parser.add_argument("--carpeta", type=str, help="Subcarpeta de imágenes (por defecto = nombre del proyecto)")
    args = parser.parse_args()
    carpeta = args.carpeta or args.proyecto
    rutas = regenerar_escenas(args.escenas, args.proyecto, carpeta)
    for r in rutas:
        print(r)


if __name__ == "__main__":
    main()
