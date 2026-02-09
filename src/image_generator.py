"""FASE 6: Generación masiva de imágenes con ComfyUI. Sin placeholders: si ComfyUI no está, falla claro."""
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

from .config_loader import BASE, get_negative_prompt, get_instrucciones_imagenes
from .scene_splitter import Escena

load_dotenv(BASE / ".env")

OUTPUT_IMAGES = BASE / "output" / "imagenes"
COMFY_URL = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188").rstrip("/")
COMFY_CHECKPOINT_DEFAULT = "v1-5-pruned-emaonly.safetensors"
_resolved_checkpoint: str | None = None

# Timeouts: más largos cuando ComfyUI está en la nube (RunPod, etc.)
def _is_remote_comfy() -> bool:
    u = (os.getenv("COMFYUI_URL") or "").strip().lower()
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

COMFYUI_ERROR_MSG = (
    f"ComfyUI no está corriendo en {COMFY_URL}. "
    "Inicialo en otra terminal (ej. python main.py) o revisá COMFYUI_URL en .env si usás RunPod/nube."
)


def _get_checkpoint() -> str:
    """Usa COMFYUI_CHECKPOINT si está definido; si no, obtiene el primer checkpoint de ComfyUI /object_info."""
    global _resolved_checkpoint
    env_ckpt = (os.getenv("COMFYUI_CHECKPOINT") or "").strip()
    if env_ckpt:
        return env_ckpt
    if _resolved_checkpoint is not None:
        return _resolved_checkpoint
    try:
        r = requests.get(f"{COMFY_URL}/object_info", timeout=_comfy_timeout_connect(), verify=COMFY_VERIFY_SSL)
        if r.status_code != 200:
            _resolved_checkpoint = COMFY_CHECKPOINT_DEFAULT
            return _resolved_checkpoint
        data = r.json()
        loader = (data or {}).get("CheckpointLoaderSimple") or {}
        required = (loader.get("input") or {}).get("required") or {}
        ckpt_name = required.get("ckpt_name")
        if ckpt_name is not None and isinstance(ckpt_name, list):
            if len(ckpt_name) == 0:
                raise RuntimeError(
                    "ComfyUI no tiene ningún checkpoint en models/checkpoints. "
                    "Añadí al menos un .safetensors o .ckpt ahí, o configurá COMFYUI_CHECKPOINT en .env con el nombre exacto."
                )
            first = ckpt_name[0]
            if isinstance(first, list) and len(first) > 0:
                name = first[0]
            elif isinstance(first, str):
                name = first
            else:
                name = None
            if name and isinstance(name, str):
                _resolved_checkpoint = name
                return _resolved_checkpoint
    except RuntimeError:
        raise
    except Exception:
        pass
    _resolved_checkpoint = COMFY_CHECKPOINT_DEFAULT
    return _resolved_checkpoint


def _workflow_comfyui(prompt_text: str, negative: str, width: int, height: int, seed: int | None = None):
    """Workflow ComfyUI. width/height se redondean a múltiplos de 8."""
    import random
    seed = seed if seed is not None else random.randint(0, 999999)
    w, h = (width // 8) * 8, (height // 8) * 8
    if w < 64:
        w = 64
    if h < 64:
        h = 64
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
                "steps": 15,
                "cfg": 8,
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
        raise RuntimeError(COMFYUI_ERROR_MSG + f" Detalle: {e}") from e

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


def generar_imagen(
    prompt: str,
    escena_num: int,
    carpeta: Path,
    width: int | None = None,
    height: int | None = None,
) -> Path | None:
    """Genera una imagen con ComfyUI. Si no está disponible, lanza error (sin placeholders)."""
    instrucciones = get_instrucciones_imagenes()
    params = instrucciones.get("parametros_sd", {})
    img_width = width if width is not None else params.get("width", 1024)
    img_height = height if height is not None else params.get("height", 576)
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
    raise RuntimeError(COMFYUI_ERROR_MSG)


def generar_lote(
    escenas_con_prompts: list[tuple[Escena, str]],
    subcarpeta: str = "default",
    width: int | None = None,
    height: int | None = None,
) -> list[Path]:
    """Genera todas las imágenes con ComfyUI. Falla al inicio si ComfyUI no está."""
    if not _comfyui_disponible():
        raise RuntimeError(COMFYUI_ERROR_MSG)
    carpeta = OUTPUT_IMAGES / subcarpeta
    rutas = []
    for escena, prompt in escenas_con_prompts:
        path = generar_imagen(prompt, escena.numero, carpeta, width=width, height=height)
        if path:
            rutas.append(path)
    return rutas
