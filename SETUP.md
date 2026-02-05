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

### 4. **Configurar Generador de Imágenes**

Tienes 4 opciones (de más fácil a más avanzado):

**Opción A: Pollinations.ai (GRATIS, sin configuración) ⭐ RECOMENDADO PARA EMPEZAR**
- ✅ **100% gratis, sin token, sin instalación**
- ✅ Funciona automáticamente si no configuras nada más
- ⚠️ Límite: máximo 1024x1024 píxeles
- ⚠️ Puede ser más lento que otras opciones
- **No necesitas configurar nada en `.env`** - se usa automáticamente como fallback

**Opción B: Hugging Face Inference API (GRATIS con token)**
1. Crea una cuenta gratuita en: https://huggingface.co/
2. Ve a Settings → Access Tokens y crea un token
3. En `.env` agrega: `HUGGINGFACE_API_KEY=tu-token-aqui`
- ✅ Gratis con límites razonables
- ✅ Buena calidad
- ⚠️ Requiere token (gratis)

**Opción C: Automatic1111 (local)**
1. Instala Automatic1111: https://github.com/AUTOMATIC1111/stable-diffusion-webui
2. Inicia el servidor: `python webui.py --api`
3. En `.env` usa: `SD_API_URL=http://127.0.0.1:7860`
- ✅ Control total, sin límites
- ⚠️ Requiere GPU y instalación local

**Opción D: ComfyUI (local)**
1. Instala ComfyUI: https://github.com/comfyanonymous/ComfyUI
2. Inicia con API habilitada
3. En `.env` usa: `SD_API_URL=http://127.0.0.1:8188`
- ✅ Control total, sin límites
- ⚠️ Requiere GPU y instalación local

**Orden de prioridad automático:**
1. Si `SD_API_URL` está configurado → usa Stable Diffusion API
2. Si `HUGGINGFACE_API_KEY` está configurado → usa Hugging Face
3. Si nada está configurado → usa Pollinations.ai (gratis)

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
