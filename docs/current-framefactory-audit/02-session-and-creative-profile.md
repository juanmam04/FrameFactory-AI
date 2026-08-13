# 02 — Sesión y Creative Profile

## ¿Sigue existiendo? **SÍ** (Studio legacy)

El sidebar **Sesión de trabajo** y **Perfil** siguen activos. Documentary **no los consume**.

## Crear sesión (CONFIRMED `saas_ui._nav`)

1. Click **Nueva sesión**
2. `_session_persist()` guarda chat/perfil actual
3. `add_session(store, "Nueva sesión", seed_profile)` — seed = creative_profile actual
4. Nueva sesión con mensaje inicial del asistente

**Pregunta inicial al usuario (CONFIRMED `saas_sessions.new_session_doc`):**

> "Hola. ¿Qué tipo de videos querés publicar en esta sesión?"

## Dónde se guarda

| Dato | Path |
|------|------|
| Store sesiones | `output/saas_sessions.json` |
| Legacy (migrado) | `output/saas_agent_chat.json`, `output/saas_creative_profile.json` |

### Estructura sesión (CONFIRMED `new_session_doc`)

```json
{
  "id": "20260812_031500_a1b2c3d4",
  "title": "Nueva sesión",
  "created_at": "2026-08-12T03:15:00",
  "updated_at": "2026-08-12T03:15:00",
  "memory_summary": "",
  "messages": [
    {"role": "assistant", "content": "Hola. ¿Qué tipo de videos querés publicar en esta sesión?"}
  ],
  "creative_profile": { "...": "..." }
}
```

Store root:

```json
{
  "version": 1,
  "active_id": "<session_id>",
  "sessions": [ ... ]
}
```

## creative_profile

**Definición:** `src/saas_creative_profile.default_creative_profile()`

**Campos principales (CONFIRMED):**

- `niche`, `tone`, `hook_style`, `pacing`, `narrator_preference`
- `language_register`, `topics_to_avoid`, `topics_to_focus`
- `title_style`, `thumbnail_style`
- `audience`: `{who, pain_points, reading_level}`
- `channel`: `{name, tagline, content_pillars}`
- `script`: `{structure_preference, forbidden_phrases, cta_style, opening_style}`
- `video`: `{primary_format, target_length_category, ...}`
- `visual`: `{look, color_mood, shot_preferences, b_roll_style, ...}`
- `editing`: `{cut_rhythm, transitions_default, subtitles_intent, music_role, ...}`
- `idea_generation`: `{brief, angles_to_favor, angles_to_avoid}`
- `notes_freeform`

**Default problemático para tu canal:** `content_type: "reddit_dark_storytime"` y `angles_to_avoid` orientado a narco/Reddit oscuro.

## Cómo se genera / actualiza

1. **Manual** — tab Editar perfil en Perfil
2. **Chat asistente** — tab Asistente: mensajes → `_creative_agent_reply` → merge JSON al perfil
3. **Memoria de sesión** — botón resumir chat → `summarize_session_messages` → `memory_summary` en sesión

## Quién consume creative_profile (Studio only)

| Consumidor | Uso |
|------------|-----|
| `generar_guion` | `creative_context` (excepto plantilla documentary_en aislada) |
| `page_create` ideas IA | `saas_viral_idea_engine` |
| `run_saas_mvp` | `creative_profile` + `session_context` en render |
| `saas_edit_planner` | plan montaje por bloque |

**Documentary:** ninguno (CONFIRMED).

## Relación Sesión ↔ Documentary

| Pregunta | Respuesta |
|----------|-----------|
| A) ¿Usa sesiones? | **NO** |
| B) ¿Usa creative_profile? | **NO** |
| C) ¿Usa memoria de sesión? | **NO** |
| D) ¿Independiente? | **SÍ** |
| E) ¿Parcial? | **NO** |

**Hallazgo importante:** configurar el canal en Perfil/Asistente **no afecta** Documentary hoy.

## Potencial (no implementado)

El esquema `creative_profile` + sesión conversacional **podría** mapearse a "Session = Channel" para Documentary, pero hoy son sistemas paralelos.
