"""Tests unitarios para generación de imágenes con ComfyUI (con mocks, sin servidor real)."""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Importar después de posible path fix en conftest
from src import image_generator as ig


class TestWorkflowComfyUI:
    """Estructura y contenido del workflow que se envía a ComfyUI."""

    @pytest.fixture(autouse=True)
    def mock_get_checkpoint(self):
        """Evitar HTTP real en _get_checkpoint."""
        with patch.object(ig, "_get_checkpoint", return_value="test_checkpoint.safetensors"):
            yield

    def test_workflow_tiene_nodos_requeridos(self):
        w = ig._workflow_comfyui("un prompt", "negative", 512, 512)
        assert "3" in w  # CheckpointLoaderSimple
        assert "4" in w  # CLIPTextEncode positive
        assert "5" in w  # CLIPTextEncode negative
        assert "6" in w  # EmptyLatentImage
        assert "7" in w  # KSampler
        assert "8" in w  # VAEDecode
        assert "9" in w  # SaveImage

    def test_workflow_checkpoint_loader(self):
        w = ig._workflow_comfyui("p", "n", 256, 256)
        assert w["3"]["class_type"] == "CheckpointLoaderSimple"
        assert w["3"]["inputs"]["ckpt_name"] == "test_checkpoint.safetensors"

    def test_workflow_clip_text_encode(self):
        w = ig._workflow_comfyui("mi texto", "neg", 512, 512)
        assert w["4"]["inputs"]["text"] == "mi texto"
        assert w["5"]["inputs"]["text"] == "neg"
        assert w["4"]["inputs"]["clip"] == ["3", 1]

    def test_workflow_dimensiones_multiplo_8(self):
        w = ig._workflow_comfyui("p", "n", 100, 100)
        assert w["6"]["inputs"]["width"] == 96   # 100 -> 96
        assert w["6"]["inputs"]["height"] == 96

    def test_workflow_dimensiones_minimo_64(self):
        w = ig._workflow_comfyui("p", "n", 32, 32)
        assert w["6"]["inputs"]["width"] == 64
        assert w["6"]["inputs"]["height"] == 64

    def test_workflow_ksampler_tiene_denoise(self):
        w = ig._workflow_comfyui("p", "n", 512, 512)
        assert w["7"]["inputs"].get("denoise") == 1.0

    def test_workflow_serializable_json(self):
        w = ig._workflow_comfyui("prompt", "neg", 1024, 576)
        # No debe fallar y debe ser válido para POST
        payload = {"prompt": w}
        json.dumps(payload)


class TestComfyUIDisponible:
    """Detección de disponibilidad de ComfyUI."""

    def test_disponible_cuando_queue_200(self):
        with patch("src.image_generator.requests.get") as mget:
            mget.return_value.status_code = 200
            mget.return_value.raise_for_status = MagicMock()
            assert ig._comfyui_disponible() is True
            mget.assert_called_once()
            assert "/queue" in mget.call_args[0][0]

    def test_no_disponible_cuando_timeout(self):
        import requests
        with patch("src.image_generator.requests.get") as mget:
            mget.side_effect = requests.Timeout()
            assert ig._comfyui_disponible() is False

    def test_no_disponible_cuando_500(self):
        with patch("src.image_generator.requests.get") as mget:
            mget.return_value.status_code = 500
            assert ig._comfyui_disponible() is False


class TestComfyUIEsRemoto:
    """Detección de ComfyUI remoto vs local."""

    def test_local_con_127(self):
        with patch.dict("os.environ", {"COMFYUI_URL": "http://127.0.0.1:8188"}, clear=False):
            # Recargar lógica: el módulo ya tiene _is_remote_comfy que lee os.getenv
            assert ig._is_remote_comfy() is False

    def test_remoto_con_runpod(self):
        with patch.dict("os.environ", {"COMFYUI_URL": "https://xyz-8188.proxy.runpod.net"}, clear=False):
            assert ig._is_remote_comfy() is True


