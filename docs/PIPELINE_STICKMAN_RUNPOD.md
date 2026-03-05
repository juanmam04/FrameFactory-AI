# Pipeline real: stickman 2D para videos (RunPod + ComfyUI + LoRA)

Objetivo: generar **~240 imágenes** por video (20 min, 1 imagen cada 5 s), estilo stickman 2D consistente, con LoRA entrenado por vos. Todo en **/workspace** para no reventar el disco.

---

## A) Arreglo de espacio en disco (OBLIGATORIO)

El volumen `overlay` tiene ~5 GB y se llena con pip/curl. Hay que mandar todo a `/workspace`.

**Si estás en RunPod y NO tenés el repo FrameFactory:** los archivos `scripts/runpod_workspace_env.sh` y `docs/` solo existen en tu repo local. En el Pod ejecutá únicamente los bloques de comandos de abajo (copiá y pegá en la terminal del Pod).

### Comandos exactos (ejecutar en el Pod)

```bash
# Crear estructura en /workspace
mkdir -p /workspace/tmp
mkdir -p /workspace/.cache/pip
mkdir -p /workspace/.cache/huggingface

# Variables para esta sesión
export TMPDIR=/workspace/tmp
export TEMP=/workspace/tmp
export TMP=/workspace/tmp
export PIP_CACHE_DIR=/workspace/.cache/pip
export HF_HOME=/workspace/.cache/huggingface
export TRANSFORMERS_CACHE=/workspace/.cache/huggingface
export HUGGINGFACE_HUB_CACHE=/workspace/.cache/huggingface
```

### Hacerlo persistente (.bashrc)

```bash
cat >> ~/.bashrc << 'EOF'

# FrameFactory / RunPod: evitar "No space left on device"
export TMPDIR=/workspace/tmp
export TEMP=/workspace/tmp
export TMP=/workspace/tmp
export PIP_CACHE_DIR=/workspace/.cache/pip
export HF_HOME=/workspace/.cache/huggingface
export TRANSFORMERS_CACHE=/workspace/.cache/huggingface
export HUGGINGFACE_HUB_CACHE=/workspace/.cache/huggingface
EOF
source ~/.bashrc
```

### ComfyUI y venvs en /workspace

- Clonar/instalar ComfyUI en `/workspace/ComfyUI`.
- Crear venv en `/workspace/venv` o `/workspace/comfy_venv` y usar ese `pip` (con las variables ya exportadas).
- Checkpoints y LoRAs en `/workspace/ComfyUI/models/checkpoints` y `.../models/loras`.

Después de esto, `pip install` y descargas de Hugging Face usan `/workspace` y no el overlay.

### RunPod: ComfyUI ya está pero falta venv o dependencias (ModuleNotFoundError: sqlalchemy)

Si ComfyUI está en `/workspace/ComfyUI` pero al hacer `python main.py` falla por módulos faltantes (ej. sqlalchemy), creá un venv en `/workspace` e instalá las dependencias ahí:

```bash
# Variables ya en .bashrc; si no, ejecutá antes los export de la sección A
export TMPDIR=/workspace/tmp
export PIP_CACHE_DIR=/workspace/.cache/pip

cd /workspace/ComfyUI
python3 -m venv /workspace/comfy_venv
source /workspace/comfy_venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
# Arrancar ComfyUI
python main.py --listen 0.0.0.0 --port 8188
```

Si `requirements.txt` no existe en ese ComfyUI (template viejo), instalá al menos:

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install sqlalchemy aiohttp aiofiles pillow numpy requests
```

Luego probá de nuevo `python main.py --listen 0.0.0.0 --port 8188`. Para no perder el proceso al cerrar la sesión: `screen -S comfy` y dentro de eso los comandos, o configurá el Start Command del Pod para que arranque ComfyUI al iniciar.

---

## B) Entrenar el LoRA (pasos exactos)

### Base: SD 1.5 (recomendado para arrancar YA)

- **Más rápido**: 512×512, menos VRAM, entrenamiento en ~1–2 h con 60–120 imágenes.
- **ComfyUI**: menos carga por imagen; 240 imágenes por video son viables en tiempo razonable.
- **SDXL** vale la pena si más adelante querés más detalle/calidad; requiere más VRAM y tiempo. Podés entrenar un segundo LoRA SDXL cuando el pipeline ya funcione.

### Dependencias (en /workspace)

```bash
cd /workspace
export TMPDIR=/workspace/tmp
export PIP_CACHE_DIR=/workspace/.cache/pip
export HF_HOME=/workspace/.cache/huggingface
export TRANSFORMERS_CACHE=/workspace/.cache/huggingface

# Clonar sd-scripts (kohya)
git clone https://github.com/kohya-ss/sd-scripts.git
cd sd-scripts

