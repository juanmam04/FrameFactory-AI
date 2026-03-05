# 🚀 Configuración para crear tu primer video

## ✅ Lo que ya tienes
- ✅ Python 3.11.3 instalado
- ✅ Código del proyecto completo

## ❌ Lo que FALTA configurar

### 1. **Instalar dependencias de Python**
```bash
pip install -r requirements.txt
```

### 2. **Instalar FFmpeg** (OBLIGATORIO)
FFmpeg es necesario para montar los videos.

**Windows:**
- Descarga desde: https://ffmpeg.org/download.html
- O usa chocolatey: `choco install ffmpeg`
- O usa winget: `winget install ffmpeg`
- **IMPORTANTE:** Agrega FFmpeg al PATH del sistema

**Verificar instalación:**
```bash
ffmpeg -version
```

### 3. **Crear archivo `.env` con tus credenciales**

Crea un archivo `.env` en la raíz del proyecto con este contenido:

```env
# ============================================
# OBLIGATORIAS
# ============================================

# OpenAI API Key (para generar guiones y opcionalmente voz)
# Obtén tu key en: https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-tu-api-key-aqui

# ============================================
# OPCIONALES - Generación de Imágenes
# ============================================

# Opción 1: Stable Diffusion API (local o remota)
# Si usas Automatic1111 local: http://127.0.0.1:7860
# Si usas ComfyUI: http://127.0.0.1:8188
# Si usas API en la nube: https://tu-api-sd.com
# SD_API_URL=http://127.0.0.1:7860

# Opción 2: Hugging Face Inference API (GRATIS con token)
# Obtén tu token en: https://huggingface.co/settings/tokens
# HUGGINGFACE_API_KEY=tu-token-huggingface

# Opción 3: Pollinations.ai (GRATIS, sin token)
# No necesitas configurar nada - se usa automáticamente si no hay otras opciones

# ============================================
# OPCIONALES - Voz
# ============================================

# ElevenLabs API Key (alternativa a OpenAI TTS para voz)
# ELEVENLABS_API_KEY=tu-elevenlabs-key
# ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM

# OpenAI TTS (si no usas ElevenLabs)
OPENAI_TTS_MODEL=tts-1-hd
OPENAI_TTS_VOICE=alloy

# ============================================
# OPCIONALES - Modelo de lenguaje
# ============================================

# Modelo de OpenAI para generar guiones
OPENAI_MODEL=gpt-4o-mini

# ============================================
# OPCIONALES - Música de fondo
# ============================================

# BACKGROUND_MUSIC_PATH=path/to/musica.mp3
```

### 4. **Configurar generación de imágenes (ComfyUI)**

La app usa **ComfyUI** para generar las imágenes. Tenés que tener ComfyUI corriendo **antes** de generar el video.

#### Opción A: Automatic1111 en Mac (alternativa)

1. **Requisitos:** Python 3.10+, Xcode Command Line Tools (`xcode-select --install`), y bastante espacio (modelos ~4–7 GB).
2. Cloná e instalá Automatic1111, arrancalo con `./webui.sh --api`.
3. En `.env`: `SD_API_URL=http://127.0.0.1:7860` (la app prioriza ComfyUI si está `COMFYUI_URL`).

#### Opción B: ComfyUI (local)

1. Instalá ComfyUI y arrancalo en el puerto **8188** (por defecto ComfyUI usa ese puerto).
   - Desde la carpeta de ComfyUI: `python main.py --port 8188`
   - O desde este proyecto (Windows): `.\scripts\start_comfyui.ps1` (opcionalmente pasá la ruta a ComfyUI, o definí `COMFYUI_PATH` en `.env`).
2. En `.env`: `COMFYUI_URL=http://127.0.0.1:8188`.

#### Opción B2: ComfyUI en RunPod (GPU en la nube)

**Para que el RunPod no sea al pedo:** usá **SDXL** (no SD 1.5). El programa prioriza SDXL solo si está en el Pod; ver pasos más abajo.

**Si ya tenés un Pod en RunPod**, seguí estos pasos:

1. **En el RunPod (SSH o la consola web):** si el template no trae ComfyUI, instalalo y arrancalo:
   ```bash
   cd /workspace || cd ~
   git clone https://github.com/comfyanonymous/ComfyUI
   cd ComfyUI
   pip install -r requirements.txt
   # Un modelo mínimo (SD 1.5); si ya tenés otro en models/checkpoints/, saltá esto:
   mkdir -p models/checkpoints && cd models/checkpoints
   wget -q https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors
   cd ../..
   python main.py --listen 0.0.0.0 --port 8188
   ```
   (Si solo tenés `python3`, usá `python3 main.py ...`). Dejalo corriendo; el `--listen 0.0.0.0` hace que escuche desde fuera del Pod. Para no perderlo al cerrar la sesión: `screen -S comfy` y después los comandos, o `tmux`.

