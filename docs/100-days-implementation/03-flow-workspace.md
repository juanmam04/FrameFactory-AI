# 03 — Flow Workspace

UI tab **Flow Workspace** (after Flow Pack export):

1. **MASTER REFERENCES** — global style + CHAR/LOC/OBJ reference prompts  
2. **Batches** — default 10 shots (`batch_size` in project.json)  
3. Per shot: narration, references, continuity, shot type, prompt, expected file  
4. Mark: generated / approved / needs regen  
5. Previous / Next  

Copy UX: prompts shown in `st.code` blocks for quick select-all copy (Streamlit has no native clipboard API without components).

On disk: `flow-pack/shot-list.json`, `shots/NNN.txt`, `references/…`, `README.md`.
