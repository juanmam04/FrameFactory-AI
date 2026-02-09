"""Tests de integración con ComfyUI real. Se saltan si ComfyUI no está disponible."""
import os
from pathlib import Path

import pytest

from src import image_generator as ig


def comfyui_available() -> bool:
    """True si ComfyUI responde en COMFYUI_URL."""
    return ig._comfyui_disponible()


@pytest.mark.skipif(not comfyui_available(), reason="ComfyUI no está corriendo en COMFYUI_URL")
class TestComfyUIConnectivity:
    """Comprobaciones contra un ComfyUI real."""

    def test_queue_responde_200(self):
        import requests
        r = requests.get(
            f"{ig.COMFY_URL}/queue",
            timeout=ig._comfy_timeout_connect(),
            verify=ig.COMFY_VERIFY_SSL,
        )
        assert r.status_code == 200

    def test_object_info_devuelve_checkpoints(self):
        import requests
        r = requests.get(
            f"{ig.COMFY_URL}/object_info",
            timeout=ig._comfy_timeout_connect(),
            verify=ig.COMFY_VERIFY_SSL,
        )
        assert r.status_code == 200
        data = r.json()
        assert "CheckpointLoaderSimple" in data
        required = (data.get("CheckpointLoaderSimple") or {}).get("input", {}).get("required", {})
        ckpt = required.get("ckpt_name")
        assert ckpt is not None and isinstance(ckpt, list), "ComfyUI debe listar al menos un checkpoint"


@pytest.mark.skipif(not comfyui_available(), reason="ComfyUI no está corriendo en COMFYUI_URL")
@pytest.mark.timeout(300)  # hasta 5 min si ComfyUI/GPU es lento
class TestComfyUIGenerarUnaImagen:
    """Genera una imagen real con ComfyUI (lento, requiere GPU/servidor)."""

    def test_generar_una_imagen_y_guardar(self, tmp_path):
        carpeta = tmp_path / "test_escenas"
        carpeta.mkdir(parents=True, exist_ok=True)
        path = ig._generar_imagen_comfyui(
            "A simple red circle on white background, minimal art",
            "blurry, text",
            carpeta,
            escena_num=1,
            width=512,
            height=512,
            timeout_post=ig._comfy_timeout_post(),
            timeout_poll=ig._comfy_timeout_poll(),
        )
        assert path is not None
        assert path.exists()
        assert path.suffix == ".png"
        assert path.stat().st_size > 100
        # Verificación mínima de PNG
        with open(path, "rb") as f:
            header = f.read(8)
        assert header.startswith(b"\x89PNG")
