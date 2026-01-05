#!/bin/bash
set -e

A2W_ENV="a2w"
VLLM_ENV="vllm"
CKPT_DIR="./ckpt"
MODEL_NAME="qwen3-30b-a3b"
MODEL_API_KEY="NuistMathAutoModelForCausalLM"
MODEL_PATH="$CKPT_DIR/$MODEL_NAME"
LLM_PORT=23333
A2W_PORT=8002

echo "create python env..."
conda create -n "$A2W_ENV" python=3.10 -y
conda create -n "$VLLM_ENV" python=3.10 -y

echo "pip a2w requirement..."
conda activate "$A2W_ENV"
pip install --upgrade pip
pip install -r requirements.txt
conda deactivate

echo "pip vllm  requirement..."
conda activate "$VLLM_ENV"
pip install --upgrade pip
pip install -r vllm_requirements.txt
conda deactivate
