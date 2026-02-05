"""FASE 6: Generación masiva de imágenes con Stable Diffusion (API local/cloud) o servicios gratuitos."""
import base64
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

from .config_loader import BASE, get_negative_prompt, get_instrucciones_imagenes
from .scene_splitter import Escena

load_dotenv(BASE / ".env")


def _generar_imagen_placeholder(prompt: str, width: int, height: int, escena_num: int) -> bytes:
    """
    Genera una imagen placeholder simple (imagen negra con texto) como último recurso.
    Usa PIL si está disponible, sino genera una imagen PNG básica.
    """
    try:
        # Intentar usar PIL (Pillow) si está disponible
        from PIL import Image, ImageDraw, ImageFont
        
        # Crear imagen negra
        img = Image.new("RGB", (width, height), color="black")
        draw = ImageDraw.Draw(img)
        
        # Intentar usar una fuente, sino usar default
        try:
            # Intentar fuente más grande
            font_size = min(width // 20, 48)
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            try:
                font = ImageFont.load_default()
            except:
                font = None
        
        # Texto a mostrar
        texto = f"Escena {escena_num}\n{prompt[:50]}..."
        
        # Calcular posición centrada
        if font:
            bbox = draw.textbbox((0, 0), texto, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        else:
            text_width = len(texto) * 10
            text_height = 40
        
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        
        # Dibujar texto blanco
        draw.text((x, y), texto, fill="white", font=font)
        
        # Convertir a bytes
        import io
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
        return img_bytes.getvalue()
        
    except ImportError:
        # Si PIL no está disponible, generar PNG básico (imagen negra simple)
        # PNG header + datos mínimos
        # Esto es un PNG válido de 1x1 pixel negro, escalado conceptualmente
        # En realidad, mejor generar una imagen negra más grande
        print(f"   ⚠️ PIL no disponible, generando placeholder básico...")
        
        # Generar un PNG simple: imagen negra de width x height
        # Usar una librería básica o crear PNG manualmente
        # Por ahora, vamos a usar una aproximación simple
        try:
            # Intentar con otra librería o método
            import struct
            
            # Crear un PNG básico (esto es complejo, mejor usar otra opción)
            # Por ahora, retornar None y dejar que el sistema maneje el fallback
            return None
        except:
            return None
    except Exception as e:
        print(f"   ⚠️ Error al generar placeholder: {e}")
        return None

OUTPUT_IMAGES = BASE / "output" / "imagenes"
MAX_REINTENTOS = 3  # Default, se carga dinámicamente
PAUSA_REINTENTO = 5  # Default, se carga dinámicamente


def _generar_imagen_pollinations(prompt: str, width: int, height: int) -> bytes | None:
    """
    Genera imagen usando Pollinations.ai (GRATIS, sin token).
    Prueba múltiples endpoints en caso de que uno falle.
    """
    # Limpiar prompt para URL (eliminar caracteres especiales)
    import urllib.parse
    prompt_encoded = urllib.parse.quote(prompt)
    
    # Intentar múltiples endpoints de Pollinations
    endpoints = [
        {
            "url": "https://image.pollinations.ai/prompt/",
            "method": "get",
            "params": {
                "prompt": prompt,
                "width": width,
                "height": height,
                "nologo": "true",
                "enhance": "true",
            }
        },
        {
            "url": f"https://pollinations.ai/prompt/{prompt_encoded}",
            "method": "get",
            "params": {
                "width": width,
                "height": height,
                "nologo": "true",
            }
        },
    ]
    
    for idx, endpoint in enumerate(endpoints):
        try:
            if endpoint["method"] == "get":
                r = requests.get(
                    endpoint["url"], 
                    params=endpoint.get("params", {}),
                    timeout=90, 
                    allow_redirects=True,
                    headers={"User-Agent": "Mozilla/5.0"}
                )
            else:
                continue
                
            r.raise_for_status()
            
            # Verificar que la respuesta sea una imagen válida
            content_type = r.headers.get("content-type", "").lower()
            
            # Algunos servidores devuelven "text/html" pero la imagen está en el body
            # Verificar por el contenido, no solo por content-type
            if r.content.startswith(b"<!DOCTYPE") or r.content.startswith(b"<html") or r.content.startswith(b"<?xml"):
                if idx < len(endpoints) - 1:
                    print(f"⚠️ Endpoint {idx+1} devolvió HTML, probando siguiente...")
                    continue
                print(f"⚠️ Pollinations devolvió HTML en lugar de imagen")
                return None
            
            # Verificar tamaño mínimo (imágenes válidas suelen ser > 1KB)
            if len(r.content) < 1000:
                if idx < len(endpoints) - 1:
                    print(f"⚠️ Endpoint {idx+1} devolvió respuesta muy pequeña, probando siguiente...")
                    continue
                print(f"⚠️ Pollinations devolvió respuesta muy pequeña ({len(r.content)} bytes)")
                return None
            
            # Verificar que empiece con magic bytes de imagen (PNG, JPEG, etc.)
            if not (r.content.startswith(b"\x89PNG") or r.content.startswith(b"\xff\xd8") or r.content.startswith(b"GIF")):
                if idx < len(endpoints) - 1:
                    print(f"⚠️ Endpoint {idx+1} no devolvió imagen válida, probando siguiente...")
                    continue
                print(f"⚠️ Pollinations no devolvió formato de imagen válido")
                return None
            
            print(f"✅ Pollinations funcionó con endpoint {idx+1}")
            return r.content
            
        except requests.exceptions.Timeout:
            if idx < len(endpoints) - 1:
                print(f"⚠️ Endpoint {idx+1} timeout, probando siguiente...")
                continue
            print(f"⚠️ Pollinations: Timeout (el servicio puede estar lento)")
            return None
        except requests.exceptions.RequestException as e:
            if idx < len(endpoints) - 1:
                print(f"⚠️ Endpoint {idx+1} falló: {e}, probando siguiente...")
                continue
            print(f"⚠️ Error con Pollinations: {e}")
            return None
        except Exception as e:
            if idx < len(endpoints) - 1:
                print(f"⚠️ Endpoint {idx+1} error inesperado: {e}, probando siguiente...")
                continue
            print(f"⚠️ Error inesperado con Pollinations: {e}")
            return None
    
    return None


def _generar_imagen_huggingface(prompt: str, width: int, height: int, negative_prompt: str = "") -> bytes | None:
    """
    Genera imagen usando Hugging Face Inference API (GRATIS con token).
    Requiere HUGGINGFACE_API_KEY en .env
    """
    api_key = os.getenv("HUGGINGFACE_API_KEY")
    if not api_key:
        return None
    
    try:
        # Modelo Stable Diffusion XL en Hugging Face
        model = "stabilityai/stable-diffusion-xl-base-1.0"
        url = f"https://api-inference.huggingface.co/models/{model}"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "negative_prompt": negative_prompt,
                "width": width,
                "height": height,
            }
        }
        
        r = requests.post(url, headers=headers, json=payload, timeout=120)
        r.raise_for_status()
        return r.content
    except Exception as e:
        print(f"⚠️ Error con Hugging Face: {e}")
        return None


