# 01 — Session = Channel model

```text
SESSION  = CHANNEL / FORMAT
VIDEO    = episode under that channel
```

## Detection

A session is Documentary when Creative Profile has:

- `workflow: "documentary"`, or
- `content_type: "business_documentary"`, or
- `video.content_type: "business_documentary"`

## Profile fields → Documentary

| Area | Fields used |
|------|-------------|
| Ideas | `idea_generation.*`, `topics_to_focus`, `topics_to_avoid`, `niche`, `channel.content_pillars`, `title_style`, `audience`, memory |
| Script | full profile via `profile_to_script_context` + idea brief + research/sources; `channel.target_words`, language |
| Visual / Flow | `visual.look/color_mood/shot_preferences/b_roll_style` |
| Editing | music volume defaults; Ken Burns via existing assembler; equal still length |

## Canonical channel

`business_documentary_profile()` seeds **100 Days — Business Documentaries** (EN, 8–12 min, ~1500 words, pillars, Flow manual).
