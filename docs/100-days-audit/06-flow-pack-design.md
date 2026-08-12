# 06 — Flow Pack — diseño mínimo viable

## Objetivo

Carpeta que una persona abre y usa en **Google Flow** sin APIs no oficiales.

## Modificación mínima sobre FrameFactory

**No** hace falta nuevo microservicio. Un script/CLI (o botón Studio) que, dado un proyecto con guion + beats/bloques, escriba:

```text
output/projects/<project-id>/flow-pack/
  README.md
  story-bible.json          # v1: puede ser stub o manual
  global-style.txt          # desde visual_bible / perfil
  references/
    characters/CHAR_*.txt   # v1 opcional
    locations/LOC_*.txt
    objects/OBJ_*.txt
  shots/
    001.txt
    002.txt
    ...
  shot-list.json
```

## Fuente de datos mínima (reutilizar)

| Campo shot | Fuente actual más cercana |
|------------|---------------------------|
| NARRATION | `block.text` / `Escena.texto` |
| TIME | acumulado por duración audio **o** estimación wpm pre-TTS |
| SHOT TYPE / CAMERA | `VisualBeat` / `FrameSpec` / edit planner |
| ACTION | `FrameSpec` / beat action / visual_intent |
| PROMPT | `frame_prompt_builder` **sin** llamar gen; o prompt sintetizado desde intent |
| EXPECTED FILE | `NNN.png` |
| REFERENCES | IDs bible (v1: vacío o heurística) |

### Path A (recomendado Video 1) — clásico ligero
`dividir_en_escenas` → `generar_beats` → `beats_a_frame_specs` → `prompt_desde_frame_spec` → escribir `shots/NNN.txt`  
**Sin** `frame_image_pipeline`.

### Path B — SaaS
Usar bloques + `visual` / `visual_direction` / `b_roll_suggestion`  
Más débil cinematográficamente; más cerca de la UI actual.

## Contenido mínimo de `NNN.txt`

```text
SHOT 024
EXPECTED FILE: 024.png
NARRATION: "..."
SHOT TYPE: wide
ACTION: ...
CONTINUITY: ...
PROMPT:
Documentary cinematic still, ...
```

## `README.md` del pack (humano)

1. Abrir Flow  
2. Pegar `global-style.txt` como estilo base  
3. Generar refs de personajes/locaciones si existen  
4. Generar shots en orden; guardar como `001.png`…  
5. Copiar a `output/projects/<id>/flow-import/`  
6. Volver a FrameFactory → Import → Render  

## Fuera de alcance Video 1

- Auto-upload a Flow  
- Browser automation  
- Scoring automático de outputs Flow  
- Story Bible LLM completa  

Ver `14-do-not-build.md`.
