<div align="center"> 

# A2W(Agent-to-Weather): 以宜春市为例 重构气象服务材料协作Agent

</div>

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
把模型权重下载到./ckpt/qwen3-30b-a3b文件夹

step2: 下载SQLServer 并导入数据
数据库名称：A2W_YiChun(也可以自己定义，别忘了改.env文件即可)
表名(必须一致，如若不一致，请联系我更改后端逻辑)：
小时表：automatic_station_data
日表：automatic_station_his_day_data_年份

step3: 开始部署
bash -u ./deploy.sh
```

### 2. 启动服务

```bash
step1: 确保数据库后端服务已经启动

step2: 复制.env.exmaple文件为.env，修改.env的配置

step3: 启动服务
bash -u ./start.sh
```