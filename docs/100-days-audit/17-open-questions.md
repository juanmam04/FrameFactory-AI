# 17 — Preguntas abiertas

## Producto / editorial

1. ¿El Video 1 será **100% stills documentales** o acepta B-roll de stock además de Flow?  
2. ¿Idioma final del canal: **solo inglés**? (hoy plantillas y UI están en ES.)  
3. ¿Cuántas imágenes por minuto objetivo? (influye N de Flow y duración por still.)  
4. ¿Hay voice ID ElevenLabs definitivo en EN para el canal?  
5. ¿Research: el humano aporta notes siempre, o se prioriza tool de sources en Video 10?

## Técnico

6. ¿Preferís path **clásico `montar_video`** o **adaptar SaaS MVP** como UI diaria?  
7. ¿Workspace solo filesystem o también SQLite `web/`?  
8. ¿Se rota/limpia ya `.env.example` con secrets (P0-008)?  
9. ¿Google Flow exporta con qué naming real (001 vs shot_01)?  
10. ¿Cuántos minutos máximos de render aceptables en MacBook Air del operador?

## UNKNOWN (sin evidencia en repo)

- Uso real diario actual de FastAPI `web/` vs solo Streamlit.  
- Si HeyGen está en uso productivo o solo experimental.  
- Pricing actual de Flow / ElevenLabs / OpenAI del operador.  
- Si existe proceso editorial externo (docs fuera del repo).

## Decisión requerida antes de codear

Aprobación explícita de:

1. MUST HAVE M1–M6 (`15-minimal-implementation-plan.md`)  
2. Path de render elegido (clásico vs SaaS)  
3. No-integración de Flow (manual forever para Video 1–10)
