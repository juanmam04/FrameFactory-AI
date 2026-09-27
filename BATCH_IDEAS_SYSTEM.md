# Sistema de Batch de Ideas con Diversidad de Vehículos

## ¿Qué hace?

Cuando generás ideas en Check, el sistema ahora crea **5 conceptos de temas completamente diferentes** cada vez. Cada idea usa un "vehículo" distinto (músico, chef, atleta, emprendedor, etc.), garantizando máxima variedad.

## Cómo funciona

### 1. Generación Diversa

Cuando pedís ideas, el sistema:
1. Selecciona 5 vehículos diferentes del catálogo universal
2. Le dice al LLM: "generá 5 seeds, cada una con un vehicle_type DIFERENTE"
3. Asegura que cada idea sea de un tema único

### 2. Vehículos Asignados

El sistema usa el catálogo de `universal_vehicles.py` para asignar vehículos:

- 🏀 **Sports Team** - Dueño de equipo deportivo
- 🎵 **Musician** - Carrera musical
- 🎬 **Filmmaker** - Director de cine
- 👨‍🍳 **Chef** - Restaurante propio
- 📱 **Creator** - Creador de contenido
- 👗 **Fashion Designer** - Diseñador de moda
- 🏃 **Athlete** - Atleta profesional
- 📚 **Author** - Escritor bestseller
- 🎮 **Game Dev** - Desarrollador de videojuegos
- 🏠 **Real Estate** - Inversionista inmobiliario
- 🎨 **Artist** - Artista visual
- 📸 **Photographer** - Fotógrafo profesional
- 🎙️ **Podcaster** - Podcaster exitoso
- 🥊 **Fighter** - Peleador profesional
- 🎧 **DJ/Producer** - DJ/Productor
- 🎯 **E-Sports** - Jugador profesional
- 🏗️ **Architect** - Arquitecto

### 3. Preservación del Vehículo

El `vehicle_type` se preserva a través de todo el pipeline:

```
Seed (vehicle_type="musician")
  ↓
Story Core (vehicle_type="musician", + contexto específico)
  ↓
Package (vehicle_type="musician", vehicle_name="Músico Profesional")
  ↓
UI (🎵 Músico Profesional)
```

## Ejemplo de Batch

Cuando generás ideas, podés recibir algo como:

1. **🏀 Dueño de Equipo Deportivo** - Comprás equipo en quiebra, lo salvás
2. **🎵 Músico Profesional** - De bedroom producer a gira sold out
3. **👨‍🍳 Chef** - De cocinero a restaurante Michelin
4. **📱 Creador de Contenido** - De 100 subs a 1M y marca propia
5. **💼 Fundador de Empresa** - SaaS de 0 a adquisición millonaria

**Cada una de un tema completamente diferente.**

## UI Visual

En la interfaz de ideas, cada concepto muestra:
- Emoji identificador del vehículo
- Nombre del vehículo en etiqueta destacada
- Resto de info (score, categoría, coherencia)

```html
<span class="tag" style="background:var(--accent-light);font-weight:600">
  🎵 Músico Profesional
</span>
```

## Flujo de Usuario

1. Usuario toca **"Generar conceptos"**
2. Sistema genera 5 ideas de temas distintos (~1-3 min)
3. Usuario ve 5 tarjetas, cada una claramente etiquetada:
   - 🎵 Músico
   - 🎬 Filmmaker
   - 👨‍🍳 Chef
   - etc.
4. Usuario elige el que más le gusta ese día
5. Desarrolla ese concepto

## Ventajas

### Para el Usuario
- **Variedad garantizada**: Nunca recibís 5 ideas del mismo tema
- **Visual claro**: Emojis y etiquetas ayudan a identificar rápido
- **Elección real**: Podés elegir qué tipo de fantasía te interesa hoy

### Para el Sistema
- **Mejor calidad**: El LLM recibe contexto específico del vehículo
- **Menos repetición**: Diversidad forzada evita ideas similares
- **Escalable**: Fácil agregar nuevos vehículos al catálogo

## Código Técnico

### Modificaciones en `concepts.py`

```python
# En _llm_raw_seeds_once:

# Obtener vehículos disponibles
available_vehicles = list(UNIVERSAL_VEHICLES.keys())

# Seleccionar vehículos diversos para este batch
vehicle_pool = available_vehicles * ((count // len(available_vehicles)) + 1)
random.shuffle(vehicle_pool)
required_vehicles = vehicle_pool[:count]

# Pasar al LLM
user = {
    "required_vehicles": required_vehicles,
    "available_vehicles": vehicle_descriptions,
    "vehicle_diversity_rule": "CADA seed debe ser un vehicle_type DIFERENTE",
    # ...
}
```

### Preservación del Vehicle Type

```python
# En normalize_concept_package:
vehicle_type = str(raw.get("vehicle_type") or "business").strip()
out["vehicle_type"] = vehicle_type

# Agregar nombre descriptivo
if vehicle_type in UNIVERSAL_VEHICLES:
    out["vehicle_name"] = UNIVERSAL_VEHICLES[vehicle_type]["name"]
```

### Contexto al LLM

```python
# En _llm_story_from_seed:
vehicle_type = seed.get("vehicle_type", "business")
v_info = UNIVERSAL_VEHICLES[vehicle_type]
vehicle_context = (
    f"VEHICLE TYPE: {v_info['name']} - {v_info['vehicle']}. "
    f"Progresión típica: {v_info['progression']}. "
    f"Métricas relevantes: {', '.join(v_info['metrics'][:3])}."
)
```

## Testing

Para verificar que funciona:

```python
# Genera un batch de ideas
ideas = generate_concept_packages(profile, count=5)

# Verifica diversidad
vehicle_types = [idea["vehicle_type"] for idea in ideas]
assert len(set(vehicle_types)) == 5  # 5 vehículos únicos

# Verifica que cada una tiene vehicle_name
for idea in ideas:
    assert idea["vehicle_name"]
    assert idea["vehicle_type"]
```

## Agregar Nuevos Vehículos

Para agregar un nuevo tipo de fantasía al batch:

1. **Agregar a `universal_vehicles.py`**:

```python
UNIVERSAL_VEHICLES = {
    # ... existentes ...
    
    "tu_nuevo_vehiculo": {
        "name": "Nombre Descriptivo",
        "vehicle": "el vehículo específico",
        "acquisition": "cómo empieza",
        "progression": "unidades de tiempo",
        "metrics": ["métrica1", "métrica2"],
        "life_changes": ["cambio1", "cambio2"],
    },
}

VEHICLE_KEYWORDS = {
    # ... existentes ...
    
    "tu_nuevo_vehiculo": [
        "palabra clave 1",
        "frase que indica",
    ],
}
```

2. **Agregar emoji en `studio.js`**:

```javascript
const vehicleEmoji = {
  // ... existentes ...
  tu_nuevo_vehiculo: "🎭",  // emoji apropiado
};
```

3. **¡Listo!** El sistema automáticamente:
   - Lo incluye en la rotación de vehículos
   - Lo detecta de keywords
   - Lo muestra en UI con emoji

## Roadmap

### Próximas mejoras:
- [ ] Usuario puede especificar qué tipos de vehículos quiere en el batch
- [ ] Filtros en UI para ver solo ciertos tipos
- [ ] Historial de qué vehículos ya usó el usuario
- [ ] Recomendaciones de vehículos basadas en performance

---

**Desarrollado para FrameFactory Studio**
*"5 fantasías, 5 temas, tu elección"*
