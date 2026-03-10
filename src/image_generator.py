"""FASE 6: Generación de imágenes con ComfyUI (local o RunPod)."""
import os
import shutil
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable

import requests
from dotenv import load_dotenv

from .config_loader import BASE, get_negative_prompt, get_instrucciones_imagenes, get_estilo_base, get_character_references, get_visual_references
from .scene_splitter import Escena

# Mapeo outfit_key (outfit_library) -> nombre de archivo en references/outfits/
OUTFIT_REF_FILENAMES: dict[str, str] = {
    "casual_outfit": "outfit_casual.png",
    "kid_outfit": "outfit_kid.png",
    "gamer_outfit": "outfit_gamer.png",
    "athlete_outfit": "outfit_athlete.png",
    "business_outfit": "outfit_business.png",
    "criminal_outfit": "outfit_criminal.png",
    "war_outfit": "outfit_war.png",
}
OUTFIT_REF_DIR = BASE / "references" / "outfits"

load_dotenv(BASE / ".env")

OUTPUT_IMAGES = BASE / "output" / "imagenes"
COMFY_URL = (os.getenv("COMFYUI_URL") or "http://127.0.0.1:8188").strip().rstrip("/")
COMFY_CHECKPOINT_DEFAULT = "v1-5-pruned-emaonly.safetensors"
_resolved_checkpoint: str | None = None

# DALL-E deshabilitado: solo ComfyUI o Replicate (FLUX).
def _usar_openai_imagenes() -> bool:
    return False

# Replicate: permitimos elegir modelo de texto→imagen por .env.
# REPLICATE_IMAGE_MODEL (nuevo) tiene prioridad; si no está, usamos REPLICATE_FLUX_MODEL (legacy) y,
# en última instancia, flux-schnell (muy barato pero peor calidad de anatomía).
REPLICATE_MODEL_TEXT = (
    os.getenv("REPLICATE_IMAGE_MODEL")
    or os.getenv("REPLICATE_FLUX_MODEL")
    or "black-forest-labs/flux-schnell"
).strip()
# Para flujos con imagen de referencia (Kontext) mantenemos por defecto FLUX Kontext, también configurable.
REPLICATE_MODEL_KONTEXT = os.getenv(
    "REPLICATE_IMAGE_MODEL_WITH_REF", "black-forest-labs/flux-kontext-dev"
).strip()

def _usar_replicate() -> bool:
    """Usar SIEMPRE Replicate (FLUX) cuando haya token; ComfyUI queda como opción legacy."""
    return bool(os.getenv("REPLICATE_API_TOKEN", "").strip())

def _replicate_disponible() -> bool:
    return bool(os.getenv("REPLICATE_API_TOKEN", "").strip())

# Timeouts: más largos cuando ComfyUI está en la nube (RunPod, etc.)
def _is_remote_comfy() -> bool:
    u = COMFY_URL.lower()
    if not u:
        return False
    return "127.0.0.1" not in u and "localhost" not in u

def _comfy_timeout_connect() -> int:
    return int(os.getenv("COMFYUI_TIMEOUT_CONNECT", "15" if _is_remote_comfy() else "5"))

def _comfy_timeout_post() -> int:
    return int(os.getenv("COMFYUI_TIMEOUT_POST", "90" if _is_remote_comfy() else "30"))

def _comfy_timeout_poll() -> int:
    return int(os.getenv("COMFYUI_TIMEOUT_POLL", "300" if _is_remote_comfy() else "120"))

def _comfy_timeout_view() -> int:
    return int(os.getenv("COMFYUI_TIMEOUT_VIEW", "60" if _is_remote_comfy() else "30"))

# Verificación SSL (para proxies RunPod con HTTPS; poner COMFYUI_VERIFY_SSL=false solo si hay problemas de cert)
COMFY_VERIFY_SSL = os.getenv("COMFYUI_VERIFY_SSL", "true").strip().lower() not in ("0", "false", "no")

MAX_REINTENTOS = 3
PAUSA_REINTENTO = 5

def _comfyui_error_msg() -> str:
    return (
        f"ComfyUI no está corriendo en {COMFY_URL}. "
        "Inicialo en otra terminal (ej. python main.py) o revisá COMFYUI_URL en .env si usás RunPod/nube."
    )


