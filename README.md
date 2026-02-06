# FrameFactory-AI

Sistema automático de creación de videos con IA. Genera videos largos a partir de un guion: escenas visuales, voz sintética, edición automática y exportación final.

## Requisitos

- **Python 3.10+**
- **FFmpeg** instalado en el sistema
- **Stable Diffusion** (Automatic1111 o ComfyUI) en local o en la nube (ej. RunPod)
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
- ComfyUI puede ser local (puerto 8188) o remoto: poné `COMFYUI_URL` en `.env` (ej. RunPod con puerto 8188 expuesto).
- Al final podés ver y descargar el video.

### Línea de comandos

```bash
# Generar video desde un tema
python -m src.pipeline --tema "Historia de la inteligencia artificial"

# O desde un guion existente
python -m src.pipeline --guion mi_guion.txt
```

## Tests

```bash
pip install -r requirements.txt   # incluye pytest y pytest-timeout
pytest tests/ -v                   # todos los tests
pytest tests/test_image_generator.py -v   # solo tests unitarios (sin ComfyUI)
pytest tests/test_comfyui_integration.py -v   # conectividad y 1 imagen real (requiere ComfyUI)
```

- **Unitarios** (`test_image_generator.py`): workflow, checkpoint, timeouts, mocks de HTTP; no necesitan ComfyUI.
- **Integración** (`test_comfyui_integration.py`): comprueban que ComfyUI responde en `COMFYUI_URL` y, opcionalmente, generan una imagen (puede tardar 1–3 min).

## Estructura del proyecto

- `config/` — Biblia visual, estilo base y plantillas
- `tests/` — Tests unitarios y de integración con ComfyUI
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
