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

# Stable Diffusion API URL
# Si usas Automatic1111 local: http://127.0.0.1:7860
# Si usas ComfyUI: http://127.0.0.1:8188
# Si usas API en la nube: https://tu-api-sd.com
SD_API_URL=http://127.0.0.1:7860

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

### 4. **Configurar Stable Diffusion**

Tienes 3 opciones:

**Opción A: Automatic1111 (local)**
1. Instala Automatic1111: https://github.com/AUTOMATIC1111/stable-diffusion-webui
2. Inicia el servidor: `python webui.py --api`
3. En `.env` usa: `SD_API_URL=http://127.0.0.1:7860`

**Opción B: ComfyUI (local)**
1. Instala ComfyUI: https://github.com/comfyanonymous/ComfyUI
2. Inicia con API habilitada
3. En `.env` usa: `SD_API_URL=http://127.0.0.1:8188`

**Opción C: API en la nube**
- Usa un servicio como Replicate, Stability AI, etc.
- En `.env` pon la URL de la API

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
