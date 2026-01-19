#!/bin/bash

source /opt/conda/etc/profile.d/conda.sh
conda activate agent

echo "Initializing database..."
/app/init-sqlserver.sh

echo "Waiting for vLLM service to be ready..."
这里我需要后台启动lmdeploy serve api_server 本地路径：G:\项目成果打包\气象局服务材料写作系统\宜春\RAG\Weather-Agent-YiChun\ckpt\qwen3 --server-port 23333 --model-name qwen30b --api-keys NuistMathAutoModelForCausalLM
我需要等待这个服务启动完成后，通过健康检查，才能开始下面的操作


echo "Starting A2W application on port ${APP_PORT}..."
cd /app
exec python -m a2w.api.main