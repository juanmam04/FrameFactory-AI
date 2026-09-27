# Check ALS - Sistema Universal de Vehículos

## ¿Qué cambió?

Check ahora puede generar fantasías aspiracionales de **cualquier tema**, no solo deportes o negocios tradicionales.

### Antes
- Solo `sports_team` (equipo de básquet)
- Solo `business` (empresa/startup genérica)

### Ahora
- ✅ `musician` - Carrera musical
- ✅ `filmmaker` - Director de cine
- ✅ `chef` - Restaurante propio
- ✅ `creator` - Creador de contenido
- ✅ `fashion_designer` - Diseñador de moda
- ✅ `athlete` - Atleta profesional
- ✅ `author` - Escritor bestseller
- ✅ `game_dev` - Desarrollador de videojuegos
- ✅ `real_estate` - Inversionista inmobiliario
- ✅ `artist` - Artista visual
- ✅ `photographer` - Fotógrafo profesional
- ✅ `podcaster` - Podcaster exitoso
- ✅ `fighter` - Peleador profesional
- ✅ `dj_producer` - DJ/Productor
- ✅ `esports_player` - Jugador de e-sports
- ✅ `architect` - Arquitecto
- **...y cualquier otro que agregues**

## Cómo funciona

### 1. Detección Automática

El sistema detecta automáticamente el tipo de fantasía basándose en keywords:

```python
from src.documentary.formats.check_als.story_vehicle import vehicle_mode

# Detecta el vehículo del proyecto
mode = vehicle_mode(project)
# Retorna: "musician", "chef", "filmmaker", etc.
```

### 2. Prompts Adaptativos

Cada vehículo tiene su propia estructura de beats:

```python
from src.documentary.formats.check_als.universal_vehicles import get_vehicle_structure

# Obtiene la estructura específica del vehículo
structure = get_vehicle_structure("musician")
# Retorna: beats, métricas, cambios de vida específicos de músicos
```

### 3. Script Generation

El generador de scripts usa automáticamente el vehículo correcto:

```python
# En script.py - ya integrado
mode = vehicle_mode(project)  # "musician"
facts = locked_story_facts(arch, mode=mode)
master_prompt = get_check_master_prompt(facts, vehicle_mode=mode)
# Genera script con contexto de músico
```

## Agregar un Nuevo Vehículo

### Paso 1: Definir el Vehículo en `universal_vehicles.py`

```python
UNIVERSAL_VEHICLES = {
    # ... vehículos existentes ...
    
    "your_new_vehicle": {
        "name": "Nombre Descriptivo",
        "vehicle": "el vehículo (ej: banda de rock, estudio de diseño)",
        "acquisition": "cómo empieza (ej: firmar primer contrato)",
        "progression": "unidades de tiempo (ej: álbumes/giras, años/proyectos)",
        "metrics": ["métrica1", "métrica2", "métrica3"],
        "life_changes": ["cambio1", "cambio2", "cambio3"],
    },
}
```

### Paso 2: Agregar Keywords de Detección

```python
VEHICLE_KEYWORDS = {
    # ... existentes ...
    
    "your_new_vehicle": [
        "palabra clave 1",
        "palabra clave 2",
        "frase que indica este vehículo",
    ],
}
```

### Paso 3: ¡Listo!

El sistema automáticamente:
- Detecta el vehículo cuando los usuarios escriben esas keywords
- Genera prompts adaptados a ese contexto
- Valida scripts con reglas apropiadas
- Crea historias con progresión específica del dominio

## Ejemplos de Uso

### Músico
```
Premise: "Quiero ser un músico famoso que firma con una disquera"
→ Detecta: musician
→ Genera: Historia de álbumes, giras, streams, premios
→ Beats: Primer contrato → Primer álbum → Primera gira → Sold out
```

### Chef
```
Premise: "Abrir un restaurante y conseguir estrella Michelin"
→ Detecta: chef
→ Genera: Historia de restaurante, clientes, críticas, estrellas
→ Beats: Primer restaurante → Reservas llenas → Crítica positiva → Michelin
```

### Creador de Contenido
```
Premise: "Ser youtuber exitoso con millones de subs"
→ Detecta: creator
→ Genera: Historia de canal, subs, sponsors, marca propia
→ Beats: Primer viral → 100k subs → Sponsors → 1M subs
```

