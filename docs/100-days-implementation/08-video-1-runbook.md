# 08 — Video 1 runbook

## Prerequisites

1. `cp .env.example .env` and set **your** `OPENAI_API_KEY` + ElevenLabs or OpenAI TTS.  
2. FFmpeg installed (`ffmpeg -version`).  
3. Google Flow account (manual).  
4. Rotate any keys that were ever committed in old `.env.example` (FF100-P0-008).

## Run FrameFactory

```bash
cd /Users/juanmamartinez/FrameFactory-AI
./run.sh
# or: npm run dev
```

Sidebar → **Documentary**.

## Produce Video 1

1. **Create project** — topic e.g. your Day 1 story; paste research notes + sources; target ~1500 words.  
2. **Script** — Generate (LLM) or paste your own → edit → complete fact checklist → **Approve script**.  
3. **Flow Pack** — Generate Flow Pack. Open **Flow Workspace**.  
4. Generate **master references** in Flow first (CHAR/LOC/OBJ).  
5. Work **batch by batch** (10 shots): copy prompt → Flow → download as `001.png`…  
6. Put files in `projects/<id>/flow-import/` (or any folder).  
7. **Images** → Bulk import → fix missing → Replace individual shots as needed.  
8. **Voice & Render** → Generate voice → Preview → Assemble + Render.  
9. Output: `projects/<id>/render/final.mp4`.  
10. Upload to YouTube manually (title/description still mostly manual for Video 1).

## Offline structure check

```bash
venv/bin/python scripts/dogfood_100_days_test.py
```

Creates `projects/100-days-test/` with dummy stills (not publishable).
