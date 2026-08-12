# 03 — Flujo usuario Documentary (pantalla a pantalla)

Todo extraído de `documentary_ui.py`. Sin inventar UI.

## Pantalla 0 — Abrir app

- Comando: `./run.sh` o `npm run dev`
- URL: `http://localhost:8501`
- Sidebar: sesión Studio + nav
- Click: **Documentary**

## Pantalla 1 — Documentary home

**Header:** "Documentary" + subtítulo 100 Days EN business documentaries.

**Controls:**
- Select **Project**: `— new —` o ids existentes (`001-wework`, etc.)
- Caption: `N project(s)`

**Si `— new —`:** formulario crear (ver Pantalla 2).

**Si proyecto existente:**
- Tabla status (Topic, Research, Script, Flow Pack, Images, Voice, Assembly, Render)
- Tabs: Overview | Script | Flow Workspace | Images | Voice & Render

---

## Pantalla 2 — Create Documentary Project

**Subheader:** Create Documentary Project

| Input | Tipo | Default |
|-------|------|---------|
| Topic | text_input | placeholder WeWork |
| Title (optional) | text_input | vacío → usa topic |
| Target words | slider | 1500 (1000–2000) |
| Research notes | textarea | vacío |
| Sources (one per line) | textarea | vacío |
| Project id (optional) | text_input | auto `001-slug` |

**Button:** Create project (primary)

**On success:** redirect al proyecto creado.

---

## Pantalla 3 — Overview tab

- Workspace path (read-only)
- Topic (disabled textarea)
- Research notes (editable)
- Sources (editable)
- **Save research**

---

## Pantalla 4 — Script tab

**Buttons:**
- Generate script (LLM) — primary
- Generate mock script (offline)
- Approve script — disabled si script vacío

**Textarea:** Script (editable, height 360)

**Button:** Save script edits → limpia approval

**Caption:** Fact status + Approved

---

## Pantalla 5 — Flow Workspace tab

**Buttons (top):**
- Generate / refresh Flow Pack — **disabled** hasta script approved
- Flow Pack offline (no LLM beats)

**Si no flow_pack_ready:** info "Approve script, then generate Flow Pack."

**Si ready:**
- Expander **MASTER REFERENCES** (global style + CHAR/LOC/OBJ codes)
- Batch buttons BATCH_01… (max 6 visibles)
- **SHOT NNN** card: narration, references, continuity, shot type, expected file
- Prompt textarea + st.code blocks (copy manual)
- Previous / Next
- Mark generated | Mark approved | Needs regen
- Batch prompts quick scan (expanders)

---

## Pantalla 6 — Images tab

- Folder path (default `projects/<id>/flow-import`)
- **Bulk import** (primary)
- Report ready/missing
- Replace one shot: number + file_uploader + Replace shot

---

## Pantalla 7 — Voice & Render tab

- **Generate voice (continuous)** — primary
- Music path (optional text)
- Music volume slider 0.0–0.4 default 0.12
- Save audio settings
- Preview checks → JSON
- Checkbox allow missing images
- **Assemble + Render final.mp4** — primary
- Video player si existe `render/final.mp4`

---

## Estados / checkpoints visibles

Tabla en status panel refleja `project.json` checkpoints + import_report + voice duration.
