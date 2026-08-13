# 13 — Plan de cambios

Prioridad: **producir 1 video/día con mínima fricción**. Sin overengineering.

---

## KEEP EXACTLY

| Componente | Por qué |
|------------|---------|
| Workspace `projects/<id>/` + `project.json` | Resume robusto, dogfood probado |
| Pipeline checkpoints | Gates claros script → flow → images → voice → render |
| Plantilla `business_documentary_en` | Alineada al canal EN |
| Visual director + story bible + shot-list | Core diferenciador vs "solo guion" |
| Flow Pack export a disco | Backup, debug, portabilidad |
| Bulk import `001.png` naming | Simple, funciona con Flow downloads |
| Voz continua (1 narración) | Correcto para documental 8–12 min |
| `montar_video` + Ken Burns | Evita slideshow estático |
| Approve script gate | Evita shots sobre guion cambiante |
| Tests + dogfood script | Regresión |

---

## SIMPLIFY

| Qué | Cómo |
|-----|------|
| Onboarding proyecto | Defaults desde Session; solo topic obligatorio |
| Nav Documentary | Stepper lineal reemplaza 5 tabs |
| Research UI | Plantilla Facts/Sources/Timeline |
| Flow copy | Botón "Copy" por shot + "Copy batch" |
| Status | Barra progreso + siguiente acción sugerida |
| Render tab | Un CTA "Produce video" (voice+assemble si falta) |
| Project id | Auto `012-slug`, oculto |

---

## CONNECT

| Qué | Cómo |
|-----|------|
| Session → Documentary | `documentary_session_id` en project; leer creative_profile |
| creative_profile → script | Pasar tone, audience, title_style a prompt (extend plantilla) |
| creative_profile → story bible | global_style seed desde `visual.look` |
| creative_profile → ideas | Nuevo `suggest_documentary_topics(session, n=5)` |
| Import → Flow status | Auto mark generated cuando PNG existe |
| Session counter | `video_count / 100` en projects de la session |

**Esfuerzo estimado:** 3–5 días focused.

---

## HIDE FROM DOCUMENTARY

- Sidebar Studio (Dashboard, Nuevo video, Render, Biblioteca) — modo `documentary_only` flag
- Sesión de trabajo Studio (o renombrar a "Channel setup" solo docu)
- Mock script, Flow Pack offline
- Workspace path, fact_check_status raw
- Preview checks JSON → human readable panel
- Music path text → file picker o env default

---

## REMOVE FROM DOCUMENTARY

- Duplicación research (create form + overview) → solo en paso Research
- `subtitles_enabled` del schema hasta que funcione (o implementar)
- Defaults Reddit en creative_profile cuando session es documentary

---

## BUILD (orden recomendado)

### Fase A — Daily driver (1–2 semanas)

1. **Documentary Session type** — vincular creative_profile; defaults en create_project  
2. **Idea generator** — 5 topics/día desde profile + historial  
3. **Wizard UI** — stepper + "Continue"  
4. **Clipboard copy** — prompts Flow  
5. **Import auto-sync** — detect PNGs → status  
6. **Produce video** — combina voice+render con checks humanos  

### Fase B — Polish (1 semana)

7. Research template + optional LLM expand (sin web)  
8. Post-render: title/description/tags desde script  
9. Thumbnail prompt export  
10. Subtitles burn (reuse `montar_video` ASS path)  

### Fase C — Channel memory

11. Session memory_summary en ideas ("no repetir Theranos")  
12. Streak / calendar 100 days  

---

## LATER

- Web research agent  
- Flow browser automation  
- Publicación YouTube API  
- Multi-user SaaS  
- Per-shot duration sync (timestamps TTS)  
- Pan lateral Ken Burns avanzado  

---

## Estimación implementación

| Fase | Alcance | Tiempo (1 dev) |
|------|---------|----------------|
| A1 Session connect + defaults | creative_profile → documentary | 2–3 días |
| A2 Ideas + wizard | UX diario | 3–4 días |
| A3 Flow copy + import sync | fricción Flow | 1–2 días |
| A4 Produce video CTA | voice+render unificado | 1 día |
| B Metadata + subs | publish-ready | 3–4 días |
| **Total MVP daily-usable** | A completo | **~2 semanas** |
| **Total publish-ready** | A + B | **~3 semanas** |

Sin contar QA manual de 2–3 videos reales con Flow.

---

## Riesgos a evitar

- Reescribir arquitectura en microservicios  
- Automatizar Flow (frágil, fuera de scope)  
- Research web sin control factual  
- Duplicar creative_profile en otro schema — **reusar el existente**
