# 09 — Voz, timeline, render

## Voice (`voice_service.generate_project_voice`)

| | |
|--|--|
| Provider | ElevenLabs si key; else OpenAI TTS (`voice_generator.generar_voz`) |
| Model EL | `eleven_multilingual_v2` |
| Model OpenAI | `OPENAI_TTS_MODEL` default `tts-1-hd` |
| Chunks | >5000 chars EL / >4000 OpenAI → concat FFmpeg |
| Calls | **1 narración continua** (full script) |
| Speed | `project.voice_speed` default 1.0 |
| Output | `projects/<id>/audio/narration.mp3` |
| Also writes | `output/audio/doc_<id>_narration.mp3` (global) |
| Duration | ffprobe → `project.voice.duration_sec` |
| Checkpoint | `voice_ready`; clears assembly/render |
| Errors | RuntimeError si no API keys (no empty file) |

**No timestamps** por frase/shot para sync.

---

## Timeline / assembly

**Función:** `assemble_service.assemble_and_render`

### Transformación

```text
script (approved, already in voice file)
+ ordered images from shot-list (001.png…)
+ narration.mp3
→ montar_video(...)
→ render/final.mp4
```

### Duración por imagen

```python
sec = voice_duration_sec / len(images)
sec = clamp(sec, 2.5, 20.0)
```

**Uniforme** — no varía por shot individual.

### Ejemplo: 60 imágenes, 10:00 narration

- sec = 600/60 = **10s por imagen** (todas iguales)
- No hay shot de 3s vs 15s — eso **no existe** hoy

Si imágenes < narration duration: `montar_video` **extiende** video (loop last frame) to match audio.

Si video > audio: trimmed to audio duration at mux step.

---

## Movimiento (CONFIRMED `montar_video`)

Documentary llama `transiciones_suaves=True`:

- **Ken Burns:** zoompan 1.0→1.06 per still
- **Fade in** between clips (fade out disabled to avoid black extend bug)
- Scale/crop to 1920×1080
- **No pan** lateral explícito
- **No** random movement
- Fallback to static if zoom filter fails

---

## Music

| | |
|--|--|
| Source 1 | `project.music_path` if file exists |
| Source 2 | `BACKGROUND_MUSIC_PATH` from .env via `get_background_music_path()` |
| Volume | `project.music_volume` default 0.12 (UI slider 0–0.4) |
| Mix | FFmpeg amix: voice volume=1, music=music_volume |
| Ducking | **No sidechain** — fixed low music level |
| Loop | no explicit loop — amix duration=first |

---

## Subtitles

**Documentary:** `subtitles_enabled: true` in project.json schema but **NOT used** in assemble path.

`montar_video` supports `subtitles_path` + ASS — **not passed** from Documentary.

**Reusable infra:** `saas_subtitles.py` (ASS from block audios) — designed for per-block SaaS, would need adapt for single narration + shot timing or SRT from script.

---

## Render output

| | |
|--|--|
| Path | `projects/<id>/render/final.mp4` |
| Backup | prior final → `final_backup_<timestamp>.mp4` |
| Codec | libx264 CRF 23, AAC 192k |
| Resolution | 1920×1080 |
| FPS | 24 (zoom path) |
| Logs | `logs/render.log`, `logs/pipeline.log` |
| Checkpoints | assembly_ready + render_ready |
| Preview | `build_preview` JSON before render |

### Failure

Exception → log FAIL, checkpoint not set on failure path (assembly/render stay false if never succeeded).

---

## Metadata / thumbnail (Documentary)

**NO existe** en pipeline Documentary.

Studio Review tiene `reddit_publication_bundle` — **no conectado** a Documentary projects.