def _generar_imagen_stable_diffusion_api(prompt: str, width: int, height: int, negative_prompt: str, params: dict) -> bytes | None:
    """
    Genera imagen usando Stable Diffusion API (Automatic1111/ComfyUI).
    """
    url = os.getenv("SD_API_URL", "http://127.0.0.1:7860").rstrip("/")
    endpoint = f"{url}/sdapi/v1/txt2img"
    
    payload = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "steps": params.get("steps", 25),
        "width": width,
        "height": height,
        "cfg_scale": params.get("cfg_scale", 7),
    }
    
    try:
        r = requests.post(endpoint, json=payload, timeout=120)
        
        # Mostrar más detalles del error
        if r.status_code != 200:
            print(f"   ⚠️ Stable Diffusion API respondió con código {r.status_code}")
            try:
                error_data = r.json()
                print(f"   ⚠️ Error: {error_data}")
            except:
                print(f"   ⚠️ Respuesta: {r.text[:200]}")
        
        r.raise_for_status()
        data = r.json()
        img_b64 = data.get("images", [None])[0]
        if not img_b64:
            print(f"   ⚠️ Stable Diffusion API no devolvió imagen en la respuesta")
            return None
        return base64.b64decode(img_b64)
    except requests.exceptions.ConnectionError as e:
        print(f"   ⚠️ Error de conexión con Stable Diffusion API: {e}")
        return None
    except requests.exceptions.Timeout as e:
        print(f"   ⚠️ Timeout con Stable Diffusion API: {e}")
        return None
    except Exception as e:
        print(f"   ⚠️ Error con Stable Diffusion API: {type(e).__name__}: {e}")
        return None