def _lista_checkpoints_comfyui() -> list[str]:
    """Obtiene la lista de nombres de checkpoints desde ComfyUI /object_info."""
    r = requests.get(f"{COMFY_URL}/object_info", timeout=_comfy_timeout_connect(), verify=COMFY_VERIFY_SSL)
    if r.status_code != 200:
        return []
    data = r.json()
    loader = (data or {}).get("CheckpointLoaderSimple") or {}
    required = (loader.get("input") or {}).get("required") or {}
    ckpt_name = required.get("ckpt_name")
    if not isinstance(ckpt_name, list) or len(ckpt_name) == 0:
        return []
    names: list[str] = []
    for item in ckpt_name:
        if isinstance(item, str) and item.strip():
            names.append(item.strip())
        elif isinstance(item, list) and len(item) > 0:
            n = item[0] if isinstance(item[0], str) else (item[0][0] if isinstance(item[0], list) and item[0] else None)
            if n and isinstance(n, str):
                names.append(n)
    return names


def _get_checkpoint() -> str:
    """Usa COMFYUI_CHECKPOINT si está definido. Si no, prefiere SDXL en RunPod para imágenes bien hechas."""
    global _resolved_checkpoint
    env_ckpt = (os.getenv("COMFYUI_CHECKPOINT") or "").strip()
    if env_ckpt:
        _resolved_checkpoint = env_ckpt
        return env_ckpt
    if _resolved_checkpoint is not None:
        return _resolved_checkpoint
    try:
        names = _lista_checkpoints_comfyui()
        if not names:
            raise RuntimeError(
                "ComfyUI no tiene ningún checkpoint en models/checkpoints. "
                "Añadí SDXL (ej. sdXL_v10.safetensors) o configurá COMFYUI_CHECKPOINT en .env."
            )
        # Preferir SDXL para calidad (stickman, escenas); si no hay, el primero
        lower = [n.lower() for n in names]
        for i, n in enumerate(lower):
            if "sdxl" in n or "sd_xl" in n or "_xl_" in n or n.endswith("xl.safetensors"):
                _resolved_checkpoint = names[i]
                return _resolved_checkpoint
        _resolved_checkpoint = names[0]
        return _resolved_checkpoint
    except RuntimeError:
        raise
    except Exception:
        pass
    _resolved_checkpoint = COMFY_CHECKPOINT_DEFAULT
    return _resolved_checkpoint


def _comfyui_es_sdxl() -> bool:
    """True si hay que usar resolución SDXL (1024)."""
    if os.getenv("COMFYUI_SDXL", "").strip().lower() in ("1", "true", "yes"):
        return True
    ckpt = (_get_checkpoint() or "").lower()
    return "sdxl" in ckpt or "sd_xl" in ckpt or "_xl_" in ckpt


def _workflow_comfyui(prompt_text: str, negative: str, width: int, height: int, seed: int | None = None):
    """Workflow ComfyUI. SDXL usa 1024x1024 y prompts reforzados para calidad."""
    import random
    seed = seed if seed is not None else random.randint(0, 999999)
    if _comfyui_es_sdxl():
        prompt_text = "high quality, clear composition, " + (prompt_text[:3800] if len(prompt_text) > 3800 else prompt_text)
        w, h = 1024, 1024
    else:
        w, h = (width // 8) * 8, (height // 8) * 8
    if w < 64:
        w = 64
    if h < 64:
        h = 64
    steps_env = os.getenv("COMFYUI_STEPS", "").strip()
    steps = int(steps_env) if steps_env.isdigit() else (28 if _comfyui_es_sdxl() else 25)
    steps = max(15, min(50, steps))
    return {
        "3": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": _get_checkpoint()},
        },
        "4": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt_text, "clip": ["3", 1]},
        },
        "5": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": negative or "blurry, low quality, bad anatomy", "clip": ["3", 1]},
        },
        "6": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": w, "height": h, "batch_size": 1},
        },
        "7": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["3", 0],
                "positive": ["4", 0],
                "negative": ["5", 0],
                "latent_image": ["6", 0],
                "seed": seed,
                "steps": steps,
                "cfg": 7.5 if _comfyui_es_sdxl() else 8,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
            },
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["7", 0], "vae": ["3", 2]},
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "api_gen", "images": ["8", 0]},
        },
    }