# Venv dedicado
python3 -m venv /workspace/venv_lora
source /workspace/venv_lora/bin/activate
pip install --upgrade pip
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
pip install -r requirements.txt
pip install accelerate transformers safetensors
```

(Si el Pod tiene otra versión de CUDA, ajustá `cu118` a `cu121` o la que corresponda.)

### Dataset: estructura y convención

```
/workspace/lora_stickman_dataset/
├── 10_stickmain_jm/          # 10 = número de repeticiones (opcional en kohya)
│   ├── 001_streaming_room_ansiedad_plano_medio.jpg
│   ├── 002_noche_monitor_plano_detalle.jpg
│   └── ...
├── 10_jm_cine_stick/         # estilo general (si entrenás estilo aparte)
│   └── ...
```

**Convención de nombres sugerida:**  
`NNN_lugar_emocion_plano.jpg` (ej. `042_calle_noche_tension_plano_general.jpg`).  
Los captions (ver abajo) son lo que más pesa; el nombre ayuda a ordenar y no equivocarte.

**Cantidad:** 60–120 imágenes mínimo. Mejor 80+ para protagonista + estilo.

### Captions (tags) recomendadas

Cada imagen debe tener un `.txt` o caption en el dataset (kohya usa un .txt por imagen con el mismo nombre, o CSV).

**Protagonista (trigger):** usar siempre el mismo token. Ejemplo:  
`stickmain_jm` → “el stickman protagonista (cabeza circular blanca, mismas proporciones, línea negra)”.

**Estilo (trigger):**  
`jm_cine_stick` → “2D plano, lineart limpio, cinematográfico, oscuro/tenso, sin 3D ni anime”.

**Ejemplo de caption por imagen:**

```
stickmain_jm, jm_cine_stick, streaming room, dark room, monitor glow, anxiety, sitting at desk, medium shot, tense atmosphere, simple background, no text
```

**Tags útiles por categoría:**

| Categoría   | Ejemplos |
|------------|----------|
| Lugar      | streaming room, dark room, bedroom, street at night, party, office, car interior, rooftop |
| Emoción    | anxiety, tension, focus, anger, sadness, relief, determination, fear |
| Plano/cámara | medium shot, close-up, wide shot, from above, from behind, POV desk, over shoulder |
| Escena     | monitor glow, neon lights, single light source, silhouette, night |

**Trigger words (NO NEGOCIABLES):**

- **Protagonista:** `stickmain_jm`
- **Estilo:** `jm_cine_stick`

En el prompt final siempre empezar con: `stickmain_jm, jm_cine_stick, ...`

### Comando de entrenamiento (sd-scripts)

Desde `/workspace/sd-scripts` con el venv activado:

```bash
accelerate launch --mixed_precision fp16 train_network.py \
  --pretrained_model_name_or_path=/workspace/ComfyUI/models/checkpoints/v1-5-pruned-emaonly.safetensors \
  --train_data_dir=/workspace/lora_stickman_dataset \
  --output_dir=/workspace/lora_output \
  --output_name=stickman_jm_cine \
  --network_module=networks.lora \
  --network_dim=32 \
  --network_alpha=16 \
  --resolution=512,512 \
  --train_batch_size=2 \
  --max_train_steps=1500 \
  --learning_rate=1e-4 \
  --optimizer_type=AdamW8bit \
  --save_every_n_epochs=1 \
  --caption_extension=txt
