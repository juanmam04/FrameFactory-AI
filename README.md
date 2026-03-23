# FrameFactory-AI

Sistema automático de creación de videos con IA. Genera videos largos a partir de un guion: escenas visuales, voz sintética, edición automática y exportación final.

## Requisitos

- **Python 3.10+**
- **FFmpeg** instalado en el sistema
- **Stable Diffusion** (Automatic1111 o ComfyUI) en local o en la nube (ej. RunPod)
- APIs: modelo de lenguaje (OpenAI/Claude/etc.) y voz IA (ElevenLabs/OpenAI TTS/etc.)

## Instalación.

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
pytest tests/ -v                   # todos los tests (falla si algún módulo legacy tiene import roto)
pytest tests/unit/test_continuity_units.py tests/integration/test_prompt_pipeline_integration.py tests/test_regression_prompt_pipeline.py tests/test_golden_prompt_pipeline.py tests/test_seed_determinism.py tests/test_action_scene.py tests/test_kontext_prompt.py tests/test_location_visual_enrichment.py -v
pytest tests/test_image_generator.py -v   # ComfyUI mocks
pytest tests/test_comfyui_integration.py -v   # requiere ComfyUI real
```

### Verificación del pipeline de prompts (sin modelo de imagen)

- **Unitarios** (`tests/unit/test_continuity_units.py`): `resolve_location`, `resolve_camera`, personaje, `sanitize_symbolic_elements`, `update_storyboard_state`.
- **Integración** (`tests/integration/test_prompt_pipeline_integration.py`): casos A/B/C + escritura JSON en modo debug.
- **Regresión** (`tests/test_regression_prompt_pipeline.py`): cámara final vs `camera_priority`; `beat.location` vs plantilla.
- **Acción automática** (`src/action_scene.py` + `tests/test_action_scene.py`): si el beat describe movimiento/interacción (keywords ES/EN), el pipeline fuerza `full_body_action`, sustituye `empty_room_tension` por `dynamic_interaction` / `group_interaction` y añade bloques ACTION REQUIREMENT + COMPOSITION RULES al prompt.
- **Golden / snapshots** (`tests/test_golden_prompt_pipeline.py` + `tests/fixtures/golden/*.json`): comparación byte-a-byte del JSON serializado. Tras un cambio **intencional** en `visual_bible.yaml` o en el ensamblado de prompts, regenerá fixtures con:
  - `python scripts/update_prompt_goldens.py`
  - o `set UPDATE_PROMPT_GOLDENS=1` (Windows) / `export UPDATE_PROMPT_GOLDENS=1` (Unix) y `pytest tests/test_golden_prompt_pipeline.py -v` (los tests se saltan tras reescribir).
- **Semillas** (`tests/test_seed_determinism.py`): `comfyui_seed_from_material` y `seed_material` estable entre corridas.

**Modo debug obligatorio (auditoría por escena):**

- Variable de entorno `PROMPT_PIPELINE_DEBUG_DIR=ruta/carpeta` **o** argumento `debug_output_dir=` en `prompts_para_beats(...)`.
- Por cada beat se escribe `scene_XXXX.json` con: `beat`, `base_meta`, `enriched_meta`, `resolved_context`, `prompt_final`, `state_before`, `state_after`.

**Resultado esperado** al correr el paquete de prompts: `35 passed` (revisá con `pytest ... --collect-only -q`).

**Fuera de alcance de tests automáticos:** salida visual del checkpoint SD/FLUX, políticas de seguridad del proveedor, latencia/red, calidad subjetiva, sincronización exacta de audio/video en FFmpeg.

Además: **`test_image_generator.py`** (mocks ComfyUI) y **`test_comfyui_integration.py`** (servidor ComfyUI real, opcional).

## Continuidad entre escenas (prompts)

El pipeline usa `src/storyboard_continuity.py`: estado `StoryboardState` por proyecto, herencia de `beat.location`, bloque **CONTINUITY** en el prompt, cámara resuelta (incluye mapeo desde `beat.camera_type`), filtro de overlay simbólico incompatible con exteriores, y semilla estable en **ComfyUI** cuando hay `seed_material` (tupla de 5 elementos al generar lote). Tests: `tests/unit/`, `tests/integration/test_prompt_pipeline_integration.py`, `tests/test_*prompt*`.

Las **locaciones abstractas o con nombres ficticios** (p. ej. “Campo de Arkenvale”) se enriquecen en `src/location_visual_enrichment.py` con una descripción visual concreta **sin quitar el nombre** (`nombre — descripción en inglés para el prompt`). Con `OPENAI_API_KEY` se usa el modelo de chat configurado; sin API, hay respaldo heurístico. Desactivar LLM: `LOCATION_VISUAL_ENRICH_LLM=0`.

## Referencia del personaje (Replicate / Kontext)

Texto→imagen por defecto: **`black-forest-labs/flux-dev`** (configurable con `REPLICATE_IMAGE_MODEL` o `REPLICATE_FLUX_MODEL`). Imagen+texto: **`black-forest-labs/flux-kontext-dev`** (`REPLICATE_IMAGE_MODEL_WITH_REF`).

Colocá una PNG del protagonista en  
`references/character_reference/character_reference_front.png`  
(ver `references/character_reference/README.md`). En `config/visual_bible.yaml`, `character_reference.front` debe apuntar a ese archivo. **Todas las escenas** usan ese archivo como `input_image` en Kontext (prioridad `front` para máxima consistencia). Si declarás rutas en `character_reference` pero falta el archivo, la generación falla salvo que pongas `REPLICATE_FORCE_KONTEXT=0` (solo entonces se usa el modelo solo texto). Opcional: `REPLICATE_FLUX_DEV_STEPS`, `REPLICATE_FLUX_DEV_GUIDANCE`.

**`CHARACTER_REFERENCE_MODE`** (default `identity_sheet`): con una ficha sobre fondo neutro, Kontext recibe un bloque extra en el prompt para **no copiar** pose centrada ni fondo de estudio—solo anclar identidad. Si tu PNG ya es una escena con entorno, probá `scene_reference` para omitir ese bloque (ensamblado en `src/kontext_prompt.py`).

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
