# 14 — Runbook exacto: Video 1 hoy

Workflow **real** con la UI actual. Ejemplo: primer documental WeWork.

**Prerrequisitos:**
- `./run.sh` o `npm run dev`
- `.env` con `OPENAI_API_KEY` (script + TTS fallback) y/o `ELEVENLABS_API_KEY`
- Google Flow abierto en otra pestaña
- ~2–4 horas primera vez (Flow manual dominante)

---

## 1. Arrancar

```bash
cd FrameFactory-AI
./run.sh
```

Browser → `http://localhost:8501`

---

## 2. Entrar a Documentary

**Sidebar → click "Documentary"**

Ves: hero "Documentary", subtítulo 100 Days, select **Project** = `— new —`

---

## 3. Crear proyecto

Form **Create Documentary Project:**

| Campo | Valor ejemplo |
|-------|---------------|
| Topic | `The Rise and Fall of WeWork` |
| Title | (vacío) |
| Target words | `1500` |
| Research notes | Hechos verificados: fundadores, SoftBank, IPO 2019 fallido. Marcar UNKNOWN donde falte dato. |
| Sources | URLs o referencias, una por línea |
| Project id | `001-wework` (opcional) |

**Click: Create project**

→ Redirect a proyecto. Status panel: Topic ✓, resto ○

---

## 4. Research (opcional edit)

Tab **Overview** → ajustar notes/sources → **Save research**

---

## 5. Script

Tab **Script**

**Click: Generate script (LLM)** — esperar spinner

Revisar textarea **Script (editable)** (~1500 words EN)

Si OK → **Click: Approve script**

Status: Script ✓ APPROVED

⚠️ Si editas después → **Save script edits** → approval se pierde; regenerar Flow Pack.

---

## 6. Flow Pack

Tab **Flow Workspace**

**Click: Generate / refresh Flow Pack** — esperar visual director

Status: Flow Pack ✓ N shots

---

## 7. Master References en Flow

Expander **MASTER REFERENCES:**

1. Copiar **Global style** → Flow → generar mood board / style ref (guardar externamente)
2. Por cada CHAR_*, LOC_*, OBJ_*: copiar bloque `st.code` → generar reference en Flow

*(FrameFactory no importa refs — solo texto)*

---

## 8. Shots en Flow (loop)

1. Click **BATCH_01** (shots 001–010)
2. Shot **001** visible:
   - Leer Narration
   - Copiar de **st.code** "Copy Prompt" (⌘C manual)
   - Pegar en Google Flow → generar imagen
   - Descargar como `001.png`
3. **Click: Mark generated** (auto-advance Next)
4. Repetir 002…010
5. **BATCH_02** … hasta último shot

Guardar todos PNG en:

```text
projects/001-wework/flow-import/
```

*(mkdir si no existe)*

---

## 9. Import imágenes

Tab **Images**

- Folder: `projects/001-wework/flow-import` (default)
- **Click: Bulk import**

Esperar: `N / N READY`

Si missing → generar en Flow → re-import

---

## 10. Voz

Tab **Voice & Render**

**Click: Generate voice (continuous)**

Esperar → Status Voice ✓ con duración MM:SS

Opcional: Music path + volume → **Save audio settings**

---

## 11. Preview (opcional)

**Click: Preview checks** → revisar JSON (image_count, voice_ok, seconds_per_image)

---

## 12. Render

**Click: Assemble + Render final.mp4**

Esperar FFmpeg → player con video

Archivo final:

```text
projects/001-wework/render/final.mp4
```

Status: Assembly ✓, Render ✓ final.mp4

---

## 13. Qué NO hace FrameFactory hoy

- No genera thumbnail YouTube
- No exporta título/descripción/tags
- No quema subtítulos (aunque `subtitles_enabled: true` en JSON)
- No publica a YouTube
- No valida factualidad automáticamente

---

## 14. Día 2 (hoy)

Repetir desde paso 3 con nuevo topic. **No hay** "Create today's video" ni ideas automáticas.

Select Project → `— new —` → nuevo formulario.

---

## Checklist rápido

```text
□ Documentary nav
□ Create project (topic + research)
□ Generate script → Approve
□ Generate Flow Pack
□ Flow: master refs + all shots → PNGs en flow-import/
□ Bulk import
□ Generate voice
□ Assemble + Render
□ final.mp4 en projects/<id>/render/
```

---

## Tiempos orientativos (video 8–12 min, ~60 shots)

| Etapa | Tiempo |
|-------|--------|
| Research + script | 30–60 min |
| Flow Pack gen | 2–5 min |
| Flow manual (60 imgs) | 1.5–3 h |
| Import + voice + render | 10–20 min |

**Cuello de botella:** Google Flow manual + copy prompts.