```

- **rank/alpha:** 32/16 es un buen inicio; si el estilo “no agarra”, subí a 64/32. Si sobreajusta (solo sale stickman y pierde escena), bajá a 24/12.
- **batch_size:** 2 con 512; si tenés 24 GB VRAM podés probar 4.
- **steps:** 1500 para ~60–80 imágenes; para 120 imágenes podés 2000–2500.
- **caption dropout:** en sd-scripts suele ser `--caption_dropout_rate=0.1` (opcional) para que no memorice el caption literal.

### Dónde queda el LoRA

- Salida típica: `/workspace/lora_output/stickman_jm_cine.safetensors`
- Copiarlo a ComfyUI:  
  `cp /workspace/lora_output/stickman_jm_cine.safetensors /workspace/ComfyUI/models/loras/`

---

## C) Parámetros iniciales y cómo iterar

| Problema              | Ajuste |
|-----------------------|--------|
| Estilo poco consistente | Subir `network_dim`/alpha (ej. 64/32), más steps, o más imágenes en dataset |
| Solo sale stickman, pierde escena | Bajar dim/alpha (24/12), menos steps, o más variedad en captions |
| Overfitting (ruido, artefactos) | Menos steps, más dropout, o más imágenes |
| “No agarra” el personaje | Más imágenes del protagonista, trigger siempre en caption y en prompt |

**Optimizer:** AdamW8bit va bien; si falla, probar `AdamW`.  
**LR:** 1e-4 es estándar; si inestable bajar a 5e-5.

---

## D) ComfyUI: dónde poner el LoRA y workflow batch

### Ubicación del LoRA

- Ruta: `ComfyUI/models/loras/`
- En RunPod: `/workspace/ComfyUI/models/loras/stickman_jm_cine.safetensors`

### Workflow base (una imagen por llamada)

Flujo: **Load Checkpoint** → **Load LoRA** → **CLIP positive** → **CLIP negative** → **EmptyLatentImage** → **KSampler** → **VAEDecode** → **SaveImage**.

- Checkpoint: SD 1.5 (ej. `v1-5-pruned-emaonly.safetensors`).
- LoRA: `stickman_jm_cine.safetensors`, strength 0.8–1.0.
- Resolución: **1280×720** (16:9). En SD 1.5 se suele usar 512 en entrenamiento; en inferencia podés 1280×720 o 768×432 (múltiplos de 8).
- SaveImage: prefix tipo `frame_` → salen `frame_00001.png`, etc. (el nombre secuencial lo puede poner quien llame a la API).

El workflow JSON listo para ComfyUI (con LoRA) está en **`workflows/comfyui_stickman_lora_720p.json`**. ComfyUI permite cargar ese JSON y probar; la API acepta el mismo grafo reemplazando el texto del CLIP y el seed.

### Generar N imágenes desde una lista de prompts

- ComfyUI no tiene un nodo “lista de prompts” estándar. La forma robusta es: **N llamadas a la API**, una por prompt (como hace ya FrameFactory).
- Cada llamada: mismo workflow, distinto `CLIPTextEncode` (positive) y opcionalmente seed.
- Salida: `0001.png`, `0002.png`, … en la carpeta que elijas (en FrameFactory es la carpeta del proyecto; en un script standalone podés escribir en `/workspace/batch_output/`).

En **`scripts/runpod_batch_comfyui.py`** tenés un script que lee un archivo con un prompt por línea y genera 0001.png, 0002.png… usando ese workflow con LoRA:

```bash
# Desde la raíz del repo (o con COMFYUI_URL en .env)
python scripts/runpod_batch_comfyui.py prompts.txt -o /workspace/batch_frames --no-verify-ssl
```

---

## E) Plantilla de prompts (positive y negative)

### Positive (template)

Variables: `{momento_de_historia}`, `{accion}`, `{emocion}`, `{plano_camara}`, `{lugar}`, `{personajes}`.

```
stickmain_jm, jm_cine_stick, {momento_de_historia}, {lugar}, {accion}, {emocion}, {plano_camara}, {personajes}, 2D flat style, clean lineart, cinematic lighting, no text on screen, no logos, simple stickman hands, 16:9, single light source
```

Ejemplo rellenado:

```
stickmain_jm, jm_cine_stick, climax of the story, streaming room, sitting at desk looking at monitor, anxiety, medium shot from front, one character, 2D flat style, clean lineart, cinematic lighting, no text on screen, no logos, simple stickman hands, 16:9, single light source
```

### Negative (fuerte)

```
3D, anime, realistic, photograph, detailed anatomy, shaded, volume, texture, person in suit, childish, cute, colorful cartoon, text, watermark, logo, signature, extra limbs, fused fingers, deformed, blurry, low quality, messy lines, crowded, multiple overlapping figures, dense pattern, maze, architecture, cityscape, out of frame
```

Podés usar esta plantilla y negative en:
- **FrameFactory:** en `config/` (prompt_maestro o instrucciones_imagenes) y en el generador de imágenes para ComfyUI.
- **Script batch:** leyendo una lista de prompts ya rellenados o generando cada línea con la plantilla.

---

## Resumen rápido (48–72 h)

1. **Pod:** Ejecutar A (exports + .bashrc), instalar ComfyUI y todo en `/workspace`.
2. **Dataset:** 60–120 imágenes + captions con `stickmain_jm`, `jm_cine_stick` y tags de lugar/emoción/plano.
3. **Entrenar:** sd-scripts en `/workspace`, comando de la sección B; copiar `.safetensors` a `ComfyUI/models/loras/`.
4. **ComfyUI:** Cargar workflow con LoRA, 1280×720; probar un prompt.
5. **Batch:** Usar script que lee N prompts y genera 0001.png… o integrar con FrameFactory (prompts desde guion + plantilla E).

Con esto tenés un pipeline real para producir imágenes stickman 2D consistentes para videos largos.

---

## Archivos creados en el repo

| Archivo | Uso |
|--------|-----|
| `docs/PIPELINE_STICKMAN_RUNPOD.md` | Esta guía (A–E) |
| `scripts/runpod_workspace_env.sh` | Source en el Pod para TMPDIR/cachés en /workspace |
| `scripts/runpod_batch_comfyui.py` | Batch: prompts.txt → 0001.png, 0002.png… vía ComfyUI + LoRA |
| `workflows/comfyui_stickman_lora_720p.json` | Workflow ComfyUI (Checkpoint + LoRA + 1280×720) |
| `config/prompt_stickman_lora.yaml` | Plantilla positive/negative con trigger words y variables |
