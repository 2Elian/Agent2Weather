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