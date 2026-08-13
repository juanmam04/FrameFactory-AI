# 02 — Pipeline actual (reconstruido desde código)

## Qué pipeline usa realmente el usuario

**CONFIRMED:** al abrir Studio (`streamlit run app.py`) el único motor de render es `run_saas_mvp`.  
El pipeline largo `pipeline.run` **no** se invoca desde la UI.

---

## Flujo A — Studio SaaS (producto)

### 1. Creación de proyecto
- **Archivos:** `saas_ui._append_project`, `output/saas_projects.json`
- **Función:** al pulsar “Generar video” se crea `id` timestamp y status `rendering`
- **Estado:** funciona; índice JSON simple
- **Incompleto:** no hay workspace de archivos por proyecto en Studio

### 2. Entrada del tema
- **UI:** `page_create` paso 1 — `create_topic`, `create_twist`, ideas IA, auto-paquete
- **Output:** string combinado `_build_video_topic()`
- **Depende de imágenes:** no

### 3. Investigación
- **Estado:** **NO EXISTE** módulo de research / fuentes / web search  
- **CONFIRMED** por ausencia en `src/` y flujo de `generar_guion`

### 4. Generación del guion
- **Función:** `script_generator.generar_guion`
- **Modelo:** `OPENAI_MODEL` default `gpt-4o-mini`
- **Plantilla SaaS:** `reddit_stories` si reddit/gameplay/auto; else `explicativo`
- **Input:** tema + `target_words` + `creative_context`
- **Output:** texto + word_count + mins
- **Longitud:** clamp 80–10000; 2 pasos draft/adjust
- **Duplicado:** ideas virales también generan brief (`saas_viral_idea_engine`)
- **Imágenes:** no depende

### 5–6. Procesamiento / escenas (bloques)
- **Reddit:** `plan_scenes_reddit_segments` (~12 palabras/segmento) — CONFIRMED `scene_planner.py`
- **Normal:** `plan_scenes` (split por `.!?`)
- **Output:** `[{id, text}, ...]`
- **Problema para 8–12 min:** Reddit → demasiados bloques (ver P0-006)

### 7. Visual beats (clásico)
- **En SaaS:** **NO** se llama `visual_beats`
- **Sustituto SaaS:** `saas_edit_planner.annotate_blocks_with_editing` + opcional `scene_visual_intent`

### 8. Prompts visuales
- **SaaS apoyo:** `_saas_support_image_prompt(block)` texto corto → Replicate
- **Clásico:** `frame_prompt_builder.prompt_desde_frame_spec`
- **Estado SaaS:** prompts débiles vs stack V2

### 9. Generación de imágenes
- **SaaS:** `generar_imagen_apoyo_replicate` si no `skip_support_images` y no gameplay
- **Env kill-switch:** `SAAS_SKIP_SUPPORT_IMAGES`
- **Clásico:** `frame_image_pipeline` multi-intento + validator
- **Para Flow:** este paso debe volverse **manual externo**

### 10. Audio
- **SaaS:** `generar_voz` **por bloque** → `output/audio/saas_mvp_*.mp3`
- **Velocidad:** `voice_speed` + FFmpeg atempo
- **Sync:** duración clip = duración audio — **fuerte**

### 11. Timings
- **SaaS:** implícitos por duración de cada MP3 (`ffprobe` / fallback tamaño)
- **Clásico:** `Escena.duracion_segundos` heurística; video se extiende al audio total

### 12–16. Montaje / subtítulos / música / render
- Clips: `character_video_provider.render_block` (FFmpeg layers, zoom `slow_push`, fades) o gameplay
- Concat: `ffmpeg -f concat -c copy`
- Subs: `saas_subtitles.write_ass_from_block_audios` + burn
- Música/SFX: `_saas_post_mix_ambient` (amix, **sin ducking**)
- Output: `output/final.mp4` (o `*_subburn.mp4` / `*_audio.mp4`)

### 17–19. Thumbnail / metadata / exportación
- `reddit_publication_bundle` → título, alt titles, description, thumbnail **prompt** (no PNG)
- Review UI muestra bundle
- **No** hay upload a YouTube automatizado

---

## Flujo B — Pipeline clásico CLI

| Paso | Función | Estado |
|------|---------|--------|
| Tema/guion | `generar_guion` / archivo | OK |
| Escenas | `dividir_en_escenas` | OK |
| Beats | `generar_beats_para_escenas` | OK |
| FrameSpec | `beats_a_frame_specs` | OK |
| Imágenes | `generar_imagenes_desde_frame_specs` o `skip_imagenes` + `escena_*.png` | Gen local; **import manual posible** |
| Voz | una pista | OK |
| Montaje | `montar_video` | OK para stills |
| Metadata | `generar_metadata_completa` | Parcial (thumbnail None) |

**Importancia para Flow:** `skip_imagenes=True` + carpeta `escena_0001.png`… es el **precedente más cercano** a import Flow (CONFIRMED `pipeline.run` L249).

---

## Matriz rápida: ¿depende de gen de imágenes interna?

| Paso | SaaS | Clásico |
|------|------|---------|
| Guion | No | No |
| Bloques/escenas | No | No |
| Beats/FrameSpec | N/A / No en SaaS | No (pre-gen) |
| Clip render | Opcional B-roll | Sí (salvo skip) |
| Voz | No | No |
| Montaje final | No (usa assets) | Sí lista PNG |
| Metadata | No | No |

---

## Duplicaciones relevantes

1. Dos orquestadores: `run` vs `run_saas_mvp`
2. Dos stacks de prompts: V1 continuity vs V2 FrameSpec
3. Dos paquetes YT: `metadata_youtube` vs `reddit_publication_bundle`
4. Dos UIs: Streamlit Studio vs FastAPI web
