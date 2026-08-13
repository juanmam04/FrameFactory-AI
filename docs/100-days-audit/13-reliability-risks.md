# 13 — Riesgos de robustez (100 días)

## P0 — puede impedir publicar ese día

### FF100-P0-001 — Output compartido sin workspace (Studio)
- **Descripción:** Streamlit llama `run_saas_mvp` sin `workspace_subdir`; pisa `final.mp4`, `clip_*.mp4`, JSON globales.  
- **Evidencia:** `saas_ui._run_mvp_thread` vs `web/render_worker.py` (sí pasa `job_{id}`).  
- **Impacto:** perder el render de ayer / mezclar assets.  
- **Rec:** workspace `output/projects/<id>/` obligatorio.  
- **Bloquea Video 1:** Sí (operativo).

### FF100-P0-002 — Sin resume / checkpoints
- **Descripción:** fallo mid-TTS o mid-clip exige reinicio. Progreso es solo UI JSON.  
- **Evidencia:** `run_saas_mvp` loop lineal; `.saas_render_progress.json` cosmético.  
- **Impacto:** perder 30–90 min.  
- **Rec:** checkpoint por etapa (script / audio / import / render).  
- **Bloquea Video 1:** Parcial (mitigable con cuidado); crítico a escala 100.

### FF100-P0-003 — Sin bulk import Flow
- **Descripción:** no hay mapeo `001.png`→escena en producto.  
- **Evidencia:** sin uploader; único reuse = `skip_imagenes` + `escena_*.png`.  
- **Impacto:** no hay path limpio “Flow → video”.  
- **Rec:** script import + skip gen.  
- **Bloquea Video 1:** Sí (para el nuevo workflow).

### FF100-P0-004 — Regeneración por bloque stub
- **Descripción:** Review UI no regenera clip/audio/imagen.  
- **Evidencia:** `saas_ui.page_review` mensaje “próximamente”.  
- **Impacto:** un shot malo = día perdido o re-render total.  
- **Rec:** al menos re-montar con still reemplazado.  
- **Bloquea Video 1:** No si el import/render es manual-disciplinado; sí a escala.

### FF100-P0-005 — Guion no documental / factual
- **Descripción:** plantillas POV/Reddit ES; prompts incentivan detalles inventados.  
- **Evidencia:** `config/plantillas_guion.yaml`, `script_generator.py`.  
- **Impacto:** contenido inadecuado o riesgo reputacional.  
- **Rec:** plantilla EN + proceso humano.  
- **Bloquea Video 1:** Sí (calidad del canal).

### FF100-P0-006 — Reddit segments × video largo
- **Descripción:** ~12 palabras/bloque → ~100–180 TTS.  
- **Evidencia:** `scene_planner.plan_scenes_reddit_segments`.  
- **Impacto:** rate limits, coste, tiempo.  
- **Rec:** no usar reddit mode para docu; voz única o bloques por párrafo.  
- **Bloquea Video 1:** Si se deja el default Reddit, sí.

### FF100-P0-007 — TTS sin API → archivo vacío
- **Descripción:** `generar_voz` escribe MP3 vacío si no hay keys.  
- **Evidencia:** `voice_generator.py` L77–80 aprox.  
- **Impacto:** fallos confusos / audio mudo.  
- **Rec:** fail-fast.  
- **Bloquea Video 1:** Solo si mal config.

### FF100-P0-008 — Secretos en `.env.example`
- **Descripción:** keys con aspecto real en ejemplo versionado.  
- **Evidencia:** `.env.example`  
- **Impacto:** compromiso de cuentas.  
- **Rec:** rotar + placeholders.  
- **Bloquea Video 1:** Seguridad, no creativo.

## P1 — pérdida considerable de tiempo

| ID | Tema |
|----|------|
| FF100-P1-001 | Fallos silenciosos: subs/mix/zoom omitidos con warning |
| FF100-P1-002 | Chunk TTS sin FFmpeg → narración truncada |
| FF100-P1-003 | Miniatura sin PNG |
| FF100-P1-004 | Review regenera guion si falta meta (desync + coste) |
| FF100-P1-005 | Audio `output/audio/` global colisiona stems |
| FF100-P1-006 | Concat `-c copy` frágil entre clips heterogéneos |
| FF100-P1-007 | Capítulos clásicos no usan duración real TTS |

## P2 — molesto

| ID | Tema |
|----|------|
| FF100-P2-001 | Ken Burns clásico off por default |
| FF100-P2-002 | Sin ducking música |
| FF100-P2-003 | Dual pipeline / docs desfasados |
| FF100-P2-004 | Tests de voz triviales |

## P3 — mejora futura

| ID | Tema |
|----|------|
| FF100-P3-001 | Estimación duración por tamaño MP3 |
| FF100-P3-002 | Placeholder cartoon si falta PNG catálogo |
| FF100-P3-003 | Aprobar proyecto demo sin efecto fuerte |
| FF100-P3-004 | Story Bible automática |