def _comfyui_disponible() -> bool:
    """Comprueba si ComfyUI responde (endpoint /queue)."""
    try:
        r = requests.get(f"{COMFY_URL}/queue", timeout=_comfy_timeout_connect(), verify=COMFY_VERIFY_SSL)
        return r.status_code == 200
    except requests.RequestException:
        return False


def comfyui_es_remoto() -> bool:
    """True si COMFYUI_URL apunta a un host remoto (ej. RunPod), no localhost."""
    return _is_remote_comfy()


def _generar_imagen_comfyui(
    prompt_text: str,
    negative: str,
    carpeta: Path,
    escena_num: int,
    width: int,
    height: int,
    timeout_post: int | None = None,
    timeout_poll: int | None = None,
) -> Path | None:
    """Envía prompt a ComfyUI, espera resultado y guarda la imagen en carpeta/escena_XXXX.png."""
    timeout_post = timeout_post if timeout_post is not None else _comfy_timeout_post()
    timeout_poll = timeout_poll if timeout_poll is not None else _comfy_timeout_poll()
    workflow = _workflow_comfyui(prompt_text, negative, width, height)
    try:
        r = requests.post(
            f"{COMFY_URL}/prompt",
            json={"prompt": workflow},
            timeout=timeout_post,
            verify=COMFY_VERIFY_SSL,
        )
        if r.status_code == 400:
            try:
                body = r.json()
                err = body.get("error") or {}
                msg = err.get("message", "Prompt outputs failed validation") if isinstance(err, dict) else str(err)
                extra = (err.get("extra_info") or {}) if isinstance(err, dict) else {}
                node_errors = extra.get("node_errors") or body.get("node_errors") or {}
                if node_errors:
                    parts = [f"{n}: {'; '.join(msgs)}" for n, msgs in node_errors.items() if isinstance(msgs, list)]
                    if parts:
                        msg = msg + ". Detalle: " + " | ".join(parts)
                details = (err.get("details") or "").strip() if isinstance(err, dict) else ""
                if details:
                    msg = msg + ". " + details[:400]
            except Exception:
                msg = (r.text or f"HTTP {r.status_code}")[:500]
            raise RuntimeError(
                f"ComfyUI rechazó el workflow (400). Revisá COMFYUI_CHECKPOINT en .env "
                f"(debe existir en ComfyUI/models/checkpoints). {msg}"
            )
        r.raise_for_status()
        data = r.json()
        prompt_id = data.get("prompt_id")
        if not prompt_id:
            return None
    except RuntimeError:
        raise
    except requests.RequestException as e:
        raise RuntimeError(_comfyui_error_msg() + f" Detalle: {e}") from e

    # Poll history until job is done. Usar /history/{prompt_id} para solo nuestro job (más rápido).
    deadline = time.time() + timeout_poll
    view_timeout = _comfy_timeout_view()
    save_node_id = "9"  # SaveImage en nuestro workflow
    history_url = f"{COMFY_URL}/history/{prompt_id}"
    while time.time() < deadline:
        try:
            hist = requests.get(history_url, timeout=_comfy_timeout_connect(), verify=COMFY_VERIFY_SSL)
            hist.raise_for_status()
            h = hist.json()
            if not h or prompt_id not in h:
                time.sleep(0.8)
                continue
            entry = h[prompt_id]
            # Si el job terminó con error, salir ya (evita polling infinito)
            status = entry.get("status") or {}
            if isinstance(status, dict) and status.get("status_str") == "error":
                msgs = status.get("messages") or []
                raise RuntimeError(
                    f"ComfyUI falló al generar la imagen. {msgs[:3] if msgs else status}"
                )
            outputs = entry.get("outputs", {})
            # Aceptar node "9" o 9 (por si el servidor devuelve claves int)
            node_out = outputs.get(save_node_id) or outputs.get(9, {})
            images = (node_out or {}).get("images", [])
            # Si no hay imágenes en "9", buscar en cualquier nodo (por compatibilidad)
            if not images and outputs:
                for _nid, node_data in outputs.items():
                    imgs = (node_data or {}).get("images", [])
                    if imgs:
                        images = imgs
                        break
            if images:
                info = images[0]
                filename = info.get("filename", "")
                subfolder = info.get("subfolder", "")
                type_out = info.get("type", "output")
                params = {"filename": filename, "subfolder": subfolder, "type": type_out}
                view = requests.get(f"{COMFY_URL}/view", params=params, timeout=view_timeout, verify=COMFY_VERIFY_SSL)
                view.raise_for_status()
                path = carpeta / f"escena_{escena_num:04d}.png"
                carpeta.mkdir(parents=True, exist_ok=True)
                path.write_bytes(view.content)
                return path
        except RuntimeError:
            raise
        except requests.RequestException:
            pass
        time.sleep(0.8)
    return None