## Estructura de Beats Universal

Todos los vehículos siguen la misma estructura narrativa de 10 beats:

1. **Cold Open** (0:00-0:30): Edad + situación + oportunidad
2. **Acquisition** (0:30-2:00): Cómo empiezas + tu % o control
3. **Grind** (2:00-4:00): Primeros meses duros
4. **First Win** (4:00-5:30): Primera tracción real
5. **Progression** (5:30-8:00): Años de crecimiento
6. **Life Changes** (8:00-9:30): Mudanza, renuncia, familia
7. **Peak** (9:30-11:00): ≥3 beats sensoriales de éxito
8. **Ironía Cash** (después del peak): Papel=$X millones, Cuenta=$Y bajo
9. **Ending** (11:00-12:00): Escena final + oferta + "Mañana lo lees"

## Métricas por Vehículo

Cada vehículo tiene métricas específicas que el script debe mencionar:

- **Musician**: streams, conciertos, tours sold out, premios
- **Chef**: reservas, críticas, estrellas Michelin, expansión
- **Creator**: suscriptores, views, sponsors, revenue mensual
- **Filmmaker**: box office, festivales, premios, presupuestos
- **Athlete**: rankings, torneos ganados, sponsors, récords

## Validación Adaptativa

El sistema de validación se adapta automáticamente:

```python
# Sports team: valida deuda, ownership 51%, temporadas
# Musician: valida álbumes, streams, no mezclar con deportes
# Chef: valida restaurante, clientes, no inventar playoffs
```

## Progresión Temporal

Cada vehículo usa unidades naturales:

- **Sports team**: temporadas (Temporada 1, 2, 3...)
- **Musician**: álbumes/giras (Primer álbum, primera gira...)
- **Business**: años (Año 1, 2, 3...)
- **Filmmaker**: películas (Primera película, segundo proyecto...)

## Life Changes Específicos

Cada vehículo tiene cambios de vida relevantes:

**Músico**:
- Dejar trabajo día → Primer tour
- Departamento compartido → Casa propia
- Abrir conciertos → Headliner
- Bedroom studio → Estudio profesional

**Chef**:
- Cocinar para otros → Restaurante propio
- Menú limitado → Menú completo
- Local chico → Multiple locations
- Sin estrella → Primera Michelin

## Testing

Para probar un nuevo vehículo:

```python
# En consola Python
from src.documentary.formats.check_als.universal_vehicles import detect_vehicle_type

# Test detección
premise = "Quiero ser músico famoso con disquera"
vehicle = detect_vehicle_type(premise)
print(vehicle)  # → "musician"

# Test estructura
from src.documentary.formats.check_als.universal_vehicles import get_vehicle_structure
structure = get_vehicle_structure(vehicle)
print(structure["vehicle_info"])
print(structure["beat_structure"])
```

## Archivos Modificados

- ✅ `universal_vehicles.py` - Nuevo: catálogo de vehículos
- ✅ `story_vehicle.py` - Actualizado: detección universal
- ✅ `storytelling_check.py` - Actualizado: prompts universales
- ✅ `script.py` - Actualizado: generación adaptativa
- ✅ `story_architect.py` - Compatible: usa vehicle_mode()
- ✅ `story_sim.py` - Compatible: usa vehicle_mode()

## Roadmap

### Próximos vehículos sugeridos:
- Político / Campaña electoral
- Escritor de series / Showrunner
- Fashion model / Supermodelo
- YouTuber educativo / Divulgador
- Inversionista cripto / Trader
- Fundador de ONG / Activista
- Científico / Investigador
- Piloto comercial / Aviación
- Sommelier / Wine expert
- Personal trainer / Fitness influencer

## Mantenimiento

Para mantener el sistema:

1. **Agregar vehículos nuevos**: Solo edita `UNIVERSAL_VEHICLES` y `VEHICLE_KEYWORDS`
2. **Ajustar beats**: Modifica `get_vehicle_structure()`
3. **Cambiar prompts**: Edita templates en `universal_vehicles.py`
4. **Test de detección**: Verifica keywords en `VEHICLE_KEYWORDS`

---

**Desarrollado para FrameFactory Studio - Check ALS Format**
*"Infinitos tipos de videos, todos los temas"*
