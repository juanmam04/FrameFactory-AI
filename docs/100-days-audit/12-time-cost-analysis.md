# 12 — Tiempo humano y costos

## Estimación HOY (sin cambios) — 1 video 8–12 min docu business

| Fase | Horas (aprox.) | Notas |
|------|----------------|-------|
| Research | 1.5–3.0 | 100% humano; tool no ayuda |
| Script | 1.0–2.0 | LLM genera POV/ES; reescritura fuerte a EN factual |
| Review script | 0.5–1.0 | Facts |
| Storyboard | 1.0–2.0 | Manual; beats existen solo en CLI |
| Flow preparation | 0.5–1.5 | Sin pack export |
| Flow generation | 1.0–2.5 | Externo |
| Image import | 0.5–1.0 | Rename manual / frágil |
| Voice | 0.1–0.3 | Automático si path OK |
| Edit | 0.5–1.5 | Pocas palancas; a menudo re-render completo |
| Render | 0.2–0.5 | FFmpeg |
| Thumbnail | 0.3–0.8 | Prompt sí / PNG no |
| Upload prep | 0.2–0.4 | Copy/paste metadata |
| **Total** | **~8–14 h** | **No cumple <4 h** |

## Con MUST HAVE (ver plan) — Video 1

| Fase | Horas |
|------|-------|
| Research (humano + notes) | 0.75–1.25 |
| Script + review | 0.75–1.25 |
| Flow pack (auto) + tweak | 0.25–0.5 |
| Flow generation | 1.0–1.75 |
| Bulk import | 0.1–0.2 |
| Voice+render | 0.2–0.4 |
| Fix 3–5 shots | 0.4–0.8 |
| Thumb/title | 0.3–0.5 |
| **Total** | **~3.5–6 h** |

Objetivo <4 h: alcanzable hacia Video 5–10 con práctica + plantillas.  
Objetivo <2 h: requiere research ligero reutilizable + Flow fluency + pocos fixes.

## 5 mayores cuellos de botella

1. Research + anti-alucinación (humano)  
2. Tiempo en Google Flow  
3. Falta de Flow Pack / import  
4. Re-render completo ante errores  
5. Empaquetado thumbnail/YT incompleto  

## Costos de servicios (repo)

| Proveedor | Dónde | Pricing en repo |
|-----------|-------|-----------------|
| OpenAI | Guion, planners, metadata, VLM, chat, TTS fallback | **REQUIRES CURRENT PRICING CHECK** |
| ElevenLabs | TTS | **REQUIRES CURRENT PRICING CHECK** |
| Replicate | Imágenes (a deprecar) | **REQUIRES CURRENT PRICING CHECK** |
| HeyGen | Avatar opcional | **REQUIRES CURRENT PRICING CHECK** |
| ComfyUI/RunPod | GPU | **REQUIRES CURRENT PRICING CHECK** |
| Tokens internos SaaS | `SAAS_TOKEN_COST_PER_VIDEO=500` | No USD |
| Google Flow | Externo manual | Fuera del repo — **REQUIRES CURRENT PRICING CHECK** |
| FFmpeg | Local | $0 |

### Desperdicio potencial (CONFIRMED/INFERRED)

- N intentos/frame en `frame_image_pipeline` (`ATTEMPTS_PER_FRAME` default 4)  
- Reddit: 100–180 TTS calls  
- Review regenera guion si falta meta  
- Renders fallidos sin resume  

Con Flow + skip gen interna, coste diario debería concentrarse en **OpenAI (guion/meta) + ElevenLabs (1 narración o pocos chunks) + Flow**.