def _sanitizar_prompt_para_dalle(prompt: str, escena_num: int) -> str:
    """
    Reescribe el prompt con GPT para que sea aceptado por DALL-E (sin violencia gráfica, etc.)
    manteniendo la escena, el estilo stickman 2D y la intención narrativa. Así evitamos rechazos.
    """
    prompt = (prompt or "").strip()[:3500]
    if not prompt:
        return _prompt_fallback_stickman(escena_num)
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return prompt
    estilo = get_estilo_base()
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        r = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Reescribes descripciones de imagen para DALL-E. Reglas: misma escena, composición y emoción. Estilo: " + estilo + ". "
                        "Suaviza solo lo que active filtros (violencia, sangre). No agregues lugares que no estén en el prompt. "
                        "IMPORTANTE: La imagen debe ser UN SOLO FOTOGRAMA de ilustración, solo el contenido de la escena. "
                        "NUNCA incluyas ni menciones: reproductor de video, barra de progreso, línea de tiempo, rejilla, interfaz de programa, controles, código de tiempo. Solo la escena dibujada. "
                        "Devuelve SOLO el prompt reescrito, sin explicaciones, en un solo párrafo."
                    ),
                },
                {"role": "user", "content": f"Reescribí este prompt para DALL-E:\n\n{prompt}"},
            ],
            max_tokens=500,
            temperature=0.3,
        )
        out = (r.choices[0].message.content or "").strip()
        if out:
            return out[:4000]
    except Exception as e:
        print(f"   ⚠️ Escena {escena_num}: no se pudo sanitizar prompt ({e}), se usa original.")
    return prompt


# PNG 1x1 gris mínimo (base64) para placeholder cuando falla hasta el fallback
_PLACEHOLDER_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def _escribir_placeholder_png(carpeta: Path, escena_num: int, width: int = 1024, height: int = 576) -> Path:
    """Escribe una imagen placeholder (gris) para no dejar huecos cuando todo falla."""
    import base64
    carpeta.mkdir(parents=True, exist_ok=True)
    dest = carpeta / f"escena_{escena_num:04d}.png"
    try:
        from PIL import Image
        img = Image.new("RGB", (width, height), color=(128, 128, 128))
        img.save(dest)
        return dest
    except Exception:
        dest.write_bytes(base64.b64decode(_PLACEHOLDER_PNG_B64))
    return dest


def _aspect_ratio_from_size(width: int, height: int) -> str:
    """Calcula aspect_ratio para Replicate (16:9, 9:16, 1:1) según dimensiones."""
    if not width or not height:
        return "16:9"
    r = width / height if height else 1.0
    if r < 0.6:
        return "9:16"
    if r > 1.5:
        return "16:9"
    if abs(r - 1.0) < 0.2:
        return "1:1"
    return "16:9" if r > 1.0 else "9:16"


def _get_outfit_reference_path(outfit_key: str | None) -> Path | None:
    """Si existe la imagen de referencia del outfit en references/outfits/, devuelve su Path; si no, None."""
    if not outfit_key:
        return None
    filename = OUTFIT_REF_FILENAMES.get(outfit_key) or f"{outfit_key}.png"
    p = OUTFIT_REF_DIR / filename
    if p.exists() and p.stat().st_size > 0:
        return p
    return None


