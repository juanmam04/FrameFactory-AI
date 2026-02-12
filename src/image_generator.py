"""FASE 6: Generación de imágenes para cada escena.
Backends: OpenAI DALL-E (por defecto), ComfyUI (SD), o placeholder.
IMAGE_BACKEND=openai | comfyui | placeholder.
Con openai, DALL_E_PARALLEL (ej. 3) genera varias imágenes a la vez para ir más rápido.
"""
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable

import requests
from dotenv import load_dotenv

from .config_loader import BASE, get_negative_prompt, get_instrucciones_imagenes
from .scene_splitter import Escena

load_dotenv(BASE / ".env")

# Backend de imágenes: openai (DALL-E 3, por defecto y recomendado), comfyui (SD), placeholder
def _get_image_backend() -> str:
    load_dotenv(BASE / ".env")
    backend = (os.getenv("IMAGE_BACKEND") or "openai").strip().lower()
    if backend not in ("comfyui", "openai", "placeholder"):
        return "openai"
    return backend

OUTPUT_IMAGES = BASE / "output" / "imagenes"
COMFY_CHECKPOINT_DEFAULT = "v1-5-pruned-emaonly.safetensors"
_resolved_checkpoint: str | None = None


def _get_comfy_url() -> str:
    """Lee COMFYUI_URL del entorno cada vez (evita caché de Streamlit/import)."""
    load_dotenv(BASE / ".env")
    return (os.getenv("COMFYUI_URL") or "http://127.0.0.1:8188").strip().rstrip("/")


# Compatibilidad: variable usada en varios sitios
# Para compatibilidad con app/tests: usar COMFY_URL() para obtener la URL actual
COMFY_URL = _get_comfy_url


# Timeouts: más largos cuando ComfyUI está en la nube (RunPod, etc.)
def _is_remote_comfy() -> bool:
    u = _get_comfy_url().lower()
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
        f"ComfyUI no está corriendo en {_get_comfy_url()}. "
        "Inicialo en otra terminal (ej. python main.py) o revisá COMFYUI_URL en .env si usás RunPod/nube."
    )


def _lista_checkpoints_comfyui() -> list[str]:
    """Obtiene la lista de nombres de checkpoints desde ComfyUI /object_info."""
    r = requests.get(f"{_get_comfy_url()}/object_info", timeout=_comfy_timeout_connect(), verify=COMFY_VERIFY_SSL)
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
        r = requests.get(f"{_get_comfy_url()}/queue", timeout=_comfy_timeout_connect(), verify=COMFY_VERIFY_SSL)
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
            f"{_get_comfy_url()}/prompt",
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
    history_url = f"{_get_comfy_url()}/history/{prompt_id}"
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
                view = requests.get(f"{_get_comfy_url()}/view", params=params, timeout=view_timeout, verify=COMFY_VERIFY_SSL)
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


def _generar_imagen_placeholder(
    carpeta: Path,
    escena_num: int,
    width: int,
    height: int,
) -> Path:
    """Genera una imagen placeholder (color + texto Escena N). No usa ningún servicio externo."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        raise RuntimeError("Pillow (PIL) es necesario para el backend 'placeholder'. pip install Pillow")
    carpeta.mkdir(parents=True, exist_ok=True)
    path = carpeta / f"escena_{escena_num:04d}.png"
    img = Image.new("RGB", (width, height), color=(40, 44, 52))
    draw = ImageDraw.Draw(img)
    text = f"Escena {escena_num}"
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", min(width, height) // 15)
    except (OSError, TypeError):
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (width - tw) // 2
    y = (height - th) // 2
    draw.text((x, y), text, fill=(200, 200, 200), font=font)
    img.save(path)
    return path


def _generar_imagen_openai(
    prompt: str,
    carpeta: Path,
    escena_num: int,
    width: int,
    height: int,
) -> Path | None:
    """Genera una imagen con DALL-E 3. Sigue mejor las instrucciones (ej. stickman + contexto) que SD 1.5."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "IMAGE_BACKEND=openai requiere OPENAI_API_KEY en .env. "
            "Sin clave no se pueden generar imágenes con DALL-E."
        )
    # DALL-E 3 tamaños: 1024x1024, 1792x1024, 1024x1792
    if width >= height and width / max(height, 1) >= 1.5:
        size = "1792x1024"
    elif height > width and height / max(width, 1) >= 1.5:
        size = "1024x1792"
    else:
        size = "1024x1024"
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt[:4000],
            size=size,
            quality="standard",
            n=1,
        )
        image_url = response.data[0].url
        r = requests.get(image_url, timeout=60)
        r.raise_for_status()
        carpeta.mkdir(parents=True, exist_ok=True)
        path = carpeta / f"escena_{escena_num:04d}.png"
        path.write_bytes(r.content)
        # DALL-E solo devuelve 1024x1024, 1792x1024 o 1024x1792. Llevar exactamente a (width, height):
        # recortar a 16:9 si hace falta y luego redimensionar, para no deformar ni dejar barras.
        if (width, height) not in ((1792, 1024), (1024, 1024), (1024, 1792)):
            try:
                from PIL import Image
                img = Image.open(path).convert("RGB")
                w, h = img.size
                target_ratio = width / height
                current_ratio = w / h
                if abs(current_ratio - target_ratio) > 0.01:
                    # Recortar centro al aspect ratio pedido (ej. 16:9)
                    if current_ratio > target_ratio:
                        new_w = int(h * target_ratio)
                        left = (w - new_w) // 2
                        img = img.crop((left, 0, left + new_w, h))
                    else:
                        new_h = int(w / target_ratio)
                        top = (h - new_h) // 2
                        img = img.crop((0, top, w, top + new_h))
                resample = getattr(Image, "Resampling", Image).LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS
                img = img.resize((width, height), resample)
                img.save(path, "PNG")
            except Exception:
                pass
        return path
    except Exception as e:
        raise RuntimeError(f"DALL-E falló para escena {escena_num}: {e}") from e


