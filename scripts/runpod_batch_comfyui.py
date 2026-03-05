#!/usr/bin/env python3
"""
Genera N imágenes con ComfyUI (workflow con LoRA stickman).
Lee una lista de prompts (uno por línea) y guarda 0001.png, 0002.png, ...
Uso:
  python scripts/runpod_batch_comfyui.py prompts.txt [--output dir] [--url COMFYUI_URL]
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path

import requests

# Raíz del proyecto
REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_PATH = REPO_ROOT / "workflows" / "comfyui_stickman_lora_720p.json"


def load_workflow_template(path: Path | None = None) -> dict:
    path = path or WORKFLOW_PATH
    if not path.exists():
        raise FileNotFoundError(f"Workflow no encontrado: {path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_default_negative() -> str:
    config_path = REPO_ROOT / "config" / "prompt_stickman_lora.yaml"
    if config_path.exists():
        import yaml
        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            if isinstance(data.get("negative_prompt"), str):
                return data["negative_prompt"]
    return "3D, anime, realistic, text, watermark, blurry, deformed, extra limbs"


def comfy_post_prompt(base_url: str, workflow: dict, verify_ssl: bool = True) -> str:
    r = requests.post(
        f"{base_url.rstrip('/')}/prompt",
        json={"prompt": workflow},
        timeout=120,
        verify=verify_ssl,
    )
    if r.status_code != 200:
        raise RuntimeError(f"ComfyUI POST {r.status_code}: {r.text[:500]}")
    return r.json()["prompt_id"]


def comfy_wait_and_get_outputs(base_url: str, prompt_id: str, verify_ssl: bool = True) -> list[dict]:
    url = f"{base_url.rstrip('/')}/history/{prompt_id}"
    for _ in range(300):
        r = requests.get(url, timeout=30, verify=verify_ssl)
        if r.status_code != 200:
            time.sleep(2)
            continue
        data = r.json()
        if prompt_id not in data:
            time.sleep(2)
            continue
        outputs = data[prompt_id].get("outputs", {})
        # SaveImage suele estar en el nodo "9"
        for node_id, out in outputs.items():
            if "images" in out and out["images"]:
                return out["images"]
        time.sleep(2)
    raise TimeoutError(f"ComfyUI no devolvió imágenes para {prompt_id}")


def comfy_download_image(base_url: str, filename: str, subfolder: str, verify_ssl: bool = True) -> bytes:
    params = {"filename": filename}
    if subfolder:
        params["subfolder"] = subfolder
    r = requests.get(
        f"{base_url.rstrip('/')}/view",
        params=params,
        timeout=60,
        verify=verify_ssl,
    )
    if r.status_code != 200:
        raise RuntimeError(f"ComfyUI view {r.status_code}")
    return r.content


def generate_one(
    base_url: str,
    workflow: dict,
    positive: str,
    negative: str,
    seed: int | None,
    verify_ssl: bool,
) -> bytes:
    w = json.loads(json.dumps(workflow))
    w["4"]["inputs"]["text"] = positive
    w["5"]["inputs"]["text"] = negative
    w["7"]["inputs"]["seed"] = seed if seed is not None else random.randint(0, 2**31 - 1)
    prompt_id = comfy_post_prompt(base_url, w, verify_ssl)
    images = comfy_wait_and_get_outputs(base_url, prompt_id, verify_ssl)
    if not images:
        raise RuntimeError("Sin imágenes en la respuesta")
    img = images[0]
    return comfy_download_image(
        base_url,
        img["filename"],
        img.get("subfolder", ""),
        verify_ssl,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch ComfyUI: prompts.txt -> 0001.png, 0002.png...")
    parser.add_argument("prompts_file", type=Path, help="Archivo con un prompt por línea")
    parser.add_argument("--output", "-o", type=Path, default=REPO_ROOT / "output" / "batch_frames", help="Carpeta de salida")
    parser.add_argument("--url", default=os.getenv("COMFYUI_URL", "http://127.0.0.1:8188"), help="URL ComfyUI")
    parser.add_argument("--negative", type=Path, default=None, help="Archivo con un solo negative prompt (opcional)")
    parser.add_argument("--no-verify-ssl", action="store_true", help="Para RunPod proxy HTTPS")
    parser.add_argument("--seed", type=int, default=None, help="Seed fija (opcional)")
    args = parser.parse_args()

    if not args.prompts_file.exists():
        print(f"Error: no existe {args.prompts_file}", file=sys.stderr)
        return 1

    with open(args.prompts_file, encoding="utf-8") as f:
        lines = [ln.strip() for ln in f if ln.strip()]

    negative = get_default_negative()
    if args.negative and args.negative.exists():
        negative = args.negative.read_text(encoding="utf-8").strip()

    workflow = load_workflow_template()
    args.output.mkdir(parents=True, exist_ok=True)
    verify = not args.no_verify_ssl

    print(f"ComfyUI: {args.url} | prompts: {len(lines)} | salida: {args.output}")
    for i, positive in enumerate(lines, start=1):
        out_name = f"{i:04d}.png"
        out_path = args.output / out_name
        seed = (args.seed + i) if args.seed is not None else None
        try:
            raw = generate_one(args.url, workflow, positive, negative, seed, verify)
            out_path.write_bytes(raw)
            print(f"  {i}/{len(lines)} -> {out_name}")
        except Exception as e:
            print(f"  {i}/{len(lines)} ERROR: {e}", file=sys.stderr)
            return 2
    print("Listo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
