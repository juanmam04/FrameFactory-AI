"""FASE 6: Generación de imágenes con ComfyUI (local o RunPod)."""
import os
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable

import requests
from dotenv import load_dotenv

from .config_loader import (
    BASE,
    get_negative_prompt,
    get_instrucciones_imagenes,
    get_estilo_base,
    get_character_references,
    get_character_reference_mode,
    get_kontext_context_instruction,
)
from .kontext_prompt import build_kontext_prompt_for_replicate
from .storyboard_continuity import comfyui_seed_from_material
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

# Replicate: modelo texto→imagen por .env (por defecto FLUX.1 [dev], mayor fidelidad que schnell).
# REPLICATE_IMAGE_MODEL (nuevo) tiene prioridad; si no está, REPLICATE_FLUX_MODEL (legacy).
REPLICATE_MODEL_TEXT = (
    os.getenv("REPLICATE_IMAGE_MODEL")
    or os.getenv("REPLICATE_FLUX_MODEL")
    or "black-forest-labs/flux-dev"
).strip()
# Imagen + texto (Kontext): referencia del protagonista en todas las escenas cuando el PNG existe.
REPLICATE_MODEL_KONTEXT = os.getenv(
    "REPLICATE_IMAGE_MODEL_WITH_REF", "black-forest-labs/flux-kontext-dev"
).strip()
# Si hay character_reference en visual_bible: preferir Kontext cuando el PNG existe.
# Si las rutas están pero el archivo no está en disco: fallback a FLUX solo texto (un aviso, no error).
REPLICATE_FORCE_KONTEXT = os.getenv("REPLICATE_FORCE_KONTEXT", "0").strip().lower() not in (
    "0",
    "false",
    "no",
)
_warned_kontext_missing_ref: bool = False

# Replicate (cuenta con poco crédito): ~6 predicciones/min y burst 1 → espaciar inicios de request.
_replicate_spacing_lock = threading.Lock()
_replicate_last_prediction_mono: float = 0.0


def _replicate_min_interval_sec() -> float:
    """Segundos mínimos entre el inicio de cada predicción. Default 11s si no configurás nada (≈6/min)."""
    raw = os.getenv("REPLICATE_MIN_INTERVAL_SEC")
    if raw is not None and str(raw).strip() != "":
        try:
            return max(0.0, float(raw))
        except ValueError:
            pass
    raw2 = os.getenv("REPLICATE_INTER_FRAME_DELAY_SEC")
    if raw2 is not None and str(raw2).strip() != "":
        try:
            return max(0.0, float(raw2))
        except ValueError:
            pass
    return 11.0


def _replicate_spacing_wait() -> None:
    """Evita 429 al encadenar muchas escenas; no afecta a ComfyUI."""
    global _replicate_last_prediction_mono
    interval = _replicate_min_interval_sec()
    if interval <= 0:
        return
    with _replicate_spacing_lock:
        now = time.monotonic()
        if _replicate_last_prediction_mono > 0:
            wait = interval - (now - _replicate_last_prediction_mono)
            if wait > 0:
                time.sleep(wait)
        _replicate_last_prediction_mono = time.monotonic()


def _replicate_text_model_input(prompt: str, aspect_ratio: str) -> dict:
    """Inputs para el modelo texto→imagen (flux-dev vs schnell difieren ligeramente)."""
    model_low = REPLICATE_MODEL_TEXT.lower()
    inp: dict[str, str | int | float] = {
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "output_format": "png",
    }
    if "schnell" in model_low:
        inp["num_outputs"] = 1
        return inp
    steps = os.getenv("REPLICATE_FLUX_DEV_STEPS", "28").strip()
    try:
        inp["num_inference_steps"] = max(1, min(50, int(steps)))
    except ValueError:
        inp["num_inference_steps"] = 28
    guidance = os.getenv("REPLICATE_FLUX_DEV_GUIDANCE", "3.5").strip()
    try:
        inp["guidance"] = float(guidance)
    except ValueError:
        inp["guidance"] = 3.5
    return inp

def _usar_replicate() -> bool:
    """Usar SIEMPRE Replicate (FLUX) cuando haya token; ComfyUI queda como opción legacy."""
    return bool(os.getenv("REPLICATE_API_TOKEN", "").strip())

def _replicate_disponible() -> bool:
    return bool(os.getenv("REPLICATE_API_TOKEN", "").strip())

# Timeouts: más largos cuando ComfyUI está en la nube (RunPod, etc.)
def _is_remote_comfy() -> bool:
    # Leer URL en tiempo de ejecución (tests y .env pueden cambiar COMFYUI_URL sin recargar el módulo).
    u = (os.getenv("COMFYUI_URL") or "http://127.0.0.1:8188").strip().rstrip("/").lower()
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
    seed: int | None = None,
) -> Path | None:
    """Envía prompt a ComfyUI, espera resultado y guarda la imagen en carpeta/escena_XXXX.png."""
    timeout_post = timeout_post if timeout_post is not None else _comfy_timeout_post()
    timeout_poll = timeout_poll if timeout_poll is not None else _comfy_timeout_poll()
    workflow = _workflow_comfyui(prompt_text, negative, width, height, seed=seed)
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