def generar_imagen(prompt: str, escena_num: int, carpeta: Path, width: int | None = None, height: int | None = None) -> Path | None:
    """
    Genera una imagen usando el servicio configurado.
    Orden de prioridad:
    1. Stable Diffusion API (SD_API_URL) si está configurado
    2. Hugging Face (HUGGINGFACE_API_KEY) si está configurado
    3. Pollinations.ai (gratis, sin token) como fallback
    
    Reintentos automáticos si falla.
    width/height: Si se proporcionan, sobrescriben la configuración.
    """
    # Cargar parámetros desde configuración
    instrucciones = get_instrucciones_imagenes()
    params = instrucciones.get("parametros_sd", {})
    reintentos_config = instrucciones.get("reintentos", {})
    max_reintentos = reintentos_config.get("max_reintentos", MAX_REINTENTOS)
    pausa_reintento = reintentos_config.get("pausa_segundos", PAUSA_REINTENTO)
    
    # Usar width/height proporcionados o los de la configuración
    img_width = width if width is not None else params.get("width", 1024)
    img_height = height if height is not None else params.get("height", 576)
    
    # Limitar dimensiones para servicios gratuitos (algunos tienen límites)
    img_width = min(img_width, 1024)
    img_height = min(img_height, 1024)
    
    negative_prompt = get_negative_prompt()
    carpeta.mkdir(parents=True, exist_ok=True)
    nombre = f"escena_{escena_num:04d}.png"
    path = carpeta / nombre

    # Determinar qué servicio usar
    sd_api_url = os.getenv("SD_API_URL", "").strip()
    hf_api_key = os.getenv("HUGGINGFACE_API_KEY", "").strip()
    
    print(f"\n🎨 Generando imagen para escena {escena_num}...")
    print(f"   Dimensiones: {img_width}x{img_height}")
    print(f"   Prompt: {prompt[:80]}...")
    
    for intento in range(max_reintentos):
        try:
            img_bytes = None
            servicio_usado = None
            
            # Prioridad 1: Stable Diffusion API (local o remota)
            if sd_api_url:
                print(f"   🔄 Intento {intento + 1}: Probando Stable Diffusion API...")
                # Si es local, verificar que esté disponible
                if sd_api_url.startswith("http://127.0.0.1") or sd_api_url.startswith("http://localhost"):
                    if _verificar_sd_local():
                        img_bytes = _generar_imagen_stable_diffusion_api(prompt, img_width, img_height, negative_prompt, params)
                        if img_bytes:
                            servicio_usado = "Stable Diffusion API (local)"
                    else:
                        print(f"   ⚠️ Stable Diffusion local no disponible")
                else:
                    # API remota, intentar directamente
                    img_bytes = _generar_imagen_stable_diffusion_api(prompt, img_width, img_height, negative_prompt, params)
                    if img_bytes:
                        servicio_usado = "Stable Diffusion API (remota)"
            
            # Prioridad 2: Hugging Face (si no funcionó SD o no está configurado)
            if not img_bytes and hf_api_key:
                print(f"   🔄 Intento {intento + 1}: Probando Hugging Face...")
                img_bytes = _generar_imagen_huggingface(prompt, img_width, img_height, negative_prompt)
                if img_bytes:
                    servicio_usado = "Hugging Face"
            
            # Prioridad 3: Pollinations.ai (gratis, sin token)
            if not img_bytes:
                print(f"   🔄 Intento {intento + 1}: Probando Pollinations.ai (gratis)...")
                img_bytes = _generar_imagen_pollinations(prompt, img_width, img_height)
                if img_bytes:
                    servicio_usado = "Pollinations.ai"
            
            if img_bytes:
                # Verificar que sea una imagen válida antes de guardar
                if len(img_bytes) < 1000:
                    print(f"   ⚠️ Imagen muy pequeña ({len(img_bytes)} bytes), puede ser inválida")
                    if intento < max_reintentos - 1:
                        continue
                    raise ValueError(f"Imagen inválida: solo {len(img_bytes)} bytes")
                
                path.write_bytes(img_bytes)
                print(f"   ✅ Imagen generada con {servicio_usado}: {nombre} ({len(img_bytes)} bytes)")
                return path
            else:
                # Mostrar qué servicios se intentaron
                servicios_intentados = []
                if sd_api_url:
                    servicios_intentados.append("Stable Diffusion API")
                if hf_api_key:
                    servicios_intentados.append("Hugging Face")
                servicios_intentados.append("Pollinations.ai")
                
                if intento < max_reintentos - 1:
                    print(f"   ⚠️ Ningún servicio funcionó en este intento. Reintentando...")
                else:
                    # Último recurso: generar placeholder
                    print(f"   ⚠️ Todos los servicios fallaron. Generando imagen placeholder...")
                    img_bytes = _generar_imagen_placeholder(prompt, img_width, img_height, escena_num)
                    if img_bytes:
                        servicio_usado = "Placeholder (fallback)"
                        path.write_bytes(img_bytes)
                        print(f"   ⚠️ Imagen placeholder generada: {nombre} (todos los servicios fallaron)")
                        return path
                    else:
                        raise ValueError(f"No se pudo generar imagen con ningún servicio después de {max_reintentos} intentos. Servicios intentados: {', '.join(servicios_intentados)}")
                
        except Exception as e:
            if intento < max_reintentos - 1:
                print(f"⚠️ Intento {intento + 1}/{max_reintentos} falló: {e}, reintentando en {pausa_reintento}s...")
                time.sleep(pausa_reintento)
            else:
                # Último intento: generar placeholder
                print(f"   ⚠️ Todos los intentos fallaron. Generando imagen placeholder como último recurso...")
                try:
                    img_bytes = _generar_imagen_placeholder(prompt, img_width, img_height, escena_num)
                    if img_bytes:
                        path.write_bytes(img_bytes)
                        print(f"   ⚠️ Imagen placeholder generada: {nombre}")
                        return path
                except Exception as placeholder_error:
                    print(f"   ❌ Error al generar placeholder: {placeholder_error}")
                
                raise RuntimeError(f"Falló generación escena {escena_num}: {e}") from e
    return None


def _verificar_sd_local() -> bool:
    """Verifica si Stable Diffusion local está disponible."""
    try:
        url = os.getenv("SD_API_URL", "http://127.0.0.1:7860").rstrip("/")
        r = requests.get(f"{url}/sdapi/v1/options", timeout=5)
        return r.status_code == 200
    except:
        return False


def generar_lote(
    escenas_con_prompts: list[tuple[Escena, str]],
    subcarpeta: str = "default",
    width: int | None = None,
    height: int | None = None,
) -> list[Path]:
    """Genera todas las imágenes y las guarda con nombre de escena."""
    carpeta = OUTPUT_IMAGES / subcarpeta
    rutas = []
    for escena, prompt in escenas_con_prompts:
        path = generar_imagen(prompt, escena.numero, carpeta, width=width, height=height)
        if path:
            rutas.append(path)
    return rutas
