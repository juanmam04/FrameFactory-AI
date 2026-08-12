# 07 — Flow Pack y Flow Workspace

## Generate Flow Pack — qué hace

**Función:** `documentary/flow_pack.py::export_flow_pack`

**Precondición:** `script_approved == True`

**Pasos:**
1. `analyze_visuals` (si rebuild o no existe visual_analysis.json)
2. Escribe en `projects/<id>/flow-pack/`:

| Archivo | Contenido |
|---------|-----------|
| `global-style.txt` | story_bible.global_style |
| `story-bible.json` | bible completa |
| `references/characters/CHAR_*.txt` | master ref prompts |
| `references/locations/LOC_*.txt` | idem |
| `references/objects/OBJ_*.txt` | idem |
| `shots/001.txt` … `NNN.txt` | shot brief legible |
| `shot-list.json` | shots + batches + bible |
| `README.md` | instrucciones humanas Flow |
| `visual_analysis.json` | análisis interno |

3. Checkpoint `flow_pack_ready = True`
4. `project.flow_pack = {shot_count, batch_size}`

**LLM:** vía analyze_visuals (beats + bible), no LLM extra en export.

---

## Flow Workspace — elementos UI CONFIRMADOS

| Elemento | Existe | Notas |
|----------|--------|-------|
| Generate / refresh Flow Pack | ✅ | disabled sin approve |
| Flow Pack offline | ✅ | sin LLM beats |
| MASTER REFERENCES expander | ✅ | global style + CHAR/LOC/OBJ |
| Global style textarea | ✅ | read-only display |
| Batch selector buttons | ✅ | BATCH_01… max 6 columnas |
| Shot number header | ✅ | ### SHOT NNN |
| Narration display | ✅ | st.write |
| References display | ✅ | comma-separated IDs |
| Continuity display | ✅ | |
| Shot type display | ✅ | |
| Expected file display | ✅ | NNN.png |
| Prompt textarea | ✅ | editable display only (no save back) |
| Copy Prompt (st.code) | ✅ | manual ⌘C |
| Copy Prompt + References (st.code) | ✅ | |
| Previous / Next buttons | ✅ | persiste flow_shot_index |
| Mark generated | ✅ | status + auto next |
| Mark approved | ✅ | |
| Needs regen | ✅ | |
| Status caption | ✅ | pending/generated/approved/needs_regen |
| Batch prompts quick scan | ✅ | expanders per shot in batch |

**NO existe (CONFIRMED ausente en código):**
- Clipboard API / one-click copy button
- Keyboard shortcuts
- Copy entire batch at once
- Upload reference images from Flow
- Checkbox UI (usa buttons Mark *)
- Timeline periods UI section
- Drag-drop images

---

## Workflow FrameFactory → Flow → FrameFactory

1. **Approve script** → Flow Workspace tab
2. **Generate Flow Pack**
3. Abrir expander **MASTER REFERENCES**
4. Copiar global style + cada CHAR/LOC/OBJ prompt → generar en Flow → guardar refs externamente (no upload FF)
5. Click **BATCH_01** → shots 001–010
6. Por cada shot: copiar prompt (o prompt+refs) → Flow → descargar como `NNN.png`
7. **Mark generated** → Next (loop)
8. Repetir batches
9. Poner todos PNG en `projects/<id>/flow-import/` (o carpeta custom)
10. Tab **Images** → Bulk import
11. Tab **Voice & Render**

### Fricciones actuales

- Copy manual desde `st.code` (no botón clipboard)
- Global style textarea no editable/save
- Prompt textarea edits no persisten al JSON
- Referencias Flow no se re-importan a FrameFactory
- Mezcla español en LLM beats vs inglés en script
- 5 tabs — mucho context switching
