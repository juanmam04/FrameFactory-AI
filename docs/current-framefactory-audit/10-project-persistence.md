# 10 — Project persistence

## Root

`projects/<project_id>/`

Ejemplo real: `projects/100-days-test/`

## project.json — schema REAL (CONFIRMED)

Ver `projects/100-days-test/project.json` en repo.

### Campos core

| Field | Type | Purpose |
|-------|------|---------|
| `id` | string | e.g. `001-wework`, `100-days-test` |
| `slug` | string | slugified title |
| `mode` | string | always `"documentary"` |
| `title` | string | |
| `topic` | string | story subject |
| `language` | string | `"en"` |
| `target_words` | int | default 1500 |
| `target_duration_min` | [8,12] | informational |
| `research_notes` | string | |
| `sources` | string[] | |
| `script` | string | full narration |
| `fact_check_status` | pending/approved/needs_fixes | |
| `script_approved` | bool | gate for Flow Pack |
| `voice_speed` | float | default 1.0 |
| `music_path` | string | optional |
| `music_volume` | float | default 0.12 |
| `subtitles_enabled` | bool | **unused in render** |
| `batch_size` | int | default 10 |
| `flow_shot_index` | int | UI resume position |
| `flow_batch_index` | int | reserved |
| `checkpoints` | object | see below |
| `import_report` | object | last bulk import |
| `preview` | object | last preview checks |
| `visual_analysis` | object | shot_count, path |
| `flow_pack` | object | shot_count, batch_size |
| `voice` | object | path, duration_sec, speed |
| `render` | object | path, seconds_per_image |
| `errors` | array | |
| `created_at`, `updated_at` | ISO UTC | |

### Checkpoints

```json
{
  "script_ready": true,
  "flow_pack_ready": true,
  "images_imported": true,
  "voice_ready": true,
  "assembly_ready": true,
  "render_ready": true
}
```

### Resume capability

| Close/reopen | Works? |
|--------------|--------|
| project.json | ✅ full state |
| script on disk | ✅ script/script.txt |
| flow pack | ✅ flow-pack/* |
| images | ✅ images/*.png |
| voice | ✅ audio/narration.mp3 |
| flow shot index | ✅ flow_shot_index |
| mid-LLM call | ❌ no — restart step |
| mid-FFmpeg | ❌ partial files possible |

**Session Streamlit** separate from project — documentary state is project-centric (good).

## Directory layout

```text
projects/<id>/
  project.json
  script/script.txt, script_meta.json, research_notes.md, fact_checklist.md
  flow-pack/...
  flow-import/          (convention, user-created)
  images/001.png...
  audio/narration.mp3
  render/final.mp4
  metadata/             (created empty, unused)
  logs/pipeline.log, render.log
```
