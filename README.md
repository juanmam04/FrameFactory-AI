# FrameFactory-AI

Sistema automático de creación de videos con IA. Genera videos largos a partir de un guion: escenas visuales, voz sintética, edición automática y exportación final.

## Requisitos

- **Python 3.10+**
- **FFmpeg** instalado en el sistema
- **Stable Diffusion** (Automatic1111 o ComfyUI) en local, o API en la nube
- APIs: modelo de lenguaje (OpenAI/Claude/etc.) y voz IA (ElevenLabs/OpenAI TTS/etc.)

## Instalación

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Editar .env con tus API keys y URLs
```

## Uso rápido

### Frontend (navegador)

```bash
streamlit run app.py
```

Se abre la app en el navegador. Podés:
- **Desde un tema**: escribir el tema, duración y estilo → se genera guion + video.
- **Desde un guion**: pegar o subir un .txt → se generan escenas, imágenes, voz y video.
- Opcional: nombre del proyecto, saltar imágenes/voz, subir música de fondo.
- Al final podés ver y descargar el video.

### Línea de comandos

```bash
# Generar video desde un tema
python -m src.pipeline --tema "Historia de la inteligencia artificial"

# O desde un guion existente
python -m src.pipeline --guion mi_guion.txt
```

## Estructura del proyecto

- `config/` — Biblia visual, estilo base y plantillas
- `src/` — Pipeline: guiones → escenas → imágenes → voz → video
- `output/` — Guiones, imágenes y videos generados

## Fases del plan (según PDF)

1. Definición del sistema (config)
2. Infraestructura (Python, FFmpeg)
3. Generador de guiones
4. División en escenas
5. Prompts visuales
6. Generación de imágenes (Stable Diffusion)
7. Control de calidad (opcional)
8. Generación de voz
9. Montaje de video (FFmpeg)
10. Regeneración parcial
11. Script maestro (pipeline)
12–13. Escala e iteración
