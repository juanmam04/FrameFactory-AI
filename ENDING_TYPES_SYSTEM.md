# Sistema de Endings Variados para Check ALS

## El Problema Anterior

Antes, **TODOS** los videos de Check terminaban igual:
```
Estadio vacío. Email: oferta de adquisición. Bloqueas. Mañana lo lees.
```

Mismo final una y otra vez. Predecible. Aburrido.

## La Solución: 8 Tipos de Endings

Ahora cada video puede tener un final **completamente diferente**:

### 1. 🏆 Victoria Total
**Logro máximo alcanzado**

```
Tienes 27 años.

Ganaste el campeonato. Copa en tus manos. Estadio vacío después del partido.

Hace 5 años estabas en una oficina compartiendo departamento con dos roommates.

Ahora sos campeón.

Ya lo lograste.

Ahora qué.
```

**Emoción**: 8/10 - Triunfo  
**Cuándo usar**: Campeonato ganado, exit millonario, imperio consolidado

---

### 2. 💰 Exit/Venta Exitosa
**Firmaste, vendiste, salís**

```
Tienes 28 años.

Firmaste. 35 millones de dólares por el 51%.

Google es el nuevo dueño.

Tu último día en la oficina. Apagas las luces. Cierras tu laptop.

Hace 6 años compraste esto con 8.000 dólares.

Ahora vale 70 millones.

Sales por última vez.
```

**Emoción**: 7/10 - Agridulce  
**Cuándo usar**: Adquisición, venta exitosa, cambio de ownership

---

### 3. 💔 Pérdida/Colapso
**Perdiste, cerró, quedó poco**

```
Tienes 29 años.

El equipo cerró. Deuda impagable. No hubo otra salida.

El estadio está vacío. Para siempre.

Hace 7 años compraste esto por un dólar. Pusiste todo.

Ahora solo quedan las fotos. Las memorias. La experiencia.

Perdiste.
```

**Emoción**: 3/10 - Derrota  
**Cuándo usar**: Quiebra, colapso, competidor te eliminó

---

### 4. ⚖️ Dilema Moral
**Dos opciones, decisión imposible**

```
Tienes 26 años.

Dos ofertas en la mesa.

Opción A: 40 millones, perdés control, te quedás con 15%.

Opción B: seguís dueño, deuda por 3 años más, riesgo real.

No podés elegir ambas.

Hace 4 años esto era simple: un equipo en crisis, una oportunidad.

Ahora dos caminos completamente distintos frente a ti.

Tenés hasta el viernes.

Decidís mañana.
```

**Emoción**: 6/10 - Tensión  
**Cuándo usar**: Decisiones críticas, caminos mutuamente excluyentes

---

### 5. ⚔️ Victoria Pírrica
**Ganaste pero el costo fue brutal**

```
Tienes 30 años.

Ganaste el campeonato. Sold out cada partido. El equipo está en la cima.

Pero tu matrimonio terminó hace 2 años. Tus hijos casi no te conocen.

En papel vales 50 millones de dólares.

En realidad: hace 5 años que no cenás con tu familia.

Hace 8 años querías el campeonato.

Ahora lo tenés.

Pero los años con tu familia no vuelven.
```

**Emoción**: 5/10 - Amargo  
**Cuándo usar**: Gran logro pero costo personal alto

---

### 6. 🔄 Final Irónico
**Conseguiste lo que querías, pero no como pensabas**

```
Tienes 27 años.

Querías ser dueño del equipo. Lo sos.

Pero el equipo ahora es tuyo y de 50 accionistas más.

La junta decide. Vos ejecutas. En tu propio equipo.

Hace 5 años imaginabas esto distinto. Dueño absoluto. Control total.

Ahora tenés el título. Pero no el control.

Resulta que "dueño" no significa lo que pensabas.
```

**Emoción**: 7/10 - Revelación  
**Cuándo usar**: Logro con twist, expectativa vs realidad

---

### 7. ❓ Final Abierto (Clásico)
**Oferta pendiente, decidís mañana**

```
Tienes 27 años.

El estadio está vacío después del partido. El personal ya se fue.

En tu teléfono: email. Oferta de adquisición.

Hace 5 años estabas en una oficina compartiendo departamento.

Ahora alguien quiere comprarte el equipo.

Bloqueas el teléfono.

Mañana lo lees.
```

**Emoción**: 6/10 - Suspenso  
**Cuándo usar**: Historia en curso, oportunidad nueva

---

### 8. 📊 Meseta/Nuevo Normal
**Ni peak ni colapso, esto es**

```
Tienes 29 años.

No campeonato. Pero playoffs cada año. 12.000 de asistencia promedio. Rentable.

Hace 7 años querías el anillo.

No llegaste ahí.

Pero tampoco fracasaste.

El equipo paga las cuentas. Los fans llenan la mitad del estadio. Jugás playoffs.

Esto es. No más. No menos.
```

**Emoción**: 6/10 - Realista  
**Cuándo usar**: Estabilidad sin extremos, éxito moderado

---

## Cómo Funciona el Sistema

### 1. Generación de Ideas

Cuando generás 5 ideas, el sistema asigna automáticamente 5 endings diferentes:

```python
# En concepts.py - asignación automática
ending_types = ["victory", "exit", "loss", "dilema", "pyrrhic"]
random.shuffle(ending_types)

# Cada seed recibe un ending distinto
seed_1.ending_type = "victory"   # 🏆
seed_2.ending_type = "exit"      # 💰
seed_3.ending_type = "loss"      # 💔
seed_4.ending_type = "dilema"    # ⚖️
seed_5.ending_type = "pyrrhic"   # ⚔️
```

