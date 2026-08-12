# 01 — Cómo funciona FrameFactory (entry point + arquitectura)

## Entry point (CONFIRMED)

| Comando | Archivo | Resultado |
|---------|---------|-----------|
| `./run.sh` | `run.sh` | Activa venv → `streamlit run app.py` |
| `npm run dev` | `package.json` | Wrapper de `./run.sh` |
| `streamlit run app.py` | directo | Igual |

**Entrypoint Python:** `app.py` → `from src.saas_ui import render_app; render_app()`

## UI que se abre

**Streamlit** — título página: `FrameFactory Studio` (`saas_ui.render_app`, `st.set_page_config`).

### Sidebar (CONFIRMED `_nav()`)

1. **Sesión de trabajo** — selectbox + renombrar + **Nueva sesión**
2. Nav buttons:
   - Inicio (Dashboard)
   - **Documentary** ← MVP 100 days
   - Nuevo video (Create) ← Studio legacy
   - Biblioteca
   - Render
   - Revisar
   - Perfil

### Modos

| Modo | Nav key | Módulo | Propósito |
|------|---------|--------|-----------|
| Dashboard | `Dashboard` | `page_dashboard` | Lista proyectos SaaS JSON |
| **Documentary** | `Documentary` | `documentary_ui.page_documentary` | Pipeline 100 days |
| Create | `Create` | `page_create` | Wizard 3 pasos → `run_saas_mvp` |
| Library | `Library` | `page_library` | Proyectos SaaS |
| Rendering | `Rendering` | `page_rendering` | Progreso MVP SaaS |
| Review | `Review` | `page_review` | Bundle publicación Reddit |
| Profile | `Profile` | `page_profile` | Creative profile + chat |

## Documentary vs Studio

| | Documentary | Studio (Nuevo video) |
|--|-------------|----------------------|
| Workspace | `projects/<id>/` | `output/` compartido |
| Imágenes | Flow manual import | Replicate / catálogo / gameplay |
| Guion plantilla | `business_documentary_en` | `reddit_stories` / `explicativo` |
| Voz | 1 narración continua | TTS por bloque (Reddit) |
| Montaje | `montar_video` stills | `character_video_provider` clips |
| Sesión/perfil | **No usa** | Usa creative_profile + session_context |
| Checkpoints | `project.json` | `.saas_render_progress.json` |

## Arquitectura interna Documentary

```
documentary_ui.py (Streamlit)
  → documentary/project.py          (workspace, checkpoints)
  → documentary/script_service.py   → script_generator.generar_guion
  → documentary/visual_director.py  → scene_splitter, visual_beats, frame_director, frame_prompt_builder
  → documentary/story_bible.py      → OpenAI JSON o heurística
  → documentary/flow_pack.py          → export disk + shot-list.json
  → documentary/import_images.py
  → documentary/voice_service.py      → voice_generator.generar_voz
  → documentary/assemble_service.py   → video_assembler.montar_video
```

## Otros entry points (no UI principal)

- `python -m src.pipeline` — pipeline clásico CLI
- `uvicorn web.main:app` — FastAPI SaaS (jobs → `run_saas_mvp`)
- `backend/server.js` — Node legacy (aislado)
