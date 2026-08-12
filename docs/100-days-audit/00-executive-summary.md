# 00 — Resumen ejecutivo

## Veredicto general

**CONFIRMED:** FrameFactory hoy es un sistema **viable para narrar + montar + empaquetar**, pero **no** está alineado al formato documental de negocio 8–12 min con imágenes externas de Google Flow.

Hay **dos mundos**:

1. **Producto vivo (UI Streamlit / FastAPI):** `run_saas_mvp` — guion → bloques → TTS por bloque → clip FFmpeg (catálogo / B-roll Replicate / gameplay) → concat → subtítulos → mix.  
   Evidencia: `app.py` → `src/saas_ui.py` → `src/pipeline.py::run_saas_mvp`; `web/render_worker.py`.

2. **Pipeline clásico (CLI / scripts / tests):** `pipeline.run` — escenas → visual beats → FrameSpec → gen imágenes local → voz única → `montar_video`.  
   Evidencia: `src/pipeline.py::run`; no importado por `saas_ui`.

El stack de **generación de imágenes propio** (Replicate/ComfyUI/FrameValidator/Kontext/continuidad V1) es grande, costoso en mantenimiento y **ya no debe ser el camino principal**. Parte de su inteligencia narrativa (beats, specs, prompts, hints de B-roll) **sí** se puede reutilizar como director/shot list hacia Flow.

Para el reto **100 videos / 100 días**, el camino más corto **no** es refactorizar el generador visual: es **reutilizar montaje + voz + packaging**, añadir un **Flow Pack export + import numerado**, y **adaptar el guion** a documentales factuales en inglés.

## Respuesta a la pregunta central

> Camino más corto: tomar el path **clásico con `skip_imagenes`** (o un MVP SaaS que acepte carpeta de PNGs por bloque) + exportar prompts/shot list desde beats/`scene_visual_intent` + TTS + FFmpeg + metadata; **no** integrar Flow por API; **no** seguir iterando Replicate/ComfyUI.

## Reutilización aproximada

| Área | % reutilizable | Nota |
|------|----------------|------|
| Voz / TTS | ~90% | Listo para 8–12 min (chunking) |
| FFmpeg montaje clásico | ~80% | Ideal para stills + narración |
| SaaS MVP montaje | ~70% | Útil si se alimenta con stills externos |
| Guion LLM | ~40% | Longitud OK; plantilla/idioma/research NO |
| Director visual (beats/FrameSpec/intent) | ~50–60% | Como brief a Flow, no como gen |
| Gen imágenes local | ~5% | Deprecar del path principal |
| UI Studio | ~40% | Falta workspace, import, plantilla docu |
| Metadata YT | ~60% | Textos sí; PNG thumbnail no |
| Backend Node / stickman / Veo | ~0–10% | Lateral / abandonado |

**Estimación global reutilizable para el nuevo objetivo: ~55–65%.**  
El resto es deuda visual, UX Reddit/POV, o código muerto.

## P0 (bloquean o rompen el día)

Ver detalle en `13-reliability-risks.md`.

| ID | Resumen |
|----|---------|
| FF100-P0-001 | Studio escribe en `output/` compartido sin `workspace_subdir` → overwrite entre videos |
| FF100-P0-002 | Sin resume/checkpoints reales de pipeline |
| FF100-P0-003 | Sin bulk import Flow (`001.png`…`N.png`) en UI/MVP |
| FF100-P0-004 | Sin regeneración por bloque en UI (stub “próximamente”) |
| FF100-P0-005 | Plantilla de guion no es documental business EN; incentiva ficción |
| FF100-P0-006 | Modo Reddit: ~10–16 palabras/bloque → 100–180 TTS calls en video largo |
| FF100-P0-007 | TTS sin API escribe archivo vacío (`voice_generator.generar_voz`) |
| FF100-P0-008 | Secretos con aspecto real en `.env.example` (rotar) |

## 5 cuellos de botella humanos (hoy)

1. **Calidad/factualidad del guion** sin research ni plantilla documental.  
2. **Preparación visual + generación en Flow** (manual; no hay pack export).  
3. **Importación/mapeo imagen↔escena** (manual/frágil).  
4. **Re-renders completos** ante un fallo o un shot malo.  
5. **Thumbnail + empaquetado YouTube** incompleto (sin PNG).

## MUST HAVE antes de Video 1

1. Workspace aislado por proyecto/día (`output/projects/<id>/`).  
2. Plantilla de guion **documentary EN** (money/power/business) + target ~1200–1600 palabras.  
3. Export **Flow Pack** mínimo (shot prompts numerados + style + README).  
4. **Import bulk** `NNN.png` → escenas/bloques + render con `skip` gen interna.  
5. Path de render **stills + voice + music + subs** estable (preferir `montar_video` o MVP adaptado).  
6. Checklist humano de facts (aunque sea markdown; research automático puede esperar).

**Estimación implementación MUST HAVE:** 3–6 días-persona de ingeniería enfocada (sin overengineering).  
**Estimación trabajo humano Video 1 (con MUST HAVE hechos):** 3.5–6 h (dominado por Flow + review factual).  
**Hoy, sin cambios:** 8–14 h y alto riesgo de no publicar.

## Qué NO hacer ahora

Integración no oficial de Flow, nuevo generador de imágenes, microservicios, reescritura total de UI, agentes multi-step complejos. Ver `14-do-not-build.md`.
