# 12 — Diseño UX ideal propuesto

Comparación con el estado actual. **No implementado** — diseño objetivo.

---

## Concepto central

```text
SESSION = CHANNEL / FORMAT
  "100 Days — Business Documentaries"
  ↓ creative_profile estructurado (una vez)
  
VIDEO = historia individual
  ↓ hereda idioma, tono, duración, estilo visual, reglas Flow
```

---

## Pantalla home ideal

```text
┌─────────────────────────────────────────┐
│ 100 Days — Business Documentaries       │
│ Video 12 / 100 · Streak: 11 days        │
│                                         │
│ [ CREATE TODAY'S VIDEO ]                │
│                                         │
│ Recent: 011-enron · 010-theranos · …    │
└─────────────────────────────────────────┘
```

**vs hoy:** select Project + formulario técnico.

---

## Flujo diario ideal (8 pasos visibles)

```text
OPEN → IDEAS → CHOOSE → RESEARCH → SCRIPT → APPROVE
  → FLOW → IMPORT → VOICE → RENDER → DONE
```

Un solo **stepper** horizontal; tab actual resaltado; botón "Continue" siempre visible.

**vs hoy:** 5 tabs libres + status table.

---

## Paso IDEAS

FrameFactory propone **3–10 historias** usando:
- `creative_profile.topics_to_focus`
- `idea_generation.brief`
- historial de proyectos (evitar repetir)
- opcional: trending / manual seed "fraud this week"

Usuario: click en una card → pre-rellena topic + título.

**vs hoy:** usuario escribe topic desde cero.

---

## Paso RESEARCH

Opciones en capas (no overengineering):

1. **Quick** — usuario pega bullets + URLs (como hoy, mejor UI)
2. **Assisted** — LLM expande bullets a research_notes estructurado (sin web = disclaimer)
3. **Advanced** — web search futuro (LATER)

Plantilla visible: Facts / Timeline / Key people / Open questions / Sources.

**vs hoy:** textarea vacío.

---

## Paso SCRIPT

- Un botón: **Generate script**
- Preview con word count + estimated duration
- Inline edit
- **Approve & lock** — modal explica que desbloquea Flow

**vs hoy:** 3 botones (LLM / mock / approve) + save clears approval sin modal.

---

## Paso FLOW (integrado)

- Master refs: copy all bundle (zip o single doc)
- Shot cards con progress: ○ pending · ◐ generated · ✓ imported
- Batch export: "Copy batch 01 prompts" 
- Instrucciones Flow inline (3 pasos, no README en disco)

**vs hoy:** Flow Workspace potente pero manual y desconectado de import status.

---

## Paso IMPORT

- Drag-drop folder o watch `flow-import/`
- Auto-detect new PNGs → update shot status
- Missing highlighted con "copy prompt again"

**vs hoy:** path text + bulk import button.

---

## Paso VOICE + RENDER

- **Generate voice** → **Render video** (dos clicks max)
- Music: default del canal, slider simple "Background music: Low / Medium"
- Preview inline
- **DONE** screen: final.mp4 + campos YouTube (title, description, tags) + export thumbnail prompt

**vs hoy:** voice + preview JSON + assemble checkbox + no metadata.

---

## Session setup (una vez)

Conversación:

> Quiero documentales en inglés de 8–12 min sobre empresas, fundadores, fraude…

FrameFactory escribe `creative_profile` + crea Session Documentary vinculada.

Todos los proyectos Documentary de esa session heredan:
- language, target_words, tone, title_style
- global_style seed para story bible
- default music, voice id
- idea_generation angles

**vs hoy:** Perfil Studio existe pero Documentary ignora.

---

## Qué esconder en Advanced

- Project id manual
- Batch size
- Flow Pack offline / no LLM
- Allow missing images
- Music path filesystem
- voice_speed fine tuning
- fact_check_status manual

---

## Qué eliminar del camino Documentary

- Nav items Studio (Dashboard, Nuevo video, Render legacy) cuando session type = documentary
- Mock script button (dev only via env flag)
- Duplicate research en Overview + create form
