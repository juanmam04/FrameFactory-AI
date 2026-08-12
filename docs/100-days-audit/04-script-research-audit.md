# 04 — Auditoría de guiones y research

## Cómo genera scripts hoy (CONFIRMED)

- **Función:** `src/script_generator.py::generar_guion`
- **Modelo:** `os.getenv("OPENAI_MODEL", "gpt-4o-mini")`
- **Plantillas:** `config/plantillas_guion.yaml` — `explicativo`, `reddit_stories`, `historia`, `listado`
- **Uso SaaS:** `reddit_stories` o `explicativo` (`pipeline.run_saas_mvp`)
- **Contexto extra:** `creative_profile` + `narrative_rules.channel_dark_confession_bible`
- **Control longitud:** target_words 80–10000; min 80% / max 120%; draft + expand/trim (múltiples llamadas OpenAI)
- **Idioma dominante en plantillas:** español neutro, 2ª persona (“Este eres tú.”) — CONFIRMED en `plantillas_guion.yaml`

## Estructura hook / body / payoff

| Plantilla | Estructura | ¿Sirve a docu business EN? |
|-----------|------------|----------------------------|
| `explicativo` | Acto 0 gancho + “Este eres tú.” + actos + cierre cine | **No** (POV ficción cinematográfica) |
| `reddit_stories` | Confesión oscura 5 fases | **No** (ficción viral) |
| `historia` / `listado` | Existen en YAML; SaaS no las elige | Parcial / no documental |

No hay outline persistido por actos ni QA estructural post-hoc más allá del conteo de palabras.

## Research / fuentes / alucinaciones

| Capacidad | Estado | Evidencia |
|-----------|--------|-----------|
| Research web | **Ausente** | Sin módulo search/scrape/RAG |
| Fuentes citadas | **Ausente** | — |
| Anti-alucinación factual | **Ausente** | Prompts piden “cifras, nombres, marcas” → **incentiva** detalle inventado |
| Separación narración vs visuales | Parcial | Guion = narración; visual en planners separados |
| Regenerar partes | UI Review stub; CLI `regeneration` clásico | Débil para reto diario |
| Contexto global | Perfil creativo + session memory | Útil tono; no facts |

## Utilidad para documentales money/power/business 8–12 min

**Evaluación: BAJA–MEDIA como está.**

- **Longitud:** el motor **puede** generar ~1120–1680 palabras (CONFIRMED caps + guidance `target_words >= 1000`).
- **Formato:** **no** está calibrado a mini-documental factual en inglés.
- **Riesgo editorial:** inventar fraudes/fechas/cifras es inaceptable en este nicho.

### Qué reutilizar
- Orquestación de longitud / retries de word count
- Inyección de `creative_context`
- Estimación UI `_saas_estimated_speech_minutes` (~140 wpm)

### Qué falta (sin implementar aún)
- Plantilla `business_documentary_en`
- Paso research notes (aunque sea markdown pegado por humano)
- Reglas: “no inventar; marcar UNKNOWN; citar”
- Outline → draft → fact pass
- Idioma EN nativo (TTS EN)

## Ideas / viral engine

`saas_viral_idea_engine` + biblia dark confession: útil para shorts Reddit, **contraproducente** como default del canal documental. Clasificar **DEPRECATE** del path 100-days docu; opcional otro canal.