def generar_imagen(
    prompt: str,
    escena_num: int,
    carpeta: Path,
    width: int | None = None,
    height: int | None = None,
) -> Path | None:
    """Genera una imagen según IMAGE_BACKEND: comfyui, openai (DALL-E) o placeholder."""
    instrucciones = get_instrucciones_imagenes()
    params = instrucciones.get("parametros_sd", {})
    img_width = width if width is not None else params.get("width", 1024)
    img_height = height if height is not None else params.get("height", 576)
    backend = _get_image_backend()

    if backend == "placeholder":
        return _generar_imagen_placeholder(carpeta, escena_num, img_width, img_height)

    if backend == "openai":
        return _generar_imagen_openai(prompt, carpeta, escena_num, img_width, img_height)

    # comfyui
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
    raise RuntimeError(_comfyui_error_msg())


def _generar_una_escena(
    item: tuple[Escena, str],
    carpeta: Path,
    width: int | None,
    height: int | None,
) -> tuple[int, Path | None]:
    """Helper para paralelo: (numero_escena, path o None)."""
    escena, prompt = item
    path = generar_imagen(prompt, escena.numero, carpeta, width=width, height=height)
    return (escena.numero, path)


def generar_lote(
    escenas_con_prompts: list[tuple[Escena, str]],
    subcarpeta: str = "default",
    width: int | None = None,
    height: int | None = None,
    on_progress: Callable[[int, int], None] | None = None,
) -> list[Path]:
    """Genera todas las imágenes según IMAGE_BACKEND.
    Con openai, usa DALL_E_PARALLEL (ej. 3) para generar varias a la vez.
    on_progress(opcional): callback(current_1based, total).
    """
    backend = _get_image_backend()
    if backend == "comfyui" and not _comfyui_disponible():
        raise RuntimeError(_comfyui_error_msg())
    if backend == "openai" and not os.getenv("OPENAI_API_KEY", "").strip():
        raise RuntimeError(
            "IMAGE_BACKEND=openai requiere OPENAI_API_KEY en .env para generar imágenes con DALL-E."
        )
    carpeta = OUTPUT_IMAGES / subcarpeta
    total = len(escenas_con_prompts)
    instrucciones = get_instrucciones_imagenes()
    params = instrucciones.get("parametros_sd", {})
    w = width if width is not None else params.get("width", 1024)
    h = height if height is not None else params.get("height", 576)

    # Paralelo: varias imágenes a la vez (OpenAI o ComfyUI)
    parallel = 1
    if backend == "openai":
        try:
            parallel = max(1, min(5, int(os.getenv("DALL_E_PARALLEL", "2"))))
        except (TypeError, ValueError):
            parallel = 1
    elif backend == "comfyui":
        try:
            parallel = max(1, min(6, int(os.getenv("COMFYUI_PARALLEL", "3"))))
        except (TypeError, ValueError):
            parallel = 1

    if parallel > 1 and total > 1:
        rutas_por_num: dict[int, Path] = {}
        completed = 0
        with ThreadPoolExecutor(max_workers=parallel) as executor:
            futures = {
                executor.submit(_generar_una_escena, item, carpeta, w, h): item
                for item in escenas_con_prompts
            }
            for fut in as_completed(futures):
                num, path = fut.result()
                if path:
                    rutas_por_num[num] = path
                completed += 1
                if on_progress:
                    on_progress(completed, total)
        return [rutas_por_num[n] for n in sorted(rutas_por_num)]

    rutas = []
    for i, (escena, prompt) in enumerate(escenas_con_prompts):
        if on_progress:
            on_progress(i + 1, total)
        path = generar_imagen(prompt, escena.numero, carpeta, width=width, height=height)
        if path:
            rutas.append(path)
    return rutas
