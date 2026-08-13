# 07 — Video 1/100 runbook

## Start

```bash
# on branch feature/100-days-daily-workflow
./run.sh
# or: streamlit run app.py
```

1. Confirm session **100 Days — Business Documentaries** is active (auto-seeded).
2. Home → **CREATE TODAY'S VIDEO**
3. **Generate** ideas (or offline mocks if no API) → **Choose**
4. Paste real research notes + sources → Continue to Script
5. **Generate script** → fact-check → **Approve script** (builds Flow)
6. Flow → create master refs in Google Flow → generate stills as `001.png`…
7. Images → import folder
8. Voice → Generate voice
9. Render → Render video
10. Output: `projects/<id>/render/final.mp4`

Keys needed for real Video 1: `OPENAI_API_KEY`, TTS (`ELEVENLABS_*` or OpenAI TTS), FFmpeg.