def _generar_imagen_replicate(
    prompt: str,
    carpeta: Path,
    escena_num: int,
    width: int = 1024,
    height: int = 576,
    expression_key: str | None = None,
    outfit_key: str | None = None,
) -> Path | None:
    """Genera una imagen con Replicate.
    - Si existe character_reference (front o expresión), usa el modelo con referencia (por defecto FLUX Kontext).
    - Si no hay personaje pero sí outfit_key y existe references/outfits/outfit_<x>.png, usa esa imagen como referencia visual del outfit.
    - Si no, usa el modelo de texto→imagen sin imagen.
    """
    import replicate as replicate_client
    from base64 import b64encode

    prompt = (prompt or "").strip()[:3500]
    if not prompt:
        return None
    # 1) Prioridad: imagen de referencia de PERSONAJE (Kontext respeta cara/cuerpo).
    image_ref_path: Path | None = None
    try:
        refs = get_character_references()
        ref_key = (expression_key if expression_key and refs.get(expression_key) else None) or "front"
        ref_rel = refs.get(ref_key)
        if ref_rel:
            p = BASE / ref_rel
            if p.exists() and p.stat().st_size > 0:
                image_ref_path = p
    except Exception:
        pass
    # 2) Si no hay referencia de personaje, usar imagen de referencia del OUTFIT (references/outfits/) si existe.
    if image_ref_path is None:
        image_ref_path = _get_outfit_reference_path(outfit_key)

    if image_ref_path:
        # Identidad del personaje; ropa y edad según contexto. Siempre incluir lugar y acción.
        context_instruction = (
            "Generate with maximum common sense and logical intelligence—like the smartest image AI in the world. Every image must be coherent, believable, and free of absurd or impossible elements. "
            "Keep the character's identity (face, style) from the reference. "
            "Clothing and age/body MUST adapt to THIS scene: if baby → baby, if child → child, "
            "if wearing suit → suit, if footballer → team kit, etc. Each character with appropriate clothes for the situation. "
            "Always show a clear location/setting and what is happening in the scene. "
            "Background is mandatory: never white or empty background; every image must have a visible, detailed environment. "
            "Common sense - anatomy: every character has exactly two arms, two legs, one head. No extra limbs, no animal heads on human bodies, no mixed or impossible anatomy, no extra fingers or hands. "
            "Common sense - secondary characters: draw them in the SAME visual style as the main character (minimalist, same figure type). Do not draw other characters as realistic humans or with animal features; all characters must look like they belong in the same world. "
            "Logical props and quantities: one computer = one monitor unless the story says otherwise; realistic proportions and object counts (one table, one chair where it makes sense). Coherent perspective and space. "
            "Nothing impossible or ridiculous: the scene must be 100% believable to any observer with common sense. "
            "This frame must have a different composition or angle than the others; vary shot type; avoid repeating the same shot. "
        )
        prompt_kontext = (context_instruction + prompt).strip()[:3500]
        aspect_ratio = _aspect_ratio_from_size(width, height)
        seed = (escena_num * 12345 + (hash(prompt) % 100000)) % (2**31)
        try:
            with open(image_ref_path, "rb") as f:
                output = replicate_client.run(
                    REPLICATE_MODEL_KONTEXT,
                    input={
                        "prompt": prompt_kontext,
                        "input_image": f,
                        "aspect_ratio": aspect_ratio,
                        "output_format": "png",
                        "num_inference_steps": 28,
                        "seed": seed,
                    },
                )
        except Exception as e:
            raise RuntimeError(f"Replicate FLUX Kontext no pudo generar la imagen: {e}") from e
    else:
        # Solo texto, sin referencia: usar modelo configurable (REPLICATE_MODEL_TEXT)
        aspect_ratio = "16:9"
        if width and height:
            r = width / height if height else 1.0
            if r < 0.6:
                aspect_ratio = "9:16"
            elif r > 1.5:
                aspect_ratio = "16:9"
            elif abs(r - 1.0) < 0.2:
                aspect_ratio = "1:1"
        try:
            output = replicate_client.run(
                REPLICATE_MODEL_TEXT,
                input={
                    "prompt": prompt,
                    "aspect_ratio": aspect_ratio,
                    "output_format": "png",
                    "num_outputs": 1,
                },
            )
        except Exception as e:
            raise RuntimeError(f"Replicate FLUX no pudo generar la imagen: {e}") from e
    if not output:
        return None
    # output puede ser lista de URLs o un FileOutput
    url = output[0] if isinstance(output, (list, tuple)) else output
    if hasattr(url, "read"):
        data = url.read()
    elif isinstance(url, str) and (url.startswith("http://") or url.startswith("https://")):
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        data = r.content
    else:
        return None
    carpeta.mkdir(parents=True, exist_ok=True)
    path = carpeta / f"escena_{escena_num:04d}.png"
    path.write_bytes(data)
    return path