class TestGetCheckpoint:
    """Resolución del checkpoint (env vs object_info)."""

    @pytest.fixture(autouse=True)
    def reset_checkpoint_cache(self):
        ig._resolved_checkpoint = None
        yield
        ig._resolved_checkpoint = None

    def test_usa_env_si_esta_definido(self):
        with patch.dict("os.environ", {"COMFYUI_CHECKPOINT": "mi_modelo.safetensors"}, clear=False):
            with patch("src.image_generator.requests.get"):
                ckpt = ig._get_checkpoint()
            assert ckpt == "mi_modelo.safetensors"

    def test_usa_object_info_si_env_vacio(self):
        with patch.dict("os.environ", {"COMFYUI_CHECKPOINT": "", "COMFYUI_URL": "http://127.0.0.1:8188"}, clear=False):
            with patch("src.image_generator.requests.get") as mget:
                mget.return_value.status_code = 200
                mget.return_value.json.return_value = {
                    "CheckpointLoaderSimple": {
                        "input": {"required": {"ckpt_name": [["primer_checkpoint.safetensors"]]}}
                    }
                }
                ckpt = ig._get_checkpoint()
            assert ckpt == "primer_checkpoint.safetensors"


class TestGenerarImagenComfyUI:
    """Flujo de _generar_imagen_comfyui con mocks."""

    @pytest.fixture
    def tmp_carpeta(self, tmp_path):
        return tmp_path / "imagenes"

    @pytest.fixture(autouse=True)
    def mock_checkpoint_here(self):
        with patch.object(ig, "_get_checkpoint", return_value="test.safetensors"):
            yield

    def test_400_devuelve_error_con_detalle(self, tmp_carpeta):
        with patch("src.image_generator.requests.post") as mpost:
            mpost.return_value.status_code = 400
            mpost.return_value.json.return_value = {
                "error": {
                    "message": "Prompt outputs failed validation",
                    "extra_info": {"node_errors": {"3": ["Value not in list: ckpt_name"]}},
                }
            }
            mpost.return_value.text = ""
            with pytest.raises(RuntimeError) as exc:
                ig._generar_imagen_comfyui("p", "n", tmp_carpeta, 1, 512, 512)
            assert "400" in str(exc.value)
            assert "node_errors" in str(exc.value) or "Value not in list" in str(exc.value)

    def test_exito_guarda_imagen(self, tmp_carpeta):
        prompt_id = "test-id-123"

        def side_get(url, **kwargs):
            if "history" in url:
                r = MagicMock()
                r.status_code = 200
                r.json.return_value = {
                    prompt_id: {
                        "outputs": {
                            "9": {
                                "images": [{"filename": "api_gen_00001_.png", "subfolder": "", "type": "output"}]
                            }
                        }
                    }
                }
                return r
            if "view" in url:
                r = MagicMock()
                r.status_code = 200
                r.content = b"\x89PNG\r\n\x1a\n"  # PNG mínimo
                return r
            return MagicMock(status_code=404)

        with patch("src.image_generator.requests.post") as mpost:
            mpost.return_value.status_code = 200
            mpost.return_value.json.return_value = {"prompt_id": prompt_id}
            mpost.return_value.raise_for_status = MagicMock()
            with patch("src.image_generator.requests.get") as mget:
                mget.side_effect = side_get
                with patch("src.image_generator.time.sleep"):
                    path = ig._generar_imagen_comfyui("p", "n", tmp_carpeta, 1, 512, 512)
        assert path is not None
        assert path.exists()
        assert path.suffix == ".png"
        assert path.name == "escena_0001.png"


class TestGenerarLote:
    """generar_lote exige ComfyUI disponible."""

    def test_raise_si_comfy_no_disponible(self):
        with patch.object(ig, "_usar_replicate", return_value=False):
            with patch.object(ig, "_comfyui_disponible", return_value=False):
                with pytest.raises(RuntimeError) as exc:
                    ig.generar_lote([], subcarpeta="test")
                assert "ComfyUI" in str(exc.value)
