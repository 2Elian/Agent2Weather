#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DB Function Call Module
基于LangChain BaseTool的数据库函数调用类
"""

import asyncio
import json
from typing import Dict, List, Any, Optional, Type
from abc import ABC, abstractmethod

from langchain.tools import BaseTool
from langchain_core.pydantic_v1 import BaseModel, Field
from pydantic import BaseModel as PydanticBaseModel

from db_connector import SQLServerConnector


class DBFunctionCallInput(BaseModel):
    """数据库函数调用输入参数"""
    sql_query: str = Field(description="要执行的SQL查询语句")


class DBFunctionCall(BaseTool, ABC):
    """数据库函数调用基类"""
    
    name: str = "db_function_call"
    description: str = "执行数据库查询的通用工具"
    args_schema: Type[BaseModel] = DBFunctionCallInput
    
    def __init__(self, db_connector: SQLServerConnector, **kwargs):
        """
        初始化数据库函数调用工具
        
        Args:
            db_connector: SQL Server连接器实例
        """
        super().__init__(**kwargs)
        self.db_connector = db_connector
    
    def _run(self, sql_query: str) -> Dict[str, Any]:
        """
        同步执行数据库查询
        
        Args:
            sql_query: SQL查询语句
            
        Returns:
            查询结果
        """
        try:
            # 创建一个新的事件循环来运行异步代码
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 执行异步查询
            result = loop.run_until_complete(self._async_execute_query(sql_query))
            return result
        except Exception as e:
            return {
                "status": "error",
                "message": f"查询执行失败: {str(e)}",
                "data": None
            }
        finally:
            if 'loop' in locals():
                loop.close()
    
    async def _arun(self, sql_query: str) -> Dict[str, Any]:
        """
        异步执行数据库查询
        
        Args:
            sql_query: SQL查询语句
            
        Returns:
            查询结果
        """
        try:
            result = await self._async_execute_query(sql_query)
            return result
        except Exception as e:
            return {
                "status": "error",
                "message": f"查询执行失败: {str(e)}",
                "data": None
            }
    
    async def _async_execute_query(self, sql_query: str) -> Dict[str, Any]:
        """
        异步执行SQL查询的内部方法
        
        Args:
            sql_query: SQL查询语句
            
        Returns:
            查询结果
        """
        try:
            # 确保数据库连接已建立
            if not self.db_connector.pool:
                await self.db_connector.connect()
            
            # 执行查询
            data = await self.db_connector.execute_query(sql_query)
            
            return {
                "status": "success",
                "message": "查询执行成功",
                "data": data,
                "row_count": len(data) if data else 0
            }
        except Exception as e:
            raise Exception(f"数据库查询执行失败: {str(e)}")


# 特定的气象数据查询工具示例
class PrecipitationStatsTool(DBFunctionCall):
    """降水统计查询工具"""
    
    name: str = "query_precipitation_stats"
    description: str = "查询指定时间段和地区的降水统计信息"
    
    def _run(self, start_date: str, end_date: str, cities: List[str], aggregation: str = "mean_vs_climatology") -> Dict[str, Any]:
        """
        同步执行降水统计查询
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            cities: 城市列表
            aggregation: 聚合方式
            
        Returns:
            降水统计结果
        """
        sql_query = self._build_precipitation_sql(start_date, end_date, cities, aggregation)
        return super()._run(sql_query)
    
    async def _arun(self, start_date: str, end_date: str, cities: List[str], aggregation: str = "mean_vs_climatology") -> Dict[str, Any]:
        """
        异步执行降水统计查询
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            cities: 城市列表
            aggregation: 聚合方式
            
        Returns:
            降水统计结果
        """
        sql_query = self._build_precipitation_sql(start_date, end_date, cities, aggregation)
        return await super()._arun(sql_query)
    
    def _build_precipitation_sql(self, start_date: str, end_date: str, cities: List[str], aggregation: str) -> str:
        """
        构建降水统计SQL查询
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            cities: 城市列表
            aggregation: 聚合方式
            
        Returns:
            SQL查询语句
        """
        # 这里应该根据实际的数据库表结构调整SQL
        city_conditions = " OR ".join([f"city = '{city}'" for city in cities]) if cities else "1=1"
        
        if aggregation == "mean_vs_climatology":
            sql = f"""
            SELECT 
                AVG(precipitation) as avg_precip,
                AVG(climatology) as avg_climatology,
                AVG(precipitation) - AVG(climatology) as diff,
                COUNT(*) as days
            FROM weather_data 
            WHERE date BETWEEN '{start_date}' AND '{end_date}'
            AND ({city_conditions})
            """
        else:
            sql = f"""
            SELECT 
                SUM(precipitation) as total_precip,
                COUNT(*) as days
            FROM weather_data 
            WHERE date BETWEEN '{start_date}' AND '{end_date}'
            AND ({city_conditions})
            """
        
        return sql


class TemperatureStatsTool(DBFunctionCall):
    """温度统计查询工具"""
    
    name: str = "query_temperature_stats"
    description: str = "查询指定时间段和地区的温度统计信息"
    
    def _run(self, start_date: str, end_date: str, cities: List[str]) -> Dict[str, Any]:
        """
        同步执行温度统计查询
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            cities: 城市列表
            
        Returns:
            温度统计结果
        """
        sql_query = self._build_temperature_sql(start_date, end_date, cities)
        return super()._run(sql_query)
    
    async def _arun(self, start_date: str, end_date: str, cities: List[str]) -> Dict[str, Any]:
        """
        异步执行温度统计查询
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            cities: 城市列表
            
        Returns:
            温度统计结果
        """
        sql_query = self._build_temperature_sql(start_date, end_date, cities)
        return await super()._arun(sql_query)
    
    def _build_temperature_sql(self, start_date: str, end_date: str, cities: List[str]) -> str:
        """
        构建温度统计SQL查询
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            cities: 城市列表
            
        Returns:
            SQL查询语句
        """
        # 这里应该根据实际的数据库表结构调整SQL
        city_conditions = " OR ".join([f"city = '{city}'" for city in cities]) if cities else "1=1"
        
        sql = f"""
        SELECT 
            AVG(temperature) as avg_temp,
            MAX(temperature) as max_temp,
            MIN(temperature) as min_temp,
            AVG(temperature) - (SELECT AVG(temperature) FROM weather_data WHERE date BETWEEN DATEADD(year, -30, '{start_date}') AND DATEADD(year, -30, '{end_date}')) as diff_from_climatology
        FROM weather_data 
        WHERE date BETWEEN '{start_date}' AND '{end_date}'
        AND ({city_conditions})
        """
        
        return sql


# 工厂类用于创建各种数据库工具
class DBToolFactory:
    """数据库工具工厂类"""
    
    @staticmethod
    def create_tool(tool_name: str, db_connector: SQLServerConnector) -> DBFunctionCall:
        """
        创建指定类型的数据库工具
        
        Args:
            tool_name: 工具名称
            db_connector: 数据库连接器
            
        Returns:
            数据库工具实例
        """
        tools = {
            "query_precipitation_stats": PrecipitationStatsTool,
            "query_temperature_stats": TemperatureStatsTool,
            "db_function_call": DBFunctionCall
        }
        
        if tool_name not in tools:
            raise ValueError(f"未知的工具名称: {tool_name}")
        
        return tools[tool_name](db_connector=db_connector)


# 示例使用
if __name__ == "__main__":
    # 创建数据库连接器
    db_connector = SQLServerConnector(
        host="localhost",
        port="1433",
        database="weather_db",
        username="sa",
        password="your_password"
    )
    
    # 创建工具实例
    precipitation_tool = PrecipitationStatsTool(db_connector=db_connector)
    temperature_tool = TemperatureStatsTool(db_connector=db_connector)
    
    # 同步调用示例
    print("同步执行降水统计查询...")
    result = precipitation_tool._run(
        start_date="2024-07-01",
        end_date="2024-07-24",
        cities=["南昌市", "九江市"],
        aggregation="mean_vs_climatology"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # 异步调用示例
    async def async_example():
        print("\n异步执行温度统计查询...")
        result = await temperature_tool._arun(
            start_date="2024-07-01",
            end_date="2024-07-24",
            cities=["南昌市", "九江市"]
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # 运行异步示例
    # asyncio.run(async_example())