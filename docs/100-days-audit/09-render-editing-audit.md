# 09 — Edición y render

## Dos renderers

### A) Clásico — `video_assembler.montar_video` (CONFIRMED)

| Parámetro | Valor default |
|-----------|---------------|
| Resolución | 1920×1080 |
| FPS | 24 |
| Video | libx264 CRF 23 |
| Audio | AAC 192k |
| Ken Burns | `zoompan` 1.0→1.06 + fades **solo si** `transiciones_suaves=True` |
| Uso en `pipeline.run` | **no** pasa el flag → montaje **estático** por defecto |
| Música | `volume=0.2` + `amix` — **sin ducking** |
| Subtítulos | filtro `subtitles=` opcional |
| Fallback | video negro / estático si zoom falla |

**Ajuste al formato docu (narración + stills + motion):** **alto** — es el renderer natural. Activar `transiciones_suaves=True` para Ken Burns ligero.

### B) SaaS MVP — clips por bloque (CONFIRMED)

| Pieza | Detalle |
|-------|---------|
| Compose | `character_video_provider.render_block` |
| Motion | `static` \| `slow_push` (via `saas_edit_planner`) |
| Transiciones | `none` \| `fade` |
| Res típica | 1280×720; gameplay 1920×1080 o 1080×1920 |
| FPS | 24 / 30 gameplay |
| Concat | `-c copy` (frágil si codecs difieren) |
| Subs | ASS burn (`saas_subtitles`) |
| Música/SFX | post-mix; fallos omitidos (warning) |
| Intro/outro | no dedicado |
| Hardware accel | no explícito (libx264 software) |

## Qué falta para calidad documental

- Ducking voz/música (sidechain)  
- Capítulos visuales / lower-thirds opcionales (overlay parcial existe en gameplay)  
- Workspace por proyecto  
- Import stills full-bleed sin personaje catálogo  
- Resume mid-render  

## Veredicto

Para **narración + imágenes estáticas + movimiento suave**, el stack FFmpeg actual es **suficiente** si se usa el path clásico (o MVP adaptado) **sin** depender de Replicate/HeyGen.  
No hace falta un NLE nuevo para Video 1–10.
