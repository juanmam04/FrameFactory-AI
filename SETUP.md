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

1. Instalá ComfyUI y arrancalo (por defecto escucha en el puerto 8188).
2. En `.env`: `COMFYUI_URL=http://127.0.0.1:8188`.

#### Opción B2: ComfyUI en RunPod (GPU en la nube)

1. Creá un Pod en [RunPod](https://runpod.io) con GPU (ej. con template que incluya ComfyUI o instalalo por SSH).
2. En el Pod, arrancá ComfyUI y dejalo escuchando en el puerto **8188**.
3. En el dashboard de RunPod, **exponé el puerto 8188** (TCP): te darán una URL tipo `https://TU_POD_ID-8188.proxy.runpod.net` o una IP:puerto.
4. En tu `.env` (en tu Mac, donde corre FrameFactory):
   ```env
   COMFYUI_URL=https://TU_POD_ID-8188.proxy.runpod.net
   ```
   o bien `COMFYUI_URL=http://IP:8188` si usás conexión directa.
5. Si el proxy usa HTTPS y da error de certificado: `COMFYUI_VERIFY_SSL=false` en `.env`.

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
- [ ] Archivo `.env` con `SD_API_URL` configurado
- [ ] Stable Diffusion corriendo (si es local)
- [ ] Probar: `streamlit run app.py`

## ⚠️ Notas importantes

1. **OPENAI_API_KEY** es obligatoria para generar guiones
2. **SD_API_URL** es obligatoria para generar imágenes
3. Para voz puedes usar **OPENAI_API_KEY** (TTS) o **ELEVENLABS_API_KEY**
4. Si no tienes Stable Diffusion local, necesitas una API en la nube
