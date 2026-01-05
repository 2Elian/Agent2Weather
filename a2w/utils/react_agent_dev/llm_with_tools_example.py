#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM with Tools Example
展示如何让LLM知道有哪些工具可用
"""

import json
from typing import Dict, List, Any, Type
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import BaseTool
from langchain_core.pydantic_v1 import BaseModel, Field

# 导入我们之前创建的数据库工具
from db_function_call import PrecipitationStatsTool, TemperatureStatsTool, DBToolFactory
from db_connector import SQLServerConnector


# 定义工具的输入模型
class PrecipitationStatsInput(BaseModel):
    start_date: str = Field(description="开始日期 (YYYY-MM-DD)")
    end_date: str = Field(description="结束日期 (YYYY-MM-DD)")
    cities: List[str] = Field(description="城市列表")
    aggregation: str = Field(default="mean_vs_climatology", description="聚合方式")


class TemperatureStatsInput(BaseModel):
    start_date: str = Field(description="开始日期 (YYYY-MM-DD)")
    end_date: str = Field(description="结束日期 (YYYY-MM-DD)")
    cities: List[str] = Field(description="城市列表")


# 创建包装器工具类，使它们与LangChain Agents兼容
class PrecipitationStatsAgentTool(BaseTool):
    name = "query_precipitation_stats"
    description = "查询指定时间段和地区的降水统计信息，包括平均降水量、与常年对比等"
    args_schema: Type[BaseModel] = PrecipitationStatsInput
    
    def __init__(self, db_tool):
        super().__init__()
        self.db_tool = db_tool
    
    def _run(self, start_date: str, end_date: str, cities: List[str], aggregation: str = "mean_vs_climatology") -> Dict[str, Any]:
        return self.db_tool._run(start_date=start_date, end_date=end_date, cities=cities, aggregation=aggregation)
    
    async def _arun(self, start_date: str, end_date: str, cities: List[str], aggregation: str = "mean_vs_climatology") -> Dict[str, Any]:
        return await self.db_tool._arun(start_date=start_date, end_date=end_date, cities=cities, aggregation=aggregation)


class TemperatureStatsAgentTool(BaseTool):
    name = "query_temperature_stats"
    description = "查询指定时间段和地区的温度统计信息，包括平均温度、最高温度、最低温度等"
    args_schema: Type[BaseModel] = TemperatureStatsInput
    
    def __init__(self, db_tool):
        super().__init__()
        self.db_tool = db_tool
    
    def _run(self, start_date: str, end_date: str, cities: List[str]) -> Dict[str, Any]:
        return self.db_tool._run(start_date=start_date, end_date=end_date, cities=cities)
    
    async def _arun(self, start_date: str, end_date: str, cities: List[str]) -> Dict[str, Any]:
        return await self.db_tool._arun(start_date=start_date, end_date=end_date, cities=cities)


def create_agent_with_tools():
    """创建带有工具的Agent"""
    # 创建数据库连接器
    db_connector = SQLServerConnector(
        host="localhost",
        port="1433",
        database="weather_db",
        username="sa",
        password="your_password"
    )
    
    # 创建数据库工具
    precip_tool = PrecipitationStatsTool(db_connector=db_connector)
    temp_tool = TemperatureStatsTool(db_connector=db_connector)
    
    # 创建Agent兼容的工具
    agent_tools = [
        PrecipitationStatsAgentTool(precip_tool),
        TemperatureStatsAgentTool(temp_tool)
    ]
    
    # 初始化LLM
    llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)
    
    # 创建提示模板
    prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一个专业的气象数据分析助手。你可以使用以下工具来获取气象数据：

1. query_precipitation_stats: 查询降水统计信息
   - start_date: 开始日期 (YYYY-MM-DD)
   - end_date: 结束日期 (YYYY-MM-DD)
   - cities: 城市列表
   - aggregation: 聚合方式 (默认为 mean_vs_climatology)

2. query_temperature_stats: 查询温度统计信息
   - start_date: 开始日期 (YYYY-MM-DD)
   - end_date: 结束日期 (YYYY-MM-DD)
   - cities: 城市列表

请根据用户的问题选择合适的工具获取数据，然后给出详细的分析和回答。
"""),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ])
    
    # 创建Agent
    agent = create_tool_calling_agent(llm, agent_tools, prompt)
    
    # 创建AgentExecutor
    agent_executor = AgentExecutor(agent=agent, tools=agent_tools, verbose=True)
    
    return agent_executor


def main():
    """主函数"""
    print("=== LLM with Tools 示例 ===")
    
    # 创建Agent
    agent = create_agent_with_tools()
    
    # 示例查询
    queries = [
        "请查询2024年7月1日到7月24日期间南昌市和九江市的降水统计信息",
        "请查询2024年7月1日到7月24日期间南昌市的温度统计信息"
    ]
    
    for query in queries:
        print(f"\n用户查询: {query}")
        print("-" * 50)
        
        try:
            result = agent.invoke({"input": query})
            print("Agent回答:")
            print(result["output"])
        except Exception as e:
            print(f"执行出错: {e}")


if __name__ == "__main__":
    main()