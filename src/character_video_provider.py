"""Proveedor MVP: clip de video desde imagen fija + audio usando FFmpeg."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import mimetypes
from pathlib import Path

import requests


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _render_block_external_api(block: dict, audio_path: Path, character_image: Path, output_path: Path) -> Path:
    """
    Renderiza un clip llamando una API externa (multipart upload).

    Variables de entorno esperadas:
    - CHARACTER_ANIMATOR_URL (obligatoria): endpoint POST para crear render.
    - CHARACTER_ANIMATOR_API_KEY (opcional): se manda como Bearer.
    - CHARACTER_ANIMATOR_TIMEOUT_SECONDS (opcional, default 180).
    - CHARACTER_ANIMATOR_VERIFY_SSL (opcional, default true).
    - CHARACTER_ANIMATOR_TEXT_FIELD (opcional, default "text").
    - CHARACTER_ANIMATOR_RESPONSE_VIDEO_URL_FIELD (opcional, default "video_url").
    - CHARACTER_ANIMATOR_RESPONSE_VIDEO_B64_FIELD (opcional, default "video_base64").

    El endpoint debe aceptar:
    - file "image" (imagen del personaje)
    - file "audio" (narración)
    - campo de texto (configurable)
    """
    endpoint = os.getenv("CHARACTER_ANIMATOR_URL", "").strip()
    if not endpoint:
        raise RuntimeError("Falta CHARACTER_ANIMATOR_URL para usar proveedor external.")

    timeout = int(os.getenv("CHARACTER_ANIMATOR_TIMEOUT_SECONDS", "180"))
    verify_ssl = _bool_env("CHARACTER_ANIMATOR_VERIFY_SSL", default=True)
    text_field = os.getenv("CHARACTER_ANIMATOR_TEXT_FIELD", "text").strip() or "text"
    out_url_field = os.getenv("CHARACTER_ANIMATOR_RESPONSE_VIDEO_URL_FIELD", "video_url").strip() or "video_url"
    out_b64_field = os.getenv("CHARACTER_ANIMATOR_RESPONSE_VIDEO_B64_FIELD", "video_base64").strip() or "video_base64"

    headers: dict[str, str] = {}
    api_key = os.getenv("CHARACTER_ANIMATOR_API_KEY", "").strip()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    text = (block.get("text") or "").strip()
    payload = {text_field: text}

    with open(character_image, "rb") as img_f, open(audio_path, "rb") as aud_f:
        files = {
            "image": (character_image.name, img_f, "application/octet-stream"),
            "audio": (audio_path.name, aud_f, "application/octet-stream"),
        }
        resp = requests.post(
            endpoint,
            headers=headers,
            data=payload,
            files=files,
            timeout=timeout,
            verify=verify_ssl,
        )
    if resp.status_code >= 400:
        raise RuntimeError(f"API externa devolvió {resp.status_code}: {resp.text[:300]}")

    ctype = (resp.headers.get("content-type") or "").lower()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Si responde directamente el mp4/binario
    if "video/" in ctype or "application/octet-stream" in ctype:
        output_path.write_bytes(resp.content)
        return output_path

    # Si responde JSON con URL o base64
    data = resp.json()
    if not isinstance(data, dict):
        raise RuntimeError("Respuesta inválida de API externa (se esperaba JSON objeto o binario).")

    video_url = data.get(out_url_field)
    if isinstance(video_url, str) and video_url.strip():
        dl = requests.get(video_url.strip(), timeout=timeout, verify=verify_ssl)
        if dl.status_code >= 400:
            raise RuntimeError(f"No se pudo descargar video resultante ({dl.status_code}).")
        output_path.write_bytes(dl.content)
        return output_path

    video_b64 = data.get(out_b64_field)
    if isinstance(video_b64, str) and video_b64.strip():
        import base64
        output_path.write_bytes(base64.b64decode(video_b64))
        return output_path

    raise RuntimeError(
        f"Respuesta JSON sin campos de video esperados ({out_url_field}/{out_b64_field}). "
        f"Campos recibidos: {list(data.keys())[:10]}"
    )


def _heygen_headers() -> dict[str, str]:
    api_key = os.getenv("HEYGEN_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Falta HEYGEN_API_KEY en .env para usar HeyGen.")
    return {
        "X-Api-Key": api_key,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _heygen_video_generate_payload(block: dict) -> dict:
    avatar_id = os.getenv("HEYGEN_AVATAR_ID", "").strip()
    if not avatar_id:
        raise RuntimeError("Falta HEYGEN_AVATAR_ID en .env.")
    voice_id = os.getenv("HEYGEN_VOICE_ID", "").strip()
    use_input_audio = _bool_env("HEYGEN_USE_INPUT_AUDIO", default=True)
    if not use_input_audio and not voice_id:
        raise RuntimeError("Falta HEYGEN_VOICE_ID en .env (solo hace falta si HEYGEN_USE_INPUT_AUDIO=false).")

    text = (block.get("text") or "").strip()
    if not text:
        text = "Continuamos con el siguiente punto."

    avatar_style = os.getenv("HEYGEN_AVATAR_STYLE", "normal").strip() or "normal"
    width = int(os.getenv("HEYGEN_DIMENSION_WIDTH", "1280"))
    height = int(os.getenv("HEYGEN_DIMENSION_HEIGHT", "720"))

    return {
        "test": _bool_env("HEYGEN_TEST_MODE", default=False),
        "title": f"FrameFactory Block {block.get('id', '')}".strip(),
        "dimension": {"width": width, "height": height},
        "video_inputs": [
            {
                "character": {
                    "type": "avatar",
                    "avatar_id": avatar_id,
                    "avatar_style": avatar_style,
                },
                "voice": (
                    {
                        "type": "text",
                        "voice_id": voice_id,
                        "input_text": text,
                    }
                    if voice_id
                    else {"type": "text", "voice_id": "placeholder", "input_text": text}
                ),
            }
        ],
    }


def _heygen_apply_generate_extras(payload: dict) -> None:
    """
    Campos opcionales del mismo POST /v2/video/generate (doc "Generate Studio Video" / avatar video).
    Solo se agregan si están definidos en el entorno.
    """
    caption_raw = os.getenv("HEYGEN_CAPTION")
    if caption_raw is not None and caption_raw.strip() != "":
        payload["caption"] = _bool_env("HEYGEN_CAPTION", default=False)

    cb = os.getenv("HEYGEN_CALLBACK_ID", "").strip()
    if cb:
        payload["callback_id"] = cb

    ar = os.getenv("HEYGEN_ASPECT_RATIO", "").strip()
    if ar:
        payload["aspect_ratio"] = ar

    vs = os.getenv("HEYGEN_VIDEO_SETTING_JSON", "").strip()
    if vs:
        try:
            payload["video_setting"] = json.loads(vs)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"HEYGEN_VIDEO_SETTING_JSON no es JSON válido: {e}") from e


def _upload_audio_to_heygen(audio_path: Path, timeout: int) -> tuple[str | None, str | None]:
    """Sube audio a HeyGen Assets y devuelve (asset_id, url) si existen."""
    upload_url = os.getenv("HEYGEN_ASSET_UPLOAD_URL", "https://upload.heygen.com/v1/asset")
    api_key = _heygen_headers()["X-Api-Key"]
    upload_header = os.getenv("HEYGEN_UPLOAD_API_KEY_HEADER", "X-API-KEY").strip() or "X-API-KEY"
    headers = {upload_header: api_key, "Accept": "application/json"}
    content_type = mimetypes.guess_type(str(audio_path))[0] or "audio/mpeg"

    with open(audio_path, "rb") as f:
        resp = requests.post(
            upload_url,
            headers={**headers, "Content-Type": content_type},
            data=f.read(),
            timeout=timeout,
        )
    if resp.status_code >= 400:
        raise RuntimeError(f"HeyGen asset upload falló ({resp.status_code}): {resp.text[:400]}")

    raw = resp.json()
    candidates = [raw]
    if isinstance(raw.get("data"), dict):
        candidates.insert(0, raw["data"])

    asset_id = None
    asset_url = None
    for item in candidates:
        if not isinstance(item, dict):
            continue
        if not asset_id:
            for key in ("asset_id", "id"):
                val = item.get(key)
                if isinstance(val, str) and val.strip():
                    asset_id = val.strip()
                    break
        if not asset_url:
            for key in ("url", "asset_url", "audio_url"):
                val = item.get(key)
                if isinstance(val, str) and val.strip():
                    asset_url = val.strip()
                    break
    return asset_id, asset_url


def _build_heygen_voice_payload(block: dict, audio_path: Path, timeout: int) -> dict:
    """Construye la sección `voice`; prioriza usar audio real para lipsync."""
    text = (block.get("text") or "").strip() or "Continuamos con el siguiente punto."
    use_input_audio = _bool_env("HEYGEN_USE_INPUT_AUDIO", default=True)
    if not use_input_audio:
        voice_id = os.getenv("HEYGEN_VOICE_ID", "").strip()
        if not voice_id:
            raise RuntimeError("Falta HEYGEN_VOICE_ID en .env.")
        return {"type": "text", "voice_id": voice_id, "input_text": text}

    asset_id, asset_url = _upload_audio_to_heygen(audio_path=audio_path, timeout=timeout)
    audio_voice_type = os.getenv("HEYGEN_AUDIO_VOICE_TYPE", "audio").strip() or "audio"
    if asset_url:
        return {"type": audio_voice_type, "audio_url": asset_url, "input_text": text}
    if asset_id:
        return {"type": audio_voice_type, "asset_id": asset_id, "input_text": text}
    raise RuntimeError("HeyGen upload no devolvió ni asset_url ni asset_id para lipsync.")


def _extract_video_id(resp_json: dict) -> str:
    data = resp_json.get("data")
    if isinstance(data, dict):
        for key in ("video_id", "id"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    for key in ("video_id", "id"):
        value = resp_json.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    raise RuntimeError(f"No se encontró video_id en respuesta HeyGen: {str(resp_json)[:400]}")


def _render_block_heygen_with_audio(block: dict, audio_path: Path, output_path: Path) -> Path:
    """
    Variante HeyGen que usa audio pregrabado (lipsync) subiéndolo como asset.
    """
    create_url = os.getenv("HEYGEN_BASE_URL", "https://api.heygen.com").rstrip("/") + "/v2/video/generate"
    status_url = os.getenv("HEYGEN_STATUS_URL", "https://api.heygen.com/v1/video_status.get")
    timeout = int(os.getenv("HEYGEN_HTTP_TIMEOUT_SECONDS", "60"))
    poll_interval = float(os.getenv("HEYGEN_POLL_INTERVAL_SECONDS", "4"))
    max_wait = int(os.getenv("HEYGEN_MAX_WAIT_SECONDS", "600"))

    payload = _heygen_video_generate_payload(block)
    payload["video_inputs"][0]["voice"] = _build_heygen_voice_payload(
        block=block,
        audio_path=audio_path,
        timeout=timeout,
    )
    _heygen_apply_generate_extras(payload)
    headers = _heygen_headers()

    create_resp = requests.post(create_url, json=payload, headers=headers, timeout=timeout)
    if create_resp.status_code >= 400:
        raise RuntimeError(f"HeyGen create falló ({create_resp.status_code}): {create_resp.text[:400]}")
    create_json = create_resp.json()
    video_id = _extract_video_id(create_json)

    started = time.time()
    final_video_url = None
    while time.time() - started <= max_wait:
        status_resp = requests.get(
            status_url,
            params={"video_id": video_id},
            headers={"X-Api-Key": headers["X-Api-Key"], "Accept": "application/json"},
            timeout=timeout,
        )
        if status_resp.status_code >= 400:
            raise RuntimeError(f"HeyGen status falló ({status_resp.status_code}): {status_resp.text[:300]}")
        status_json = status_resp.json()
        data = status_json.get("data") or {}
        status = str(data.get("status") or "").lower()
        if status == "completed":
            final_video_url = data.get("video_url")
            if not final_video_url:
                raise RuntimeError("HeyGen completó pero no devolvió video_url.")
            break
        if status == "failed":
            err = data.get("error")
            raise RuntimeError(f"HeyGen marcó failed: {err}")
        time.sleep(poll_interval)

    if not final_video_url:
        raise RuntimeError(f"HeyGen no completó dentro del timeout ({max_wait}s) para video_id={video_id}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    dl = requests.get(final_video_url, timeout=timeout)
    if dl.status_code >= 400:
        raise RuntimeError(f"No se pudo descargar video de HeyGen ({dl.status_code}).")
    output_path.write_bytes(dl.content)
    return output_path


def _render_block_ffmpeg(block: dict, audio_path: Path, character_image: Path, output_path: Path) -> Path:
    """
    Genera un clip mp4 reproducible:
    - loop de imagen de personaje
    - mezcla con audio
    - corta al más corto (-shortest)
    """
    if not shutil.which("ffmpeg"):
        raise RuntimeError("FFmpeg no está instalado o no está en PATH.")
    if not character_image.exists():
        raise FileNotFoundError(f"No existe imagen de personaje: {character_image}")
    if not audio_path.exists():
        raise FileNotFoundError(f"No existe audio para bloque {block.get('id')}: {audio_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    text = (block.get("text") or "").strip()
    words = len(text.split()) if text else 8
    # Duración acotada por bloque para MVP (render rápido y estable).
    clip_seconds = max(2, min(6, int(round(words / 2.5))))

    fps = 24
    motion = str(block.get("motion") or "static").strip().lower()
    if motion not in ("static", "slow_push"):
        motion = "static"
    tin = str(block.get("transition_in") or "none").strip().lower()
    tout = str(block.get("transition_out") or "none").strip().lower()
    if tin not in ("none", "fade"):
        tin = "none"
    if tout not in ("none", "fade"):
        tout = "none"

    vf_parts: list[str] = []
    if motion == "slow_push":
        vf_parts.append(
            "scale=iw*2:ih*2,"
            f"zoompan=z='min(zoom+0.0014,1.22)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1280x720:"
            f"fps={fps}"
        )
    else:
        vf_parts.append(
            "scale=1280:720:force_original_aspect_ratio=decrease,"
            "pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=black"
        )
    if tin == "fade":
        vf_parts.append("fade=t=in:st=0:d=0.22")
    if tout == "fade":
        fo = max(0.0, clip_seconds - 0.26)
        vf_parts.append(f"fade=t=out:st={fo:.2f}:d=0.24")
    vf = ",".join(vf_parts) if vf_parts else None

    def _build_cmd(vf_chain: str | None) -> list[str]:
        c = [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            str(character_image.resolve()),
            "-i",
            str(audio_path.resolve()),
        ]
        if vf_chain:
            c.extend(["-vf", vf_chain])
        c.extend(
            [
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-r",
                str(fps),
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-t",
                str(clip_seconds),
                "-shortest",
                str(output_path.resolve()),
            ]
        )
        return c

    cmd = _build_cmd(vf)
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError:
        # Fallback estable si zoompan u otro filtro no es compatible en esta build de FFmpeg.
        simple = (
            "scale=1280:720:force_original_aspect_ratio=decrease,"
            "pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=black"
        )
        if tin == "fade":
            simple += ",fade=t=in:st=0:d=0.22"
        if tout == "fade":
            fo = max(0.0, clip_seconds - 0.26)
            simple += f",fade=t=out:st={fo:.2f}:d=0.24"
        subprocess.run(_build_cmd(simple), check=True, capture_output=True, text=True)
    return output_path


def render_block(block: dict, audio_path: Path, character_image: Path, output_path: Path) -> Path:
    """
    Render de bloque con estrategia configurable:
    - CHARACTER_ANIMATOR_PROVIDER=external -> API externa (avatar hablante)
    - CHARACTER_ANIMATOR_PROVIDER=heygen -> HeyGen API (avatar + lipsync con audio)
    - cualquier otro valor -> fallback FFmpeg imagen fija
    """
    provider = os.getenv("CHARACTER_ANIMATOR_PROVIDER", "ffmpeg_static").strip().lower()
    if provider == "heygen":
        try:
            return _render_block_heygen_with_audio(
                block=block,
                audio_path=audio_path,
                output_path=output_path,
            )
        except Exception as e:
            print(f"⚠️ HeyGen falló: {e}. Usando fallback FFmpeg estático.")
    if provider == "external":
        try:
            return _render_block_external_api(
                block=block,
                audio_path=audio_path,
                character_image=character_image,
                output_path=output_path,
            )
        except Exception as e:
            print(f"⚠️ API externa de animación falló: {e}. Usando fallback FFmpeg estático.")
    return _render_block_ffmpeg(
        block=block,
        audio_path=audio_path,
        character_image=character_image,
        output_path=output_path,
    )
