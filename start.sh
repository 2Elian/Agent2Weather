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

echo "启动 vllm 模型服务..."
conda activate "$VLLM_ENV"
CUDA_VISIBLE_DEVICES=0 nohup lmdeploy serve api_server "$MODEL_PATH" \
    --server-port "$LLM_PORT" \
    --tp 1 \
    --model-name "$MODEL_NAME" \
    --api-keys  "$MODEL_API_KEY"\
    > "./lmdeploy.log" 2>&1 &
echo "vllm启动成功 --> 日志位置: ./lmdeploy.log"
conda deactivate

echo "启动 API服务..."
conda activate "$A2W_ENV"
python -m a2w.api.main
