<div align="center"> 

# A2W(Agent-to-Weather): 以宜春市为例 重构气象服务材料协作Agent

</div>

![A2W-Framework](/docs/a2w-framework.png "Agent-to-Weather")

## 功能特性

- 检索召回写作模板 --> 内嵌badcase收集 与Embedding模型微调接口
- NL2SQL能力 --> 无痛接入气象服务材料写作中 --> 进一步提供与数据库交互聊天的NL2SQL能力与badcase数据训练接口
- 基于LangGraph重构整个项目
- 更完整的FastAPI后端实现
- embedding检索采用milvus
- 整个流程 采用TypeState进行管理 方便前端调用

---

## 部署与启动教程

### 1. 部署

如若是第一次在服务器上部署，需要此步骤，如果已部署过了则跳过此步骤。

```bash
step1: 下载大模型到本地
URL: https://www.modelscope.cn/models/Qwen/Qwen3-30B-A3B-Instruct-2507
把模型权重下载到./ckpt/qwen3文件夹

step3: 开始部署
docker-compose up -d

# 查看日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f a2w-app
docker-compose logs -f vllm

# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 停止并删除所有数据
docker-compose down -v

# 重新构建应用镜像
docker-compose build a2w-app

# 重启特定服务
docker-compose restart a2w-app

# 查看服务状态
docker-compose ps

# 进入容器
docker-compose exec a2w-app bash
docker-compose exec vllm bash

# 查看GPU使用情况
docker-compose exec vllm nvidia-smi
``