def _prompt_fallback_stickman(escena_num: int) -> str:
    """Prompt de respaldo en estilo stickman cuando hay rechazo o error; evita fotos realistas aleatorias."""
    estilo = get_estilo_base()
    return (
        f"Simple 2D stickman style illustration, {estilo}. "
        "One character with round head and stick body, minimal background, neutral emotional moment, "
        "clean lines, no realism, no photography style."
    )


def _prompt_seguro_dalle(escena_num: int) -> str:
    """Prompt seguro en estilo stickman cuando el original fue rechazado (no genérico realista)."""
    return _prompt_fallback_stickman(escena_num)


def _reescribir_prompt_rechazado_para_dalle(prompt_rechazado: str, escena_num: int) -> str | None:
    """
    Si DALL-E rechazó el prompt por política de contenido, pide a GPT una versión que sugiera
    lo mismo sin ser explícito (ej. sugerir una muerte sin mostrarla). Solo para fallback tras rechazo.
    """
    prompt_rechazado = (prompt_rechazado or "").strip()[:3000]
    if not prompt_rechazado:
        return None
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    estilo = get_estilo_base()
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        r = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "El siguiente prompt de imagen fue rechazado por políticas de contenido (ej. violencia, muerte explícita). "
                        "Reescribilo para que SUGIERA la misma escena o emoción sin ser explícito: misma narrativa, mismo estilo (" + estilo + "), "
                        "pero evita mostrar violencia, sangre, muerte explícita. Ej: en vez de 'persona muerta', usa 'silencio, sombra, mano que cae, momento de pérdida'. "
                        "Devolvé SOLO el nuevo prompt, sin explicaciones, en un solo párrafo."
                    ),
                },
                {"role": "user", "content": f"Prompt rechazado:\n\n{prompt_rechazado}"},
            ],
            max_tokens=500,
            temperature=0.3,
        )
        out = (r.choices[0].message.content or "").strip()
        return out[:4000] if out else None
    except Exception:
        return None


