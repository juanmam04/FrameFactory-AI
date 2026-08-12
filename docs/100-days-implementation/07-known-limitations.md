# 07 — Known limitations

- No automated research / fact agent  
- Story bible is light (heuristic or one LLM JSON call)  
- Flow copy relies on selecting `st.code` (no native clipboard component)  
- Keyboard shortcuts not implemented (buttons only)  
- Subtitles burn not wired in documentary assemble yet (can add post-Video 1)  
- Music “ducking” = low fixed volume, not sidechain  
- Ken Burns may fall back to static if FFmpeg filter fails  
- LLM script still needs human fact approval  
- Shot count heuristic (~words/24), not editorially perfect  
- Classic SaaS modes untouched; don’t mix with Documentary workspace  

Open P0-ish residual: deeper resume mid-TTS/render (checkpoints cover stages, not mid-loop frames).
