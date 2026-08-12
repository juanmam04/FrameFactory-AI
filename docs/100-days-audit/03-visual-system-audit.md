# 03 — Auditoría del motor visual

## Principio

No generar imágenes internamente **≠** tirar inteligencia narrativa.  
Clasificación orientada a: Google Flow genera; FrameFactory dirige, importa y monta.

## Inventario y clasificación

| Pieza | Path | Clasificación | Motivo |
|-------|------|---------------|--------|
| `visual_beats.py` | beats action/location/camera | **KEEP / ADAPT** | Shot intelligence pre-imagen |
| `frame_director.py` + `frame_spec.py` | VisualBeat → FrameSpec | **ADAPT** | Base de shot list / Flow Pack |
| `frame_prompt_builder.py` | FrameSpec → prompt | **ADAPT** | Texto para Flow (sin llamar gen) |
| `scene_visual_intent.py` | B-roll text por bloque SaaS | **KEEP / ADAPT** | Brief por escena ya en producto |
| `saas_edit_planner.py` | motion/transition/B-roll hints | **KEEP** | Montaje, no gen |
| `scene_splitter.py` | escenas con duración | **KEEP** | Timeline |
| `scene_planner.py` | bloques SaaS | **ADAPT** | Evitar chunks de 12 palabras para docu |
| `prompt_builder.py` + `storyboard_continuity.py` | continuidad V1 | **DEPRECATE** (path producto); **ADAPT** selectivo | Duplica V2; útil en tests |
| `scene_visual_mapper.py` / `visual_story_mapper.py` / `action_scene.py` | heurísticas meta | **ADAPT** parcial | Characters/location guess → Story Bible seed |
| `location_visual_enrichment.py` | enriquece locations | **ADAPT** | Útil en pack de refs |
| `image_generator.py` | Replicate/Comfy/DALL·E | **DEPRECATE** del path principal | Flow reemplaza |
| `generar_imagen_apoyo_replicate` | B-roll SaaS | **DEPRECATE** | Sustituir por import |
| `frame_image_pipeline.py` | multi-intento gen | **DELETE LATER** | Solo gen local |
| `frame_validator.py` / `frame_regenerator.py` | VLM QA post-gen | **ADAPT** opcional / **DELETE LATER** | QA post-Flow si se quiere |
| `kontext_prompt.py` | FLUX Kontext | **DELETE LATER** | Específico Replicate |
| `regeneration.py` | regen escenas desde prompts JSON | **DEPRECATE** UI; scripts | |
| `scene_descriptions.py` | LLM desc visual | **DEPRECATE** | Path viejo |
| `catalog_service.py` + assets PNG | personaje/fondo fijos | **ADAPT** | Fallback o no usar en docu stills |
| `character_video_provider.py` | compose clip | **ADAPT** | Aceptar still Flow como full-frame |
| `gameplay_background_service.py` | video fondo | **KEEP** | Formato distinto (shorts); no path docu |
| `video_assembler.py` | slideshow + audio | **KEEP** | Ideal docu stills |
| `config/visual_bible.yaml` | style lock | **ADAPT** → `global-style.txt` Flow | |
| `config/character_bible.yaml` | presets | **ADAPT** | No es cast dinámico |
| `config/visual_motifs.yaml` | motivos | **DEPRECATE** con V1 | |
| `character_reference/*.png` | identity sheets | **ADAPT** como refs humanas a Flow / **DEPRECATE** gen | |
| `workflows/comfyui_*` | stickman | **DELETE LATER** | |
| `video_replicate.py` | Veo | **DELETE LATER** | Orphan |
| `scripts/runpod_batch_comfyui.py` | batch `0001.png` | **ADAPT** naming idea | Precedente numeración |

## Continuidad y memoria visual

| Concepto | Existe? | Evidencia |
|----------|---------|-----------|
| StoryboardState / CharacterStateStore | Sí (V1) | `storyboard_continuity.py` |
| Seeds deterministas | Sí | tests `test_seed_determinism.py` |
| Previous-frame reference | En gen Kontext/Comfy | `image_generator` |
| Visual memory persistente cross-video | No | — |
| Asociación imagen↔escena estable | Clásico `escena_XXXX.png`; SaaS `saas_support_XXXX.png` | CONFIRMED |

## Recomendación

1. **Conservar** como “Visual Director”: beats → FrameSpec → prompt text → Flow Pack.  
2. **Desconectar** llamadas a `generar_imagen*` del path diario.  
3. **No borrar** todavía el stack gen (DELETE LATER tras Video 30+).  
4. Para Video 1: mínimo es **prompts numerados** + **import PNG**; no hace falta portar todo V2.
