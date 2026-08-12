# 15 — Plan mínimo de implementación

**No implementar en esta fase.** Solo plan aprobado por el usuario después.

Diseñado para **Video 1/100**, no para Video 100.

## MUST HAVE antes de Video 1

| # | Cambio | Por qué bloquea | Esfuerzo est. |
|---|--------|-----------------|---------------|
| M1 | Workspace por proyecto `output/projects/<id>/` | Evita overwrite (P0-001) | 0.5–1 d |
| M2 | Plantilla guion `business_documentary_en` + target ~1400 palabras + checklist facts (md) | Canal correcto (P0-005) | 0.5–1 d |
| M3 | Export Flow Pack mínimo (shots numerados + global-style + README) desde beats/FrameSpec **sin gen** | Preparar Flow (P0-003 prep) | 1–1.5 d |
| M4 | Import `NNN.png` → `escena_XXXX.png` + validación conteo | Cerrar loop Flow (P0-003) | 0.5 d |
| M5 | Render path: voz (1 pista o bloques grandes) + `montar_video` con stills + música + Ken Burns on + metadata texto | Publicar | 0.5–1 d |
| M6 | Desactivar defaults Reddit/Replicate/gameplay en este workflow | Evitar P0-006 y costes | 0.25 d |

**Total MUST HAVE:** ~3–6 días-persona.

### Criterio de hecho Video 1
- Guion EN 8–12 min revisado por humano  
- Carpeta flow-pack generada  
- Stills importados y montados  
- MP4 final + título/descripcion/thumb prompt  

## SHOULD HAVE antes de Video 10

- Reemplazo de N shots sin re-TTS completo  
- Capítulos desde timestamps reales de audio  
- Thumbnail PNG (Flow/Canva) asistido desde prompt  
- Botón Studio “Documentary day” (wizard corto)  
- Fail-fast si falta API TTS  
- Outline → draft en 2 pasos con sección Sources/Unknowns  

## CAN WAIT hasta Video 30+

- Story Bible automática CHAR/LOC/OBJ  
- Ducking sidechain  
- Resume fino mid-render  
- QA VLM post-import  
- YouTube upload API  
- Borrar stack Comfy/Replicate/frame_image_pipeline  
- Unificación estética de pipelines  

## DO NOT BUILD

Ver `14-do-not-build.md`.

## Secuencia sugerida de engineering

```
Day Eng 1: M1 workspace + M6 defaults
Day Eng 2: M2 plantilla + checklist
Day Eng 3–4: M3 flow-pack export
Day Eng 5: M4 import + M5 render glue
Day Eng 6: dry-run con 5 stills dummy → luego Video 1 real
```