def _resolve_protagonist_reference_path(expression_key: str | None) -> Path | None:
    """
    Imagen de referencia del protagonista para Kontext.
    Prioriza siempre ``front`` cuando existe (misma identidad en todas las escenas); si no, expresión u otras claves.
    """
    try:
        refs = get_character_references() or {}
    except Exception:
        refs = {}
    if not refs:
        return None

    def _path_for_key(k: str) -> Path | None:
        rel = refs.get(k)
        if not rel or not isinstance(rel, str):
            return None
        p = BASE / rel.strip()
        if p.exists() and p.stat().st_size > 0:
            return p
        return None

    p = _path_for_key("front")
    if p:
        return p
    if expression_key:
        p = _path_for_key(expression_key)
        if p:
            return p
    for k in ("closeup", "side"):
        p = _path_for_key(k)
        if p:
            return p
    for k in refs:
        p = _path_for_key(k)
        if p:
            return p
    return None


def _protagonist_ref_misconfigured_message() -> str | None:
    """Hay rutas en character_reference pero ningún archivo válido en disco."""
    try:
        refs = get_character_references() or {}
    except Exception:
        return None
    configured: list[str] = []
    for v in refs.values():
        if v and isinstance(v, str) and v.strip():
            configured.append(v.strip())
    if not configured:
        return None
    for rel in configured:
        p = BASE / rel
        if p.exists() and p.stat().st_size > 0:
            return None
    first = configured[0]
    return (
        "visual_bible define character_reference pero ningún PNG válido en disco "
        f"(ej. {BASE / first}). Colocá el archivo en esa ruta o quitá las entradas vacías en la bible."
    )


def _replicate_run_with_retry(run_fn, max_retries: int | None = None):
    """
    Replicate suele responder 429 con poco crédito o burst bajo; reintenta con backoff.
    REPLICATE_MAX_RETRIES (default 6), REPLICATE_RETRY_BASE_SEC (default 12).
    """
    if max_retries is None:
        max_retries = int(os.getenv("REPLICATE_MAX_RETRIES", "6"))
    base = float(os.getenv("REPLICATE_RETRY_BASE_SEC", "15"))
    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            return run_fn()
        except Exception as e:
            last_err = e
            err_s = str(e).lower()
            is_rate = "429" in err_s or "throttl" in err_s or "rate limit" in err_s
            if not is_rate or attempt >= max_retries - 1:
                break
            wait = base * (attempt + 1)
            print(f"   ⏳ Replicate ocupado/límite ({e}); reintento en {wait:.0f}s…")
            time.sleep(wait)
    if last_err:
        raise last_err
    raise RuntimeError("Replicate: sin respuesta tras reintentos")


def _is_missing_character_ref_kontext_error(exc: BaseException) -> bool:
    """True si el fallo es por bible con character_reference pero sin PNG (msg viejo o nuevo)."""
    s = str(exc).lower()
    if "character_reference" not in s:
        return False
    return (
        "kontext" in s
        or "replicate kontext" in s
        or "no existe" in s
        or "ningún png" in s
        or "ningun png" in s
        or "sin referencia" in s
        or "png en disco" in s
    )


