# 08 — Auditoría de voz

## Proveedor y modelo (CONFIRMED)

| | |
|--|--|
| Primario | ElevenLabs `eleven_multilingual_v2` si hay API key |
| Fallback | OpenAI TTS (`OPENAI_TTS_MODEL` default `tts-1-hd`) |
| Forzar EL | `ELEVENLABS_SOLO` |
| Catálogo SaaS | puede forzar OpenAI (`pref_openai`) o voice_id EL |
| Archivo | `src/voice_generator.py::generar_voz` |
| Storage | `output/audio/{nombre}.mp3` |

## Chunking / retries / velocidad

- EL: split >5000 chars; concat FFmpeg  
- OpenAI: split >4000 chars  
- Velocidad: FFmpeg `atempo` 0.5–2.0 (SaaS `voice_speed`)  
- Sin API: **escribe archivo vacío y retorna** — FF100-P0-007  
- Si FFmpeg falta en concat de chunks: riesgo de narración truncada — P1

## Sync con escenas

| Modo | Comportamiento |
|------|----------------|
| SaaS MVP | TTS **por bloque**; duración clip = audio → sync fuerte |
| Clásico | **Una** narración completa; imágenes con duración heurística; video se estira al audio |

## Capacidad 800–1800 palabras / 8–12 min

**CONFIRMED viable a nivel TTS** (chunking + caps de guion).

Estimación UI: ~140 wpm → 1120–1680 palabras ≈ 8–12 min.

### Riesgo operativo

En modo Reddit (`plan_scenes_reddit_segments`, ~12 palabras/segmento), 1800 palabras ⇒ **~150 llamadas TTS**.  
Para documentales: usar **plan_scenes** por frase/párrafo o **voz única + stills** (clásico) — mucho más barato y robusto.

## Regeneración

- Por archivo stem: pisar `output/audio/<stem>.mp3` es idempotente a nivel archivo  
- UI no ofrece regen por bloque  
- Audio SaaS en carpeta global → colisiones entre proyectos (P1)

## Costos

Pricing: **REQUIRES CURRENT PRICING CHECK** (no hay tarifas en repo).  
Uso: 1–N llamadas por video según chunking/bloques; caracteres ≈ longitud del guion.
