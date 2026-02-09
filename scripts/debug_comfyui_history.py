#!/usr/bin/env python3
"""Diagnóstico: envía un prompt a ComfyUI y muestra la estructura de GET /history.
Uso: python scripts/debug_comfyui_history.py
"""
import json
import os
import sys
import time
from pathlib import Path

# raíz del proyecto
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")
import requests

COMFY_URL = (os.getenv("COMFYUI_URL") or "http://127.0.0.1:8188").rstrip("/")
TIMEOUT = 10

def main():
    print(f"ComfyUI URL: {COMFY_URL}")
    # Workflow mínimo (mismo que image_generator)
    workflow = {
        "3": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": os.getenv("COMFYUI_CHECKPOINT") or "v1-5-pruned-emaonly.safetensors"}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": "a red circle", "clip": ["3", 1]}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"text": "blurry", "clip": ["3", 1]}},
        "6": {"class_type": "EmptyLatentImage", "inputs": {"width": 512, "height": 512, "batch_size": 1}},
        "7": {"class_type": "KSampler", "inputs": {"model": ["3", 0], "positive": ["4", 0], "negative": ["5", 0], "latent_image": ["6", 0], "seed": 42, "steps": 10, "cfg": 8, "sampler_name": "euler", "scheduler": "normal", "denoise": 1.0}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["3", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "debug", "images": ["8", 0]}},
    }
    print("Enviando POST /prompt ...")
    try:
        r = requests.post(f"{COMFY_URL}/prompt", json={"prompt": workflow}, timeout=TIMEOUT)
        print(f"  Status: {r.status_code}")
        if r.status_code != 200:
            print(r.text[:500])
            return
        data = r.json()
        prompt_id = data.get("prompt_id")
        print(f"  prompt_id: {prompt_id!r} (type: {type(prompt_id).__name__})")
    except Exception as e:
        print(f"  Error: {e}")
        return

    wait = 60
    print(f"Esperando {wait} s y luego GET /history (el job puede estar en cola o ejecutándose) ...")
    time.sleep(wait)
    try:
        # Usar GET /history/{prompt_id} como hace la app
        h = requests.get(f"{COMFY_URL}/history/{prompt_id}", timeout=TIMEOUT).json()
    except Exception as e:
        print(f"  Error: {e}")
        return

    print(f"GET /history/{{prompt_id}}: ¿encontrado? {bool(h and prompt_id in h)}")
    if prompt_id in h:
        entry = h[prompt_id]
        print(f"Claves del entry: {list(entry.keys())!r}")
        print(f"  status: {entry.get('status')}")
        outputs = entry.get("outputs", {})
        print(f"  outputs keys: {list(outputs.keys())!r}")
        for nid, node_data in (outputs or {}).items():
            imgs = (node_data or {}).get("images", [])
            print(f"  node {nid!r}: images = {imgs[:1] if imgs else []}")
    else:
        # Mostrar una entrada cualquiera de GET /history completo para comparar
        try:
            full = requests.get(f"{COMFY_URL}/history", timeout=TIMEOUT).json()
            print(f"Claves en GET /history (completo): {list(full.keys())[:5]!r}")
            q = requests.get(f"{COMFY_URL}/queue", timeout=TIMEOUT).json()
            print(f"Queue: running={len(q.get('queue_running', []))}, pending={len(q.get('queue_pending', []))}")
        except Exception as e:
            print(f"  (no se pudo leer queue/history: {e})")

if __name__ == "__main__":
    main()