def _generar_imagen_openai_dalle(
    prompt_text: str,
    carpeta: Path,
    escena_num: int,
    width: int,
    height: int,
) -> Path | None:
    """Genera una imagen con OpenAI DALL-E 3. El prompt se sanitiza con GPT antes de enviar
    para reducir rechazos por política de contenido. Si aun así es rechazado, reintenta con prompt stickman."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("USE_OPENAI_IMAGES está activo pero falta OPENAI_API_KEY en .env")
    # DALL-E 3 solo permite 1024x1024, 1792x1024, 1024x1792
    if width >= height * 1.5:
        size = "1792x1024"   # 16:9 aprox
    elif height >= width * 1.5:
        size = "1024x1792"   # 9:16 aprox
    else:
        size = "1024x1024"
    # Sanitizar con GPT para evitar rechazos; mantiene escena y estilo stickman
    prompt_clean = _sanitizar_prompt_para_dalle((prompt_text or "").strip(), escena_num)
    prompt_clean = (prompt_clean or "").strip()[:3800] or _prompt_fallback_stickman(escena_num)
    # Regla fija: un solo fotograma de ilustración, solo escena, sin ninguna interfaz y SIEMPRE el mismo estilo
    suffix = (
        " Single standalone illustration frame. Only the drawn scene content visible. "
        "Exact same flat 2D stickman style across every frame of this same video: same protagonist design, same body proportions, head size, line thickness and limited color palette. "
        "Never switch to realistic humans or a different cartoon style. Clean composition. No overlays, no text, no controls, no interface, no HUD. "
        "No floating or flying figures."
    )
    prompt_clean = (prompt_clean + suffix).strip()[:4000]

    def _llamar_dalle(prompt: str) -> Path | None:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size=size,
            quality="standard",
            n=1,
        )
        image_url = response.data[0].url
        if not image_url:
            return None
        img_response = requests.get(image_url, timeout=60)
        img_response.raise_for_status()
        carpeta.mkdir(parents=True, exist_ok=True)
        path = carpeta / f"escena_{escena_num:04d}.png"
        path.write_bytes(img_response.content)
        return path

    def _es_error_servidor(exc: Exception) -> bool:
        s = str(exc).lower()
        return "500" in s or "502" in s or "503" in s or "server_error" in s or "server had an error" in s

    # Reintentos ante error 500/502/503 del servidor (temporal)
    intentos_dalle = 3
    ultima_excepcion = None
    for intento in range(intentos_dalle):
        try:
            return _llamar_dalle(prompt_clean)
        except Exception as e:
            ultima_excepcion = e
            if _es_error_servidor(e) and intento < intentos_dalle - 1:
                espera = (intento + 1) * 5
                print(f"   ⚠️ Escena {escena_num}: error del servidor (500), reintento en {espera}s ({intento + 1}/{intentos_dalle})...")
                time.sleep(espera)
            else:
                break

    e = ultima_excepcion
    if e is None:
        return None
    err_str = str(e).lower()
    if "content_policy_violation" in err_str or "safety system" in err_str:
        prompt_alternativo = _reescribir_prompt_rechazado_para_dalle(prompt_clean, escena_num)
        if prompt_alternativo:
            print(f"   ⚠️ Escena {escena_num}: rechazado por DALL-E. Reescribiendo para sugerir la escena sin infringir políticas...")
            try:
                return _llamar_dalle(prompt_alternativo)
            except Exception:
                pass
        print(f"   ⚠️ Escena {escena_num}: usando prompt stickman de respaldo.")
        try:
            return _llamar_dalle(_prompt_seguro_dalle(escena_num))
        except Exception as e2:
            raise RuntimeError(
                f"DALL-E rechazó el prompt y el fallback también falló: {e2}. "
                "Para historias crudas o sensibles usá ComfyUI en lugar de DALL-E."
            ) from e2
    raise RuntimeError(f"DALL-E no pudo generar la imagen: {e}") from e


def generar_imagen(
    prompt: str,
    escena_num: int,
    carpeta: Path,
    width: int | None = None,
    height: int | None = None,
    expression_key: str | None = None,
    outfit_key: str | None = None,
) -> Path | None:
    """Genera una imagen con Replicate (FLUX) o ComfyUI según IMAGE_BACKEND. outfit_key se usa para imagen de referencia en references/outfits/ si no hay character ref."""
    instrucciones = get_instrucciones_imagenes()
    params = instrucciones.get("parametros_sd", {})
    img_width = width if width is not None else params.get("width", 1024)
    img_height = height if height is not None else params.get("height", 576)

    if _usar_replicate():
        for intento in range(MAX_REINTENTOS):
            try:
                path = _generar_imagen_replicate(
                    prompt, carpeta, escena_num, img_width, img_height,
                    expression_key=expression_key, outfit_key=outfit_key,
                )
                if path:
                    return path
            except RuntimeError:
                raise
            except Exception as e:
                if intento < MAX_REINTENTOS - 1:
                    time.sleep(PAUSA_REINTENTO)
                else:
                    raise RuntimeError(f"Falló generación escena {escena_num} con Replicate: {e}") from e
        return None

    negative = get_negative_prompt()
    for intento in range(MAX_REINTENTOS):
        try:
            path = _generar_imagen_comfyui(
                prompt,
                negative,
                carpeta,
                escena_num,
                img_width,
                img_height,
            )
            if path:
                return path
        except RuntimeError:
            raise
        except Exception as e:
            if intento < MAX_REINTENTOS - 1:
                time.sleep(PAUSA_REINTENTO)
            else:
                raise RuntimeError(f"Falló generación escena {escena_num}: {e}") from e
    if _usar_replicate():
        raise RuntimeError("Replicate no respondió. Revisá REPLICATE_API_TOKEN e IMAGE_BACKEND=replicate en .env.")
    raise RuntimeError(_comfyui_error_msg())


def _generar_una_escena(
    item: tuple[Escena, str] | tuple[Escena, str, str | None] | tuple[Escena, str, str | None, str],
    carpeta: Path,
    width: int | None,
    height: int | None,
) -> tuple[int, Path | None]:
    """Helper para paralelo. Item: (Escena, prompt), (Escena, prompt, expression_key) o (Escena, prompt, expression_key, outfit_key)."""
    escena = item[0]
    prompt = item[1]
    expression_key = item[2] if len(item) >= 3 else None
    outfit_key = item[3] if len(item) >= 4 else None
    path = generar_imagen(
        prompt, escena.numero, carpeta, width=width, height=height,
        expression_key=expression_key, outfit_key=outfit_key,
    )
    return (escena.numero, path)


def generar_lote(
    escenas_con_prompts: list[tuple[Escena, str]] | list[tuple[Escena, str, str | None]] | list[tuple[Escena, str, str | None, str]],
    subcarpeta: str = "default",
    width: int | None = None,
    height: int | None = None,
    on_progress: Callable[[int, int], None] | None = None,
) -> list[Path]:
    """Genera todas las imágenes con Replicate (FLUX) o ComfyUI. Si una falla con Replicate se usa placeholder.
    Cada elemento puede ser (Escena, prompt) o (Escena, prompt, expression_key) para referencia de expresión."""
    if not _usar_replicate() and not _comfyui_disponible():
        raise RuntimeError(_comfyui_error_msg())
    carpeta = OUTPUT_IMAGES / subcarpeta
    instrucciones = get_instrucciones_imagenes()
    params = instrucciones.get("parametros_sd", {})
    img_w = width if width is not None else params.get("width", 1024)
    img_h = height if height is not None else params.get("height", 576)
    usar_replicate = _usar_replicate()
    total = len(escenas_con_prompts)
    rutas = []
    for idx, item in enumerate(escenas_con_prompts, start=1):
        escena = item[0]
        prompt = item[1]
        expression_key = item[2] if len(item) >= 3 else None
        outfit_key = item[3] if len(item) >= 4 else None
        print(f"   🖼️ Imagen {idx}/{total} (escena {escena.numero})...")
        path = None
        # Pequeño bucle local para respetar rate limit de Replicate (6 req/min ≈ 1 cada 10s)
        intentos_locales = 3
        for intento in range(intentos_locales):
            try:
                path = generar_imagen(
                    prompt, escena.numero, carpeta, width=width, height=height,
                    expression_key=expression_key, outfit_key=outfit_key,
                )
                break
            except Exception as e:
                # Si no usamos Replicate, delegar comportamiento anterior.
                if not usar_replicate:
                    raise
                msg = str(e)
                # Manejo específico de 429 (rate limit): esperar y reintentar en vez de ir directo a placeholder.
                if "status: 429" in msg or "rate limit" in msg.lower():
                    espera = 10
                    if intento < intentos_locales - 1:
                        print(
                            f"   ⚠️ Escena {escena.numero}: límite de tasa de Replicate (429). "
                            f"Esperando {espera}s antes de reintentar ({intento + 1}/{intentos_locales})..."
                        )
                        time.sleep(espera)
                        continue
                # Otros errores (o demasiados 429): usar placeholder y seguir
                print(f"   ⚠️ Escena {escena.numero}: falló ({e}). Usando placeholder.")
                path = _escribir_placeholder_png(carpeta, escena.numero, img_w, img_h)
                break
        if path:
            rutas.append(path)
    if len(rutas) != len(escenas_con_prompts) and not usar_replicate:
        raise RuntimeError(f"Se generaron {len(rutas)} de {len(escenas_con_prompts)} imágenes.")
    return rutas

