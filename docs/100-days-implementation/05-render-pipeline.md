# 05 — Render pipeline

1. **Voice:** single continuous `generar_voz` → `audio/narration.mp3` (not 100+ Reddit chunks).  
2. **Preview:** missing images, voice presence, avg still length warnings.  
3. **Assemble:** `montar_video(..., transiciones_suaves=True, output_path=render/final.mp4, music_volume≈0.12)`.  
4. Prior `final.mp4` renamed to `final_backup_<timestamp>.mp4`.  
5. Errors appended to `logs/pipeline.log` and `logs/render.log`.

Resolution: 1920×1080. Music stays under narration (volume parameter; not true sidechain ducking yet).
