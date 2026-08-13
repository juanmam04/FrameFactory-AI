# 00 — Resumen ejecutivo

## Qué es FrameFactory HOY

Una app **Streamlit** (`app.py` → `saas_ui.render_app`) con **dos mundos en la misma UI**:

1. **Studio SaaS legacy** — Dashboard, Nuevo video, Render, Biblioteca, Perfil (Reddit/POV/Replicate/gameplay).
2. **Documentary 100 Days (MVP nuevo)** — nav **Documentary**, proyectos en `projects/<id>/`, imágenes externas vía Google Flow.

Para el reto de 100 videos/día, el camino operativo es **Documentary**, no Nuevo video.

## Respuesta crítica: Session ↔ Documentary

**NO** — Documentary **no** usa sesiones creativas, `creative_profile`, ni memoria de chat.  
Evidencia: cero imports/referencias en `src/documentary/*` (CONFIRMED grep).

El sidebar de sesiones sigue visible pero **no alimenta** el pipeline documental.

## Flujo usuario (Documentary) en una línea

Crear proyecto → research manual → generar/aprobar script EN → Flow Pack → Flow manual → bulk import PNGs → voz continua → assemble/render → `projects/<id>/render/final.mp4`.

## Gaps principales vs objetivo 100 días

- Sin generación de ideas/topic del día
- Sin research automático
- Sin conexión Session = Channel
- Sin subtítulos en Documentary
- Sin metadata/thumbnail YouTube en Documentary
- UX fragmentada en 5 tabs + Studio legacy visible
- Copy a Flow manual (st.code, no clipboard nativo)

## Reutilización útil

- `montar_video` + Ken Burns
- `generar_guion` plantilla `business_documentary_en`
- Stack visual beats → FrameSpec → prompts (sin gen imagen)
- Workspace + checkpoints por proyecto
