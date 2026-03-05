#!/usr/bin/env bash
# RunPod: redirigir tmp y cachés a /workspace para evitar "No space left on device"
# Uso: source scripts/runpod_workspace_env.sh
# O añadir a ~/.bashrc: source /workspace/FrameFactory-AI/scripts/runpod_workspace_env.sh

mkdir -p /workspace/tmp /workspace/.cache/pip /workspace/.cache/huggingface 2>/dev/null || true

export TMPDIR=/workspace/tmp
export TEMP=/workspace/tmp
export TMP=/workspace/tmp
export PIP_CACHE_DIR=/workspace/.cache/pip
export HF_HOME=/workspace/.cache/huggingface
export TRANSFORMERS_CACHE=/workspace/.cache/huggingface
export HUGGINGFACE_HUB_CACHE=/workspace/.cache/huggingface

echo "[runpod_workspace_env] TMPDIR and caches set to /workspace"
