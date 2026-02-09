"""Configuración compartida de pytest y fixtures."""
import os
import sys
from pathlib import Path

# Asegurar que el proyecto raíz está en el path para importar src
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def pytest_configure(config):
    """Cargar .env del proyecto en tests para que las variables existan."""
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")


# Respuesta típica de ComfyUI /object_info para CheckpointLoaderSimple (fragmento)
OBJECT_INFO_CHECKPOINT = {
    "CheckpointLoaderSimple": {
        "input": {
            "required": {
                "ckpt_name": [["v1-5-pruned-emaonly.safetensors"], ["otro.safetensors"]]
            }
        }
    }
}

# Respuesta exitosa de ComfyUI POST /prompt
PROMPT_RESPONSE_OK = {"prompt_id": "abc-123", "number": 1}

# Respuesta de GET /history cuando el job terminó
def make_history_with_image(prompt_id: str, filename: str = "api_gen_00001_.png"):
    return {
        prompt_id: {
            "outputs": {
                "9": {
                    "images": [
                        {"filename": filename, "subfolder": "", "type": "output"}
                    ]
                }
            }
        }
    }
