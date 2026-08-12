# 05 — Visual Director

**Archivo:** `documentary/visual_director.py::analyze_visuals`  
**Trigger:** `export_flow_pack` (Flow Pack button)

## Pipeline (CONFIRMED)

```
script (approved)
  → dividir_en_escenas(script, segundos_por_imagen=seg)
  → generar_beats_para_escenas(escenas, topic, max_beats_total)
  → beats_a_frame_specs(beats)
  → prompt_desde_frame_spec(spec) + _compose_flow_prompt
  → shots[] + build_story_bible
  → flow-pack/visual_analysis.json
```

## Conceptos

| Término | En Documentary |
|---------|----------------|
| Scene | `Escena` de `scene_splitter` — párrafo/oración agrupada |
| Beat | `VisualBeat` — 1 por escena (forzado en `visual_beats`) |
| Shot | 1 beat = 1 shot = 1 PNG (`001.png`…) |

## Cuántos shots

```python
target_shots = max(50, min(80, round(words / 24)))
seg = max(4.0, min(12.0, words / target_shots / 2.3))
```

Para ~1500 words → ~62 shots target, cap 80.

## LLM calls

| Paso | LLM? | Modelo | Prompt |
|------|------|--------|--------|
| Beats por escena | Sí si OPENAI_API_KEY y no `VISUAL_BEATS_LLM_DISABLED` | gpt-4o-mini | Director cine → JSON beats (español en system prompt) |
| Beats fallback | No | heurística | `_beats_por_escena_fallback` |
| Story bible | Sí opcional | gpt-4o-mini JSON | Extract CHAR/LOC/OBJ/TIME |
| FrameSpec prompts | No LLM | reglas | `frame_director` + `frame_prompt_builder` |

**Offline button:** setea `VISUAL_BEATS_LLM_DISABLED=1` → solo heurística.

## Lógica vieja reutilizada

- `scene_splitter.dividir_en_escenas`
- `visual_beats.generar_beats_para_escenas`
- `frame_director.beats_a_frame_specs`
- `frame_prompt_builder.prompt_desde_frame_spec`

**NO genera imágenes** — solo texto estructurado.

## Shot object (schema real)

```json
{
  "number": 1,
  "id": "SHOT_001",
  "expected_file": "001.png",
  "narration": "...",
  "shot_type": "wide_shot",
  "camera": "POV first person",
  "action": "...",
  "location": "...",
  "emotion": "...",
  "continuity": "opening shot",
  "references": ["LOC_001"],
  "prompt": "GLOBAL STYLE: ...\nCURRENT ACTION: ...",
  "status": "pending",
  "scene_id": 1,
  "beat_id": 1
}
```

## Duración visual

**Pre-TTS:** no hay timestamps por shot.  
Duración en render = `voice_duration / num_images` (uniforme, ver doc 09).

Cambio visual = cada nuevo shot ≈ nuevo still; ritmo driven by scene split word count, not narration timing.
