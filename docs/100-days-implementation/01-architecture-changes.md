# 01 — Architecture changes

## Added

- `src/documentary/` — project workspace, script, visual director, story bible, flow pack, import, voice, assemble
- `src/documentary_ui.py` — Streamlit **Documentary** nav page
- `projects/<id>/` — isolated workspaces (FF100-P0-001)
- Plantilla `business_documentary_en` in `config/plantillas_guion.yaml`
- `tests/test_documentary_mvp.py`, `scripts/dogfood_100_days_test.py`
- `docs/100-days-implementation/`

## Modified (minimal)

- `src/saas_ui.py` — nav entry Documentary
- `src/script_generator.py` — documentary plantilla without POV/Reddit inheritance
- `src/voice_generator.py` — fail-fast if no TTS API (FF100-P0-007)
- `src/video_assembler.py` — `output_path`, `music_volume`
- `.env.example` — placeholders only (FF100-P0-008)

## Not changed / preserved

- Classic `pipeline.run`, SaaS `run_saas_mvp`, Replicate/ComfyUI stacks (unused by Documentary path)
- No Flow automation, no new image generator, no YouTube upload

## Workspace layout

```text
projects/<id>/
  project.json          # checkpoints + metadata
  script/
  flow-pack/
  images/               # 001.png …
  audio/narration.mp3
  render/final.mp4
  metadata/
  logs/
```
