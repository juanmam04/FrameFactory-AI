# 01 — Mapa del repositorio

## Estructura top-level (CONFIRMED)

| Ruta | Propósito |
|------|-----------|
| `src/` | Núcleo Python (44 módulos + `saas_platform/`) |
| `web/` | FastAPI SaaS (auth, SQLite, jobs → `run_saas_mvp`) |
| `backend/` | Express/Node legacy ComfyUI + render (desacoplado del producto Python) |
| `config/` | YAML: plantillas guion, visual bible, subtítulos, instrucciones LLM |
| `assets/` | Catálogo SaaS: characters, backgrounds, audio YouTube-safe |
| `character_reference/` + `references/` | Refs de personaje / outfits (duplicación estructural) |
| `output/` | Artefactos runtime (guiones, audio, clips, JSON SaaS) |
| `scripts/` | Smoke, e2e, RunPod, regeneración |
| `tests/` | Pytest oficial (`pytest.ini`) |
| `test/` | Fixtures manuales (no es path de pytest) |
| `workflows/` | ComfyUI stickman LoRA |
| `docs/` | Doc RunPod + esta auditoría |
| `app.py` / `run.sh` / `package.json` | Entrada Streamlit (`npm run dev` → `./run.sh`) |
| `venv/` + `.venv/` | Dos entornos virtuales |

## Entry points (CONFIRMED)

```
Streamlit:  app.py → saas_ui.render_app()
Shell/npm:  run.sh / npm run dev → streamlit run app.py
CLI clásico: python -m src.pipeline --tema|--guion → pipeline.run()
CLI default sin args: run_saas_mvp("Why most people…")
FastAPI:    uvicorn web.main:app → render_worker → run_saas_mvp(workspace_subdir=job_*)
Node:       backend/server.js → /api/ai, /api/video (aislado)
```

## Call graph — producto vivo

```
saas_ui.page_create / page_rendering
  └─ _run_mvp_thread
       └─ pipeline.run_saas_mvp
            ├─ saas_viral_idea_engine (opcional)
            ├─ catalog_service (character/background/voice)
            ├─ script_generator.generar_guion
            ├─ scene_planner.plan_scenes | plan_scenes_reddit_segments
            ├─ saas_edit_planner.annotate_blocks_with_editing
            ├─ scene_visual_intent.enrich_blocks_with_visual_intent (reddit)
            ├─ reddit_publication_bundle.generar_bundle_publicacion_youtube
            ├─ por bloque:
            │    voice_generator.generar_voz
            │    image_generator.generar_imagen_apoyo_replicate (opcional)
            │    character_video_provider.render_block
            │      | gameplay_background_service.render_gameplay_block_clip
            ├─ ffmpeg concat → final.mp4
            ├─ saas_subtitles (+ burn)
            └─ _saas_post_mix_ambient + saas_full_package
```

## Call graph — pipeline clásico (CLI)

```
pipeline.run
  ├─ script_generator.generar_guion | leer guion
  ├─ scene_splitter.dividir_en_escenas
  ├─ visual_beats.generar_beats_para_escenas
  ├─ frame_director.beats_a_frame_specs
  ├─ frame_prompt_builder.prompt_desde_frame_spec
  ├─ frame_image_pipeline.generar_imagenes_desde_frame_specs  (o skip → escena_*.png)
  ├─ voice_generator.generar_voz (una narración)
  ├─ video_assembler.montar_video
  ├─ metadata_youtube.generar_metadata_completa
  └─ history.guardar_en_historial
```

## Servicios externos (CONFIRMED vía código / `.env.example`)

| Servicio | Uso |
|----------|-----|
| OpenAI | Guion, TTS fallback, metadata, VLM validator, planners, chat perfil |
| ElevenLabs | TTS principal |
| Replicate | FLUX / Kontext imágenes; módulo Veo huérfano (`video_replicate.py`) |
| ComfyUI | Gen local / RunPod |
| HeyGen / CHARACTER_ANIMATOR_* | Avatar opcional en clips |
| FFmpeg/ffprobe | Montaje, velocidad voz, subtítulos, gameplay |
| SQLite | `web/database.py` → `data/framefactory.db` (se crea al usar web) |

**No encontrado:** Stripe real, Anthropic/Claude, Google Flow.

## Storage runtime (CONFIRMED)

- Clásico: `output/guiones/`, `imagenes/<proy>/escena_XXXX.png`, `audio/`, `videos/`, `metadata/`, `historial.json`
- SaaS Studio: `output/saas_projects.json`, `saas_sessions.json`, `final.mp4`, `clip_*.mp4`, `saas_support_*.png`, `.saas_render_progress.json`, bundles JSON
- Web jobs: `output/job_<id>/` vía `workspace_subdir`
- Node: `backend/outputs/jobs/`

## Código abandonado / lateral (CONFIRMED)

| Ítem | Evidencia |
|------|-----------|
| `backend/` Express | No importado por `web/` ni `saas_ui` |
| `title_generator.py` | Cero importadores |
| `video_replicate.py` | Cero importadores |
| Dual path prompts V1 (`prompt_builder`/`storyboard_continuity`) vs V2 (`frame_*`) | V2 en `run`; V1 en tests/e2e |
| `SETUP.md` menciona SD/HF/Pollinations | Desfasado vs `.env.example` |
| Stickman LoRA (`workflows/`, docs RunPod) | Camino paralelo experimental |
| DALL·E en `image_generator` | Código presente, ruta deshabilitada |

## Frontend

- **UI principal:** Streamlit `saas_ui` (Dashboard, Create, Rendering, Library, Review, Profile).
- **Web FastAPI:** templates/static en `web/` (plataforma con billing por tokens internos).
- **No hay** frontend React/Next en la raíz (solo `package.json` wrapper).
