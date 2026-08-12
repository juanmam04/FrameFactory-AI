# 04 — Research y Script

## Research

### ¿Research automático? **NO**

Solo campos manuales en proyecto:

| Campo UI | Variable | Storage |
|----------|----------|---------|
| Research notes | `research_notes` | `project.json` + editable Overview |
| Sources | `sources[]` | `project.json` |

También se crean al crear proyecto:
- `script/research_notes.md`
- `script/fact_checklist.md` (markdown checklist humano)

**No hay:** web search, RAG, agente research, APIs externas.

### Cómo llega al script

`script_service.generate_documentary_script` concatena:

```text
{topic}

RESEARCH NOTES (use only these facts...):
{research_notes}

SOURCES:
- source1
```

Eso va como `tema` a `generar_guion(..., plantilla="business_documentary_en")`.

### Controles factualidad

- Prompt plantilla: no inventar; omitir si UNKNOWN
- `fact_check_status`: pending | approved | needs_fixes
- Aprobación humana obligatoria antes Flow Pack
- Checklist markdown (no enforced por código)

---

## Script — Generate Script click

**Función:** `documentary/script_service.generate_documentary_script`  
**LLM path:** `script_generator.generar_guion`  
**Plantilla:** `business_documentary_en` (`config/plantillas_guion.yaml`)  
**Modelo:** `OPENAI_MODEL` env, default `gpt-4o-mini`  
**Mock path:** `_mock_script` (offline dogfood)

### Plantilla (CONFIRMED)

- Idioma: **English**
- Estructura interna: HOOK → CONTEXT → SETUP → ESCALATION → TURNING POINT → CONSEQUENCES → ENDING
- Voz: third-person documentary
- **No** hereda POV "Este eres tú" ni biblia Reddit (`script_generator` branch `elif plantilla == "business_documentary_en"`)

### Inputs

| Input | Source |
|-------|--------|
| topic | `project.topic` |
| target_words | `project.target_words` default 1500 |
| research_notes | project |
| sources | project |
| creative_profile | **NO** |

### Output

- `project.script` (string)
- `script/script.txt`
- `script/script_meta.json` `{word_count, target_words}`
- `script_approved = False`
- `fact_check_status = pending`
- checkpoint `script_ready = True`
- checkpoint `flow_pack_ready = False` (invalida pack previo)

### Duration target

- Slider 1000–2000 words (~7–14 min @ 140 wpm)
- `target_duration_min: [8, 12]` en schema pero **no** usado en UI como control separado

---

## Approve Script

**Función:** `approve_script`

| Efecto | Valor |
|--------|-------|
| `script_approved` | True |
| `fact_check_status` | approved |
| `script_ready` checkpoint | True |
| Desbloquea | Generate Flow Pack |

### Editar script

**Save script edits:** `save_edited_script`
- Reset `script_approved = False`
- Reset `fact_check_status = pending`
- `flow_pack_ready = False` → **Flow Pack invalidado**

Editar después de approve **requiere re-approve** y re-generar Flow Pack.

---

## Topic / ideas

Documentary **NO** propone topics.

| Capacidad | Documentary | Studio Create |
|-----------|-------------|---------------|
| Usuario da topic | Sí (required) | Sí |
| Ideas IA | No | Sí (`saas_viral_idea_engine`) |
| Creative profile | No | Sí |
| Memoria sesión | No | Sí |

Para "hoy necesito el próximo video" → **no existe** en Documentary hoy.
