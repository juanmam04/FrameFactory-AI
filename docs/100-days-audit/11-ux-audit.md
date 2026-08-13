# 11 — UX actual

## Pantallas Streamlit (CONFIRMED `saas_ui.render_app`)

| Nav | Función |
|-----|---------|
| Dashboard | Métricas simples + lista proyectos |
| Create | Wizard 3 pasos → lanza render |
| Rendering | Progreso `.saas_render_progress.json` |
| Library | Proyectos JSON |
| Review | Guion/bloques/bundle; regen deshabilitada |
| Profile | Creative profile + chat memoria |

## Flujo principal hoy

1. Create paso 1: tema / ideas IA / auto-paquete / chat  
2. Paso 2: imágenes IA on/off, gameplay, voz, duración palabras, subs, música  
3. Paso 3: confirmar → Generar video  
4. Rendering (bloqueante, minutos)  
5. Review / Library  

## Qué pertenece al generador visual antiguo

- Toggle Replicate por escena  
- Catálogo personaje/fondo como “visual principal”  
- Ideas virales Reddit / dark confession  
- Gameplay Minecraft path (otro formato de canal)  

Útiles para **otro** producto; **no** para el docu 100-days.

## Qué sigue siendo útil

- Target words / voice speed / subs / música  
- Progress bar  
- Publication bundle en Review  
- Session memory / profile (si se retargetea a tono documental)  

## Fricción para 100 días

| Problema | Impacto |
|----------|---------|
| Demasiados clicks y opciones irrelevantes (gameplay, Reddit, Replicate) | Tiempo + error |
| Sin vista “Project Day 047” con checklist Research→Flow→Import→Render→YT | Caos |
| Sin import stills | Trabajo fuera de la app |
| Regen por bloque disabled | Rehacer todo |
| Output global sin workspace | Riesgo de pisar el video de ayer |
| Chat/perfil poderosos pero no orientados a facts | Distracción |

## Controles manuales importantes a conservar

- Editar/aprobar guion antes de visuals  
- Elegir voz y velocidad  
- On/off subtítulos y estilo  
- Música volume  
- Re-importar N shots malos (futuro)  

## Ideal UX mínima (concepto; no implementar aún)

Una sola página de proyecto con estados:  
`Topic → Script → Flow Pack → Import → Voice+Render → Package`.
