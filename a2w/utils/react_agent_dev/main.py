#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main Entry Point
天气报告生成Agent主程序
"""

import json
from typing import Dict, List, Any

# 导入各个模块
from weather_agent import WeatherReportAgent
from query_decomposer import QueryDecomposer
from data_planner import DataPlanner
from tool_executor import ToolExecutor
from recovery_mechanism import RecoveryMechanism
from template_generator import TemplateGenerator
from langgraph_workflow import WeatherReportWorkflow
from db_connector import SQLServerConnector
from db_function_call import DBToolFactory


# 示例工具函数
def query_precipitation_stats(start_date: str, end_date: str, cities: List[str], aggregation: str) -> Dict[str, Any]:
    """示例降水统计查询工具"""
    print(f"调用工具: query_precipitation_stats, 参数: start_date={start_date}, end_date={end_date}, cities={cities}, aggregation={aggregation}")
    # 在实际应用中，这里会调用真实的数据库工具
    # db_connector = SQLServerConnector(host="localhost", port="1433", database="weather_db", username="sa", password="your_password")
    # tool = DBToolFactory.create_tool("query_precipitation_stats", db_connector)
    # result = tool._run(start_date=start_date, end_date=end_date, cities=cities, aggregation=aggregation)
    # return result.get("data", {})
    return {
        "avg_precip": 47.0,
        "climatology_diff": 7.0,
        "rank_since_1961": 12,
        "unit": "毫米"
    }


def query_precipitation_by_county(start_date: str, end_date: str, cities: List[str]) -> Dict[str, Any]:
    """示例按县查询降水工具"""
    print(f"调用工具: query_precipitation_by_county, 参数: start_date={start_date}, end_date={end_date}, cities={cities}")
    return {
        "counties": [
            {"name": "靖安县", "precip": 100.1, "extreme_type": "最多"},
            {"name": "樟树市", "precip": 11.7, "extreme_type": "最少"}
        ]
    }


def query_temperature_stats(start_date: str, end_date: str, cities: List[str]) -> Dict[str, Any]:
    """示例温度统计查询工具"""
    print(f"调用工具: query_temperature_stats, 参数: start_date={start_date}, end_date={end_date}, cities={cities}")
    return {
        "avg_temp": 31.1,
        "diff": 2.4,
        "is_historical_extreme": True,
        "unit": "℃"
    }


def query_heatwave_events(start_date: str, end_date: str, cities: List[str]) -> Dict[str, Any]:
    """示例热浪事件查询工具"""
    print(f"调用工具: query_heatwave_events, 参数: start_date={start_date}, end_date={end_date}, cities={cities}")
    return {
        "events": [
            {
                "start_date": "2024-07-22",
                "duration": 3,
                "counties": ["南昌县", "新建区", "安义县", "进贤县", "湾里区", "青山湖区"],
                "intensity": "轻度"
            }
        ]
    }


def query_general_weather_stats(start_date: str, end_date: str, cities: List[str]) -> Dict[str, Any]:
    """示例通用天气统计查询工具"""
    print(f"调用工具: query_general_weather_stats, 参数: start_date={start_date}, end_date={end_date}, cities={cities}")
    return {
        "start_date": start_date,
        "end_date": end_date,
        "city_count": len(cities),
        "data_completeness": 0.95
    }


def query_temperature_by_county(start_date: str, end_date: str, cities: List[str]) -> Dict[str, Any]:
    """示例按县查询温度工具"""
    print(f"调用工具: query_temperature_by_county, 参数: start_date={start_date}, end_date={end_date}, cities={cities}")
    return {
        "counties": [
            {"name": "丰城市", "temp": 32.1, "extreme_type": "最高"},
            {"name": "铜鼓县", "temp": 29.6, "extreme_type": "最低"}
        ]
    }


def main():
    """主函数"""
    print("=== 天气报告生成Agent ===")
    
    # 注册工具函数
    tool_registry = {
        "query_precipitation_stats": query_precipitation_stats,
        "query_precipitation_by_county": query_precipitation_by_county,
        "query_temperature_stats": query_temperature_stats,
        "query_heatwave_events": query_heatwave_events,
        "query_general_weather_stats": query_general_weather_stats,
        "query_temperature_by_county": query_temperature_by_county
    }
    
    # 方法1: 使用完整的LangGraph工作流
    print("\n方法1: 使用LangGraph工作流")
    print("-" * 30)
    
    # 创建工作流
    workflow = WeatherReportWorkflow(tool_registry, "gpt-3.5-turbo")
    
    # 示例用户查询
    user_query = {
        "start_date": "2024-07-01",
        "end_date": "2024-07-24",
        "cities": ["南昌市", "九江市", "景德镇市"],
        "weather_types": ["降雨", "高温"]
    }
    
    # 示例模板
    template = """7 月 1 日～ 24 日，全市平均降雨量为 {avg_precip} 毫米，较常年同 期 偏少 {climatology_diff} 成 ，为 1961 年以来历史同期 第 {rank_since_1961} 少位。县级降雨量极值。全市日平均气 温为 {avg_temp} ℃，较常年同期 偏高 {diff} ℃，破 1961 年以来 历史极值。县级气温极值。7 月 22 日开 始，我市出现了高温热浪过程。"""
    
    # 运行工作流
    print("正在生成天气报告...")
    report, final_state = workflow.run(user_query, template)
    
    print("\n生成的天气报告:")
    print("=" * 50)
    print(report)
    print("=" * 50)
    
    # 显示最终状态信息
    print("\n工作流最终状态:")
    print(f"当前状态: {final_state.current_state.value}")
    print(f"重试次数: {final_state.retry_count}")
    
    # 方法2: 使用单一Agent类
    print("\n\n方法2: 使用单一Agent类")
    print("-" * 30)
    
    # 创建Agent
    agent = WeatherReportAgent("gpt-3.5-turbo")
    
    # 运行Agent
    print("正在生成天气报告...")
    report2 = agent.run(user_query, template)
    
    print("\n生成的天气报告:")
    print("=" * 50)
    print(report2)
    print("=" * 50)


if __name__ == "__main__":
    main()