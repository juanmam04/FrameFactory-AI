# Auditoría FrameFactory — Reto 100 videos / 100 días

**Fecha:** 2026-08-12  
**Alcance:** solo lectura / documentación. Sin cambios de producto.  
**Pregunta central:** ¿cuál es el camino más corto desde el FrameFactory de hoy hasta publicar un documental diario de 8–12 min usando Google Flow manualmente para las imágenes?

## Índice

| Doc | Contenido |
|-----|-----------|
| [00-executive-summary.md](./00-executive-summary.md) | Veredicto y números clave |
| [01-repository-map.md](./01-repository-map.md) | Mapa del repo y call graph |
| [02-current-pipeline.md](./02-current-pipeline.md) | Pipeline real paso a paso |
| [03-visual-system-audit.md](./03-visual-system-audit.md) | Motor visual KEEP/ADAPT/DEPRECATE |
| [04-script-research-audit.md](./04-script-research-audit.md) | Guiones y research |
| [05-story-bible-readiness.md](./05-story-bible-readiness.md) | Story Bible |
| [06-flow-pack-design.md](./06-flow-pack-design.md) | Flow Pack mínimo viable |
| [07-flow-import-audit.md](./07-flow-import-audit.md) | Importación de imágenes Flow |
| [08-voice-audit.md](./08-voice-audit.md) | Narración / TTS |
| [09-render-editing-audit.md](./09-render-editing-audit.md) | FFmpeg / montaje |
| [10-thumbnail-metadata-audit.md](./10-thumbnail-metadata-audit.md) | YouTube package |
| [11-ux-audit.md](./11-ux-audit.md) | UX Studio |
| [12-time-cost-analysis.md](./12-time-cost-analysis.md) | Tiempo humano y costos |
| [13-reliability-risks.md](./13-reliability-risks.md) | Riesgos 100 días (P0–P3) |
| [14-do-not-build.md](./14-do-not-build.md) | Qué no construir |
| [15-minimal-implementation-plan.md](./15-minimal-implementation-plan.md) | Plan mínimo Video 1 |
| [16-daily-workflow.md](./16-daily-workflow.md) | Día ideal realista |
| [17-open-questions.md](./17-open-questions.md) | Preguntas abiertas |

## Leyenda de evidencia

- **CONFIRMED** — comprobado en código
- **INFERRED** — deducido con evidencia parcial
- **UNKNOWN** — sin evidencia suficiente

## IDs de hallazgos

Formato: `FF100-P{0-3}-NNN` — ver [13-reliability-risks.md](./13-reliability-risks.md).
