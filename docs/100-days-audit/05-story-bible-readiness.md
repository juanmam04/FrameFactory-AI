# 05 — Story Bible readiness

## Objetivo futuro (no implementar)

Cast, locations, objects, timeline, global style extraídos del guion y versionados.

## Qué existe hoy (CONFIRMED)

| Artefacto | Tipo | Dinámico desde guion? |
|-----------|------|------------------------|
| `config/visual_bible.yaml` | Style lock estático | No |
| `config/character_bible.yaml` | Presets protagonistas | No |
| `narrative_rules` dark confession bible | Tono de canal | No |
| Catálogo SaaS CHARACTERS/BACKGROUNDS | Assets fijos UI | No |
| `scene_visual_mapper._guess_characters` / `_guess_location` | Heurística keyword por beat | Parcial, efímero |
| `storyboard_continuity.CharacterStateStore` | Estado entre beats (outfit, location_id) | Solo path V1 prompts |
| `FrameSpec` fields | action, location, characters estructurales | Sí en clásico V2, no exportado como bible |
| `scene_visual_intent` / edit planner | B-roll / visual_direction por bloque | Texto libre, no IDs CHAR/LOC |

## Conclusión

**No hay Story Bible persistente.** Hay **bibles estáticas de estilo** + **estado efímero de continuidad de prompts** + **hints por bloque**.

## Infraestructura reutilizable

1. **FrameSpec** (`frame_spec.py`) — mejor contenedor actual de “qué se ve en el shot”.  
2. **visual_beats** — action/location/camera.  
3. **Guessers** en `scene_visual_mapper` — semilla débil para CHAR/LOC.  
4. **visual_bible.yaml** → seed de `global-style.txt`.  
5. **JSON de meta SaaS** (`saas_last_mvp_meta.json`) — ya guarda bloques; se puede extender.

## Qué falta

- Extracción LLM estructurada → `story-bible.json` (CHAR_###, LOC_###, OBJ_###, TIMELINE)
- IDs estables referenciados por shots
- Wardrobe/period por personaje
- UI de revisión de bible

## Dónde encajaría (mínimo)

Tras aprobar guion, **antes** de Flow Pack:

```
script approved → (future) extract_story_bible → flow_pack(shots reference bible IDs)
```

Modelo de datos más cercano hoy: lista de `FrameSpec` + dict de entidades.  
Para Video 1: **bible manual corta en markdown** basta; extracción automática es SHOULD HAVE (Video 10+).
