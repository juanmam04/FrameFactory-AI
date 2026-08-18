# Check ALS — Phase 0 + Phase 1 delivery

Status: **ready for review**. Do not start Phase 2 until approved.

## Implemented

### Format pack (new)
| File | Role |
|------|------|
| `src/documentary/formats/__init__.py` | `content_format` helpers (`documentary` / `check_als`) |
| `src/documentary/formats/check_als/editorial.py` | Check editorial invariants, categories, concept system prompt |
| `src/documentary/formats/check_als/profile.py` | `check_als_profile()` defaults (12–18 min, 2nd person, visual style) |
| `src/documentary/formats/check_als/concepts.py` | Concept / Title / Thumbnail / Hook engines + coherence + world_seeds |
| `src/documentary/formats/check_als/__init__.py` | Package exports |
| `docs/check-als-phase2-world-state.md` | Contract: `world_state` will be SoT in Phase 2 |
| `docs/check-als-phase1-example-concepts.json` | 5 example concept packages |

### Engine / wiring (modified, non-destructive)
| File | Change |
|------|--------|
| `src/documentary/channel.py` | Re-exports Check profile + format helpers; documentary profile untouched |
| `src/documentary/ideas.py` | Routes to Check concept packages when `content_format=check_als` |
| `src/documentary/project.py` | `content_format`, `concept`; Check projects skip research → `ui_step=story` |
| `studio/server.py` | Dual sessions; `/api/channel/format`; `/api/concepts/regenerate`; ideas/projects accept format |
| `studio/static/studio.js` | Concept UI + format toggle + granular regen |
| `studio/static/studio.css` | Hook block styles |
| `public/**` | Synced via `scripts/sync_public_studio.py` |

## Data model — Concept package

```json
{
  "id": "string",
  "content_format": "check_als",
  "premise": "string",
  "title": "string",
  "title_options": [{ "text", "scores": {clarity,curiosity,fantasy,scale,instant_understanding,promise_match}, "overall_score" }],
  "one_line_fantasy": "string",
  "starting_state": "string",
  "end_state": "string",
  "core_transformation": "string",
  "story_category": "entrepreneurship|…",
  "ending_direction": "victory|…",
  "scores": { "fantasy_strength": 1-10, "…": "…", "originality": 1-10 },
  "overall_score": 0.0,
  "thumbnail_concept": {
    "main_visual", "protagonist_state", "environment", "central_contrast",
    "emotion", "key_object", "composition", "camera", "lighting",
    "background", "text_if_any", "thumbnail_prompt"
  },
  "hook": "multiline second-person cold open",
  "hook_seconds_target": [15, 30],
  "world_seeds": {
    "starting_age", "starting_cash", "starting_location", "starting_status",
    "target_outcome", "business_or_career_type", "timeline_scale"
  },
  "coherence": {
    "title_matches_thumbnail", "hook_fulfills_promise",
    "transformation_aligned", "notes", "pass"
  }
}
```

## UI flow

1. New episode → Format select: **Check ALS** | Documentary  
2. Generate concepts → ranked by `overall_score`  
3. Inspect: title, premise, start/end, transformation, hook, thumbnail concept, scores, coherence  
4. Optional: Regen title / thumb / hook / concept (without regenerating the whole list)  
5. **Select concept** → creates project with `content_format=check_als`, `concept` persisted, `ui_step=story`  
6. No auto-advance to Story Blueprint

## Example output

See `docs/check-als-phase1-example-concepts.json` (5 offline packages). Titles include:

- POV: You Build a $100M Company From Your Bedroom  
- POV: You Turn $100 Into $10 Million  
- POV: You Buy a Bankrupt Company for $1  
- POV: You Retire Your Parents at 23  
- POV: You Build an Empire and Lose Everything  

## Regression check

Smoke verified:

- Documentary profile + offline ideas still return `title_concept` WeWork-style packs  
- Check profile isolated behind `check_als`  
- Creating documentary project still lands on `ui_step=research`  
- Episode `001-the-47-billion-company-that-almost-collapsed-ove` still loads (script + voice intact)

## Phase 2 reminder

`world_state` = source of truth. Concept `world_seeds` only initialize it.
