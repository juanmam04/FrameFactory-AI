#!/usr/bin/env python3
"""Genera UNA imagen con DALL-E (IMAGE_BACKEND=openai) para probar."""
import os
import sys
from pathlib import Path

# Raíz del proyecto
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

os.environ["IMAGE_BACKEND"] = "openai"
from dotenv import load_dotenv
load_dotenv(REPO / ".env")

from src.image_generator import generar_imagen, _get_image_backend

def main():
    carpeta = REPO / "output" / "imagenes"
    carpeta.mkdir(parents=True, exist_ok=True)
    # Escena debe LLENAR todo el frame: sin barras ni márgenes a los costados
    style = (
        "Single image, one scene only. Flat 2D stickman, line art, dark outlines, "
        "round head with two small dot eyes, simple stick body and limbs. "
        "Simple flat colors, limited palette. No 3D, no panels. "
        "Full frame: the scene must fill the entire image edge to edge, no margins, no colored bars on sides or top or bottom, no letterboxing. Composition extends to all four edges."
    )
    context = (
        "Party scene: indoor room with string lights, balloons, other stick figures, "
        "main stickman in center, tables or decorations. Medium shot. 16:9 aspect ratio, full frame."
    )
    prompt = f"{style} Same character. {context}"
    print("Backend:", _get_image_backend())
    print("Generando una imagen con DALL-E (fiesta, mismo estilo)...")
    path = generar_imagen(prompt, 2, carpeta, 1280, 720)
    print("Listo:", path)
    return 0 if path else 1

if __name__ == "__main__":
    sys.exit(main())