### 2. Preservación del Ending

El `ending_type` se preserva a través de todo el pipeline:

```
Seed (ending_type="victory")
  ↓
Story Core (construye hacia victoria)
  ↓
Package (ending_type="victory", ending_name="Victoria Total")
  ↓
Project (ending_type="victory")
  ↓
Script Generation (usa prompt específico de victoria)
```

### 3. Prompts Específicos por Ending

Cada ending tiene su propio prompt template:

```python
# En script.py
ending_type = facts.get("ending_type", "open")
if ending_type != "open":
    ending_prompt = get_ending_prompt(ending_type, facts)
    master_prompt = master_prompt + "\n\n" + ending_prompt
```

El LLM recibe instrucciones específicas:
- **Victory**: "Incluye el logro máximo, contraste, 'Ya lo lograste. Ahora qué.'"
- **Exit**: "Incluye firma, número, último día, 'Sales por última vez.'"
- **Loss**: "Incluye pérdida explícita, contraste con peak, 'Solo queda...'"
- etc.

### 4. UI Visual

En la interfaz, cada concepto muestra su ending con emoji:

```
🎵 Músico Profesional  |  🏆 Victoria Total
🎬 Filmmaker           |  💰 Exit/Venta
👨‍🍳 Chef                |  💔 Pérdida
📱 Creator             |  ⚖️ Dilema
💼 Business            |  ⚔️ Victoria Pírrica
```

## Ejemplos por Vehículo

### Músico + Victory
```
Sold out mundial. Arena vacía después del último show.
Ya lo lograste. Ahora qué.
```

### Chef + Exit
```
Firmaste. Grupo hotelero compra tu restaurante por 8 millones.
Tu último servicio. Apagas la cocina.
Sales por última vez.
```

### Filmmaker + Loss
```
La película no funcionó. El estudio canceló el contrato.
Solo quedan las críticas. La experiencia.
Perdiste.
```

### Creator + Dilema
```
Opción A: Deal con plataforma, 5M pero pierdes ownership de contenido.
Opción B: seguís indie, control total, riesgo real.
Decidís en 48 horas.
```

### Business + Pyrrhic
```
50M en el banco. Empresa exitosa.
Pero hace 3 años que no ves a tu familia.
Los años no vuelven.
```

## Validación de Endings

El sistema valida que el script cumpla con su ending_type:

```python
# En ending_types.py
def validate_ending(script_text: str, ending_type: str):
    ending_section = script_text[-400:]
    
    if ending_type == "victory":
        if "ganaste" not in ending_section:
            issues.append("Final victoria debe incluir el logro")
    
    elif ending_type == "exit":
        if "firmaste" not in ending_section:
            issues.append("Final exit debe incluir la venta")
    
    # etc.
```

## Distribución de Endings

### Batch de 5 Ideas

Distribución típica balanceada:
- 1x Victory (común)
- 1x Exit (común)
- 1x Dilema (genera tensión)
- 1x Pyrrhic o Ironic (twist)
- 1x Loss, Open, o Plateau (variedad)

### Weights por Tipo

```python
weights = {
    "victory": 2,    # Más común
    "exit": 2,       # Más común
    "dilema": 2,     # Genera tensión
    "open": 1,       # Clásico
    "pyrrhic": 1,    # Twist
    "ironic": 1,     # Twist
    "loss": 1,       # Menos común
    "plateau": 1,    # Menos común
}
```

## Reglas Universales (Todos los Endings)

**PROHIBIDO en todos**:
- ❌ Moraleja
- ❌ Lección ("aprendiste que")
- ❌ CTA (suscríbete, like, comenta)
- ❌ Voseo (vos, sos, tenés)

**OBLIGATORIO en todos**:
- ✅ Edad final
- ✅ Contraste temporal (hace X años estabas...)
- ✅ Específico y concreto
- ✅ Sin fluff emocional

## Testing

Para verificar el sistema:

```python
from src.documentary.formats.check_als.ending_types import ENDING_TYPES, get_ending_prompt

# Ver todos los endings disponibles
for key, info in ENDING_TYPES.items():
    print(f"{key}: {info['name']} - {info['emotion']}")

# Generar prompt para un ending
facts = {...}
prompt = get_ending_prompt("victory", facts)
print(prompt)

# Validar un script
script = "..."
is_valid, issues = validate_ending(script, "victory")
```

## Agregar Nuevos Endings

Para agregar un nuevo tipo de ending:

1. **Editar `ending_types.py`**:

```python
ENDING_TYPES = {
    # ... existentes ...
    
    "tu_nuevo_ending": {
        "name": "Nombre Descriptivo",
        "emotion": "X/10 - Emoción",
        "structure": [
            "Paso 1",
            "Paso 2",
            "etc.",
        ],
        "template": """Template del ending...""",
        "examples": ["Ejemplo 1", "Ejemplo 2"],
    },
}
```

2. **Agregar emoji en `studio.js`**:

```javascript
const endingEmoji = {
  // ... existentes ...
  tu_nuevo_ending: "🎭",
};
```

3. **Actualizar validación** (opcional):

```python
def validate_ending(script_text: str, ending_type: str):
    if ending_type == "tu_nuevo_ending":
        if "palabra_clave" not in ending_section:
            issues.append("Debe incluir X")
```

## Roadmap

### Próximas mejoras:
- [ ] Usuario puede especificar qué ending quiere
- [ ] Sugerencia automática de ending según historia
- [ ] Endings contextuales (si hay campeonato → victoria/loss/pyrrhic)
- [ ] Análisis de qué endings performan mejor

---

**Desarrollado para FrameFactory Studio**
*"8 tipos de finales, infinitas historias"*