def _generar_imagen_replicate(
    prompt: str,
    carpeta: Path,
    escena_num: int,
    width: int = 1024,
    height: int = 576,
    expression_key: str | None = None,
    outfit_key: str | None = None,
    *,
    text_only: bool = False,
) -> Path | None:
    """Genera una imagen con Replicate.
    - Con PNG de personaje en visual_bible: siempre FLUX Kontext con ``input_image`` (prioridad ``front``).
    - Sin referencia de personaje: modelo texto→imagen (por defecto flux-dev). outfit_key no sustituye al personaje en Replicate.
    """
    import replicate as replicate_client

    _ = outfit_key  # reservado; consistencia del protagonista = solo character_reference (Kontext)
    prompt = (prompt or "").strip()[:3500]
    if not prompt:
        return None

    _replicate_spacing_wait()

    image_ref_path = None if text_only else _resolve_protagonist_reference_path(expression_key)
    if image_ref_path is None and REPLICATE_FORCE_KONTEXT and not text_only:
        msg = _protagonist_ref_misconfigured_message()
        if msg:
            global _warned_kontext_missing_ref
            if not _warned_kontext_missing_ref:
                print(f"⚠️ {msg}")
                print(
                    "   → Fallback automático: FLUX solo texto (sin Kontext) hasta que exista el PNG. "
                    "(Esta advertencia no se repite.)"
                )
                _warned_kontext_missing_ref = True
            # No lanzar: misma rama que sin referencia → modelo texto→imagen

    if image_ref_path:
        context_instruction = get_kontext_context_instruction()
        prompt_kontext = build_kontext_prompt_for_replicate(
            prompt,
            context_instruction,
            get_character_reference_mode(),
            max_chars=3500,
        )
        aspect_ratio = _aspect_ratio_from_size(width, height)
        seed = (escena_num * 12345 + (hash(prompt) % 100000)) % (2**31)
        def _run_kontext():
            with open(image_ref_path, "rb") as f:
                return replicate_client.run(
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

        output = _replicate_run_with_retry(_run_kontext)
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
        def _run_text():
            return replicate_client.run(
                REPLICATE_MODEL_TEXT,
                input=_replicate_text_model_input(prompt, aspect_ratio),
            )

        output = _replicate_run_with_retry(_run_text)
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
    comfy_seed: int | None = None,
    *,
    replicate_text_only: bool = False,
) -> Path | None:
    """Genera una imagen con Replicate (FLUX) o ComfyUI. En Replicate, la referencia del protagonista es solo ``character_reference`` (Kontext); outfit_key no reemplaza al PNG del personaje."""
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
                    text_only=replicate_text_only,
                )
                if path:
                    return path
            except RuntimeError as e:
                if (
                    not replicate_text_only
                    and _is_missing_character_ref_kontext_error(e)
                ):
                    path = _generar_imagen_replicate(
                        prompt, carpeta, escena_num, img_width, img_height,
                        expression_key=expression_key, outfit_key=outfit_key,
                        text_only=True,
                    )
                    if path:
                        global _warned_kontext_missing_ref
                        if not _warned_kontext_missing_ref:
                            print(
                                "⚠️ Referencia Kontext no disponible; se usa FLUX solo texto "
                                "(reintento automático por escena)."
                            )
                            _warned_kontext_missing_ref = True
                        return path
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
                seed=comfy_seed,
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
    escenas_con_prompts: list[tuple[Escena, str]]
    | list[tuple[Escena, str, str | None]]
    | list[tuple[Escena, str, str | None, str]]
    | list[tuple[Escena, str, str | None, str, str]],
    subcarpeta: str = "default",
    width: int | None = None,
    height: int | None = None,
    on_progress: Callable[[int, int], None] | None = None,
) -> list[Path]:
    """Genera todas las imágenes con Replicate (FLUX) o ComfyUI. Si una falla con Replicate se usa placeholder.
    Tupla extendida opcional: (Escena, prompt, expression_key, outfit_key, seed_material) — seed_material alimenta
    semilla estable en ComfyUI."""
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
        seed_material = item[4] if len(item) >= 5 else ""
        comfy_seed = None
        if seed_material and not usar_replicate:
            comfy_seed = comfyui_seed_from_material(f"{subcarpeta}\0{seed_material}")
        print(f"   🖼️ Imagen {idx}/{total} (escena {escena.numero})...")
        path = None
        # Pequeño bucle local para respetar rate limit de Replicate (6 req/min ≈ 1 cada 10s)
        intentos_locales = 3
        for intento in range(intentos_locales):
            try:
                path = generar_imagen(
                    prompt, escena.numero, carpeta, width=width, height=height,
                    expression_key=expression_key, outfit_key=outfit_key,
                    comfy_seed=comfy_seed,
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
                # Kontext exigido pero sin PNG (código viejo en memoria o FORCE=1): FLUX texto, no placeholder.
                if _is_missing_character_ref_kontext_error(e):
                    try:
                        path = _generar_imagen_replicate(
                            prompt,
                            carpeta,
                            escena.numero,
                            img_w,
                            img_h,
                            expression_key=expression_key,
                            outfit_key=outfit_key,
                            text_only=True,
                        )
                        if path:
                            global _warned_kontext_missing_ref
                            if not _warned_kontext_missing_ref:
                                print(
                                    "⚠️ Sin PNG de personaje para Kontext: usando FLUX solo texto "
                                    "(fallback en lote; reiniciá Streamlit para cargar el último código)."
                                )
                                _warned_kontext_missing_ref = True
                            break
                    except Exception as e2:
                        e = e2
                        msg = str(e2)
                # Otros errores (o demasiados 429): usar placeholder y seguir
                print(f"   ⚠️ Escena {escena.numero}: falló ({e}). Usando placeholder.")
                path = _escribir_placeholder_png(carpeta, escena.numero, img_w, img_h)
                break
        if path:
            rutas.append(path)
    if len(rutas) != len(escenas_con_prompts) and not usar_replicate:
        raise RuntimeError(f"Se generaron {len(rutas)} de {len(escenas_con_prompts)} imágenes.")
    return rutas

