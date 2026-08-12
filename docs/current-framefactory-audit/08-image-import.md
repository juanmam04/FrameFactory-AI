# 08 — Import de imágenes

## UI (CONFIRMED `documentary_ui._tab_images`)

- **Folder path** text_input — default `projects/<id>/flow-import`
- **Bulk import** button
- Report: `ready / expected`, missing list, st.json full report
- **Replace one shot:** number_input + file_uploader + Replace shot

**No hay:** drag-drop folder nativo; usás path a carpeta en disco.

## Naming esperado

Regex: `^(\d{1,4})\.(png|jpg|jpeg|webp)$`

Ejemplos válidos: `001.png`, `1.png`, `067.jpg`

Destino interno: **siempre** `projects/<id>/images/NNN.png` (zero-padded 3)

## Asociación

`001.png` → shot number 1 → `SHOT_001` en shot-list.json

Orden render: shot-list order, not filesystem order.

## Validación (`import_images`)

| Check | Comportamiento |
|-------|----------------|
| Missing | nums in shot-list sin archivo |
| Duplicates | mismo num twice in source |
| Unknown numbers | num not in shot-list (listed, skipped) |
| Invalid names | image files not matching pattern |
| Dimensions | PIL: width < 640; portrait flagged |

**No bloquea** import por dimensiones — solo reporta.

## Replace shot

`replace_shot_image(project, n, path)`:
- Overwrites `images/NNN.png`
- Updates missing list in import_report
- Clears `assembly_ready`, `render_ready`
- **Does NOT** invalidate voice

## Qué pasa con 001.png internamente

1. Scan source dir
2. Match regex → num=1
3. `shutil.copy2` → `projects/<id>/images/001.png`
4. Compare vs expected_nums from shot-list
5. Update `project.import_report` + checkpoint `images_imported`
