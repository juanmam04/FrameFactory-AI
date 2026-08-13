# 07 — Importación de Flow

## Estado actual del storage de imágenes (CONFIRMED)

| Pipeline | Convención | Relación |
|----------|------------|----------|
| Clásico | `output/imagenes/<proyecto>/escena_XXXX.png` | `FrameSpec.frame_id` / glob `escena_*.png` |
| SaaS apoyo | `output/saas_support_XXXX.png` | índice de bloque 1-based |
| RunPod batch script | `0001.png`… | **no** cableado a Studio |
| Catálogo | `assets/characters|backgrounds` | no es por escena |

## Capacidades existentes

| Capacidad | ¿Existe? | Evidencia |
|-----------|----------|-----------|
| Reusar imágenes sin regenerar | **Sí (clásico)** | `pipeline.run(skip_imagenes=True)` → `sorted(...glob("escena_*.png"))` |
| Upload UI / drag & drop | **No** | Sin `st.file_uploader`; catálogo dice sin uploads |
| Bulk import Flow | **No** | — |
| Replace por escena en UI | **No** | Review: regeneración “próximamente” |
| Validación faltantes | Parcial clásico | montaje falla/degrada si lista vacía; SaaS puede omitir apoyo |
| Multi-imagen por beat | No soportado limpiamente | Un PNG por escena/índice |

## Forma más simple y robusta (recomendación)

**Opción S (mínima, Video 1):**

1. Humano exporta de Flow como `001.png` … `N.png`.  
2. Script `flow_import` copia/renombra a `escena_0001.png` … bajo `output/imagenes/<project>/`.  
3. `pipeline.run(..., skip_imagenes=True)` o montaje directo `montar_video(lista_imagenes, audio)`.  
4. Validación: `assert count_png == count_escenas` y reportar faltantes.

**Opción T (Studio):**

1. Carpeta `flow-import/` en workspace del proyecto.  
2. Botón “Importar stills” que mapea `NNN.png` → bloque N.  
3. `render_block(..., support_image=full_frame_still)` o bypass personaje: still a pantalla completa.

Opción S es **menos código** y aprovecha path ya existente. Opción T mejora UX diaria (SHOULD HAVE Video 10).

## Qué necesita el renderer

- **Clásico `montar_video`:** lista ordenada de PNG + un MP3 (o audio) — CONFIRMED.  
- **SaaS `render_block`:** character PNG + optional support; para docu full-bleed, hay que tratar el still Flow como fondo/full frame (ADAPT menor).

## Validaciones mínimas post-import

1. Conteo N vs shots  
2. Dimensiones mínimas (p.ej. ≥1280px ancho)  
3. Archivos vacíos / corruptos  
4. Orden lexicográfico zero-padded (`001` not `1`)
