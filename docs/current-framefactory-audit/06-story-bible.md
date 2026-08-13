# 06 — Story Bible

**Archivo:** `documentary/story_bible.py::build_story_bible`

## Estructura REAL

```json
{
  "global_style": "Documentary cinematic realism, 16:9... Style lock hint: ...",
  "characters": [
    {
      "id": "CHAR_001",
      "name": "Adam Neumann",
      "description": "Recurring figure related to: {topic}",
      "visual_description": "Realistic adult, period-appropriate wardrobe...",
      "appears_in_shots": [3, 7, 12]
    }
  ],
  "locations": [
    {
      "id": "LOC_001",
      "name": "Corporate office",
      "description": "...",
      "visual_description": "Open-plan office, glass walls...",
      "appears_in_shots": [1, 2]
    }
  ],
  "important_objects": [
    {
      "id": "OBJ_001",
      "name": "Financial document",
      "description": "...",
      "visual_description": "...",
      "appears_in_shots": []
    }
  ],
  "timeline_periods": [
    {
      "id": "TIME_001",
      "name": "2019",
      "description": "Period around 2019",
      "visual_description": "Wardrobe, tech consistent with 2019",
      "appears_in_shots": []
    }
  ]
}
```

## Detección recurrencias

1. **LLM extract** (si API key): JSON desde topic+script, regla no inventar
2. **Heurística fallback:**
   - Characters: proper nouns capitalizados frecuentes
   - Locations/objects: plantillas genéricas LOC_001/002, OBJ_001
   - Timeline: regex años `19xx|20xx`
3. **Shot refs:** keyword guess (`office`→LOC_001) + name match en narration

## Dónde se guarda

- `projects/<id>/flow-pack/story-bible.json`
- Embebido en `shot-list.json` y `visual_analysis.json`
- Referencias texto: `flow-pack/references/characters/CHAR_001.txt`, etc.

## Uso posterior

- UI Master References (read-only display + copy)
- Inyectado en `_ref_instructions` al copiar prompt+refs
- **No** hay upload de PNGs de referencia generados en Flow

## timeline_periods

Existe en schema pero **no** tiene UI dedicada en Flow Workspace (solo characters/locations/objects en expander).
