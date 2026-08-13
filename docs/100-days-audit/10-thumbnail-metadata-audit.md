# 10 — Thumbnail y YouTube package

## Clásico — `metadata_youtube.py` (CONFIRMED)

| Entrega | Estado |
|---------|--------|
| Descripción | Sí (OpenAI + instrucciones YAML) |
| Capítulos | Sí, pero basados en `Escena.duracion_segundos` (no duración real TTS) |
| Tags | **No** campo estructurado |
| Título | vía `instrucciones_titulo.yaml` / flujo metadata |
| Miniatura imagen | `generar_miniatura()` → **siempre `None`** (DALL·E off) |
| Archivo | `output/metadata/{proyecto}_youtube.txt` |

## SaaS — `reddit_publication_bundle.py` (CONFIRMED)

| Entrega | Estado |
|---------|--------|
| `title` | Sí |
| `alt_titles` | Sí |
| `description` (+ hashtags en prompt) | Sí |
| `thumbnail.text` / `image_prompt` / `layout` | Sí (texto) |
| PNG thumbnail | **No** |
| Chapters | **No** |
| Persistencia | `saas_publication_bundle.json` + Review UI |

## `title_generator.py`

Orphan (cero importadores) — **DELETE LATER** o re-cablear.

## Qué conservar

- Generación de título + alternativas + descripción (adaptar tono a docu EN, no Reddit)  
- Thumbnail **prompt** → producir en Flow o Canva manualmente  
- Capítulos: recalcular desde duraciones reales de audio post-TTS  

## Qué no construir aún

Upload automático a YouTube API, A/B thumbnails masivos, CTR predictors.
