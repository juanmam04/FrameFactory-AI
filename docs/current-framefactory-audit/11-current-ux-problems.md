# 11 — Problemas UX actuales

Evaluación desde la perspectiva de un creador no técnico que debe producir **1 video/día durante 100 días**.

---

## 1. Dos productos en una sola app

Sidebar muestra Dashboard, Nuevo video, Render, Biblioteca, Perfil, **Sesión de trabajo** — todo orientado al Studio Reddit/POV. Documentary es **un tab más** sin ocultar el legacy.

**Impacto:** confusión sobre qué camino usar; riesgo de crear en el modo equivocado.

---

## 2. Session / Creative Profile desconectado

El usuario puede pasar 10 minutos configurando el canal en Perfil → Asistente ("documentales EN de negocios…") y **Documentary no lo ve**.

**Impacto:** duplicación de intención; sensación de que FrameFactory "no recuerda" el canal.

---

## 3. Sin "próximo video del día"

No hay botón "Create today's video", contador 12/100, ni generador de ideas compatibles con el canal.

**Impacto:** cada día empieza en blanco: pensar topic, escribir research, crear proyecto manualmente.

---

## 4. Research 100% manual sin guía

Overview pide research notes y sources sin estructura, sin plantilla, sin asistente.

**Impacto:** fricción alta; usuarios no técnicos no saben qué nivel de detalle escribir antes del script.

---

## 5. Cinco tabs = context switching

Overview → Script → Flow → Images → Voice & Render. No hay wizard lineal ni "siguiente paso" prominente.

**Impacto:** fácil olvidar aprobar script, importar imágenes, o renderizar; status panel ayuda pero no guía acción.

---

## 6. Terminología técnica expuesta

- `flow-import`, `project id`, `fact_check_status`, `Flow Pack offline (no LLM beats)`
- Checkpoints como tabla markdown cruda
- Workspace path en filesystem

**Impacto:** sensación de herramienta de desarrollador, no de estudio diario.

---

## 7. Copy a Google Flow incómodo

Prompts en `st.code` — seleccionar manualmente y ⌘C. Sin clipboard API. Prompt textarea no persiste edits.

**Impacto:** cientos de copias por video (60+ shots); error humano frecuente.

---

## 8. Flow Workspace no refleja progreso real

Mark generated/approved es manual; no sabe si `001.png` existe en disco hasta tab Images.

**Impacto:** doble tracking (status botones + import); desincronización.

---

## 9. Inputs que FrameFactory debería inferir

| Campo | Hoy | Debería |
|-------|-----|---------|
| Language | hardcoded `en` | heredar de Session |
| Target words | slider cada proyecto | default canal 1500 |
| Title | opcional manual | derivar de topic |
| Project id | opcional técnico | auto secuencial 001, 002… |
| Music path | path crudo | picker o default canal |
| Batch size | 10 fijo en JSON | oculto en Advanced |

---

## 10. Sin metadata / thumbnail / subtítulos

Pipeline termina en `final.mp4`. No título YouTube, descripción, tags, thumbnail.

**Impacto:** pasos post-producción fuera de FrameFactory; rompe flujo "DONE" del reto diario.

---

## 11. Aprobación de script frágil

"Save script edits" **limpia approval** sin advertencia clara de que invalida Flow Pack downstream (Flow Pack button disabled pero pack viejo en disco).

**Impacto:** riesgo de mezclar script nuevo con shots viejos.

---

## 12. Sesiones sidebar confunden con proyectos Documentary

Select "Sesión de trabajo" vs select "Project" — conceptos paralelos sin relación.

**Impacto:** "¿Cuál es mi sesión de documentales?" — no existe.

---

## 13. Errores de voz bloqueantes sin fallback claro

Sin API keys → RuntimeError. Correcto técnicamente; UX no explica qué variable `.env` configurar antes del día 1.

---

## 14. Preview checks es JSON crudo

Botón útil pero muestra `st.json` — no traduce a "faltan 3 imágenes, click aquí".

---

## Resumen: top 10 para el usuario

1. Studio legacy visible y confuso  
2. Session/Profile no conectado a Documentary  
3. Sin ideas/topic del día  
4. Research manual sin asistencia  
5. 5 tabs sin wizard  
6. Copy Flow manual repetitivo  
7. Terminología técnica  
8. Progreso Flow vs import desincronizado  
9. Sin metadata/thumbnail/subtítulos  
10. Inputs repetidos cada proyecto (words, id, etc.)