2. **En el dashboard de RunPod (runpod.io):**
   - Entrá a tu Pod → pestaña **Connect** o **Expose**.
   - **Exponé el puerto TCP 8188**. RunPod te muestra una URL tipo:
     - `https://abc123xyz-8188.proxy.runpod.net` (proxy HTTPS), o
     - La IP del Pod + puerto, ej. `123.45.67.89:8188` (conexión directa).

3. **En tu Mac (donde corre FrameFactory), editá el `.env`:**
   ```env
   # ComfyUI en RunPod (reemplazá por TU URL real)
   COMFYUI_URL=https://TU_POD_ID-8188.proxy.runpod.net
   ```
   Si usás la IP directa: `COMFYUI_URL=http://123.45.67.89:8188` (reemplazá por la IP de tu Pod).

4. **Si al generar te sale error de certificado SSL**, agregá en `.env`:
   ```env
   COMFYUI_VERIFY_SSL=false
   ```

5. **Opcional (RunPod suele ser más lento en respuesta):** los timeouts ya están altos por defecto; si igual falla por tiempo, podés subirlos:
   ```env
   COMFYUI_TIMEOUT_CONNECT=30
   COMFYUI_TIMEOUT_POST=120
   COMFYUI_TIMEOUT_POLL=400
   ```

Listo: en la app, **no** marques «Saltar generación de imágenes» y las imágenes se generarán en la GPU del RunPod (mucho más rápido que en una Mac).

**Stickman / cartoon:** El que no entiende bien stickman es el **modelo SD 1.5**, no ComfyUI. ComfyUI solo ejecuta el modelo que le pongas. Para que ComfyUI genere las imágenes que querés (stickman + contexto de escena), usá **SDXL** en RunPod:

1. En el Pod, en `ComfyUI/models/checkpoints/`, descargá un checkpoint SDXL, por ejemplo:
   ```bash
   wget https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors -O sdXL_v10.safetensors
   ```
2. En tu `.env` (en la Mac):
   ```env
   IMAGE_BACKEND=comfyui
   COMFYUI_URL=https://TU_POD_ID-8188.proxy.runpod.net
   COMFYUI_CHECKPOINT=sdXL_v10.safetensors
   COMFYUI_SDXL=true
   COMFYUI_PARALLEL=3
   COMFYUI_VERIFY_SSL=false
   ```
   `COMFYUI_PARALLEL=3` hace que se generen **varias imágenes a la vez** (masivo y más rápido).

3. El estilo (stickman, etc.) se controla en `config/visual_bible.yaml` y `config/instrucciones_imagenes.yaml`.

**Resumen:** ComfyUI puede crear las imágenes que necesitás y en masa; el truco es usar **SDXL** (no SD 1.5) y **COMFYUI_PARALLEL** para generar muchas a la vez.

#### Opción C: API en la nube

- Replicate, Stability AI, etc. Poné en `.env` la URL que te den (la app usa ComfyUI si `COMFYUI_URL` está definido).

## 🎬 Crear tu primer video

### Opción 1: Interfaz web (recomendado)
```bash
streamlit run app.py
```
Luego abre tu navegador en la URL que aparece.

### Opción 2: Línea de comandos
```bash
python -m src.pipeline --tema "Historia de la inteligencia artificial"
```

## 📋 Checklist rápido

- [ ] `pip install -r requirements.txt`
- [ ] FFmpeg instalado y en PATH
- [ ] Archivo `.env` creado con `OPENAI_API_KEY`
- [ ] En `.env`: `COMFYUI_URL=http://127.0.0.1:8188` (o URL de RunPod si usás nube)
- [ ] **ComfyUI prendido** en otra terminal: `cd ComfyUI && python main.py --port 8188` (si querés imágenes; si no, marcá «Saltar generación de imágenes»)
- [ ] Probar: `streamlit run app.py`

## ⚠️ Notas importantes

1. **OPENAI_API_KEY** es obligatoria para generar guiones
2. **SD_API_URL** es obligatoria para generar imágenes
3. Para voz puedes usar **OPENAI_API_KEY** (TTS) o **ELEVENLABS_API_KEY**
4. Si no tienes Stable Diffusion local, necesitas una API en la nube
