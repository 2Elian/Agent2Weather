#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Template-grounded, Data-driven Weather Report Generator Agent

架构组件：
1. Query Normalizer - 标准化用户查询
2. Data Planner Agent - 规划所需数据查询
3. Executor Agent - 执行数据查询工具调用
4. Data Validator/Critic - 验证数据完整性
5. Template-aware Writer Agent - 基于模板和数据生成报告
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum


class QueryStatus(Enum):
    """查询状态枚举"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    REVISED = "revised"


@dataclass
class SubQuery:
    """子查询数据类"""
    id: str
    purpose: str
    required_by_template: bool
    tool: str
    params: Dict[str, Any]
    expected_fields: List[str]


@dataclass
class QueryPlan:
    """查询计划数据类"""
    meta: Dict[str, Any]
    sub_queries: List[SubQuery]
    status: QueryStatus = QueryStatus.PENDING


@dataclass
class ValidationResult:
    """验证结果数据类"""
    status: str  # "ok" or "revise"
    issues: List[Dict[str, Any]]


class WeatherReportAgent:
    """天气报告生成Agent主类"""
    
    def __init__(self, llm_model: str = "gpt-3.5-turbo"):
        """初始化Agent"""
        self.template = None
        self.query_meta = None
        self.available_tools = {}
        self.data_results = {}
        self.llm_model = llm_model
        
    def normalize_query(self, user_query: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化用户查询
        
        Args:
            user_query: 用户原始查询
            
        Returns:
            标准化后的查询
        """
        # 实现查询标准化逻辑
        normalized = {
            "start_date": user_query.get("start_date"),
            "end_date": user_query.get("end_date"),
            "cities": user_query.get("cities", []),
            "weather_types": user_query.get("weather_types", [])
        }
        return normalized
    
    def plan_data_queries(self, query_meta: Dict[str, Any], template: str) -> QueryPlan:
        """
        根据模板和查询元数据规划数据查询
        
        Args:
            query_meta: 查询元数据
            template: 模板文本
            
        Returns:
            查询计划
        """
        # 使用DataPlanner生成查询计划
        from data_planner import DataPlanner
        # 定义可用工具
        available_tools = {
            "query_precipitation_stats": {
                "description": "查询降水统计信息",
                "parameters": {
                    "start_date": "开始日期",
                    "end_date": "结束日期",
                    "cities": "城市列表",
                    "aggregation": "聚合方式"
                }
            },
            "query_precipitation_ranking": {
                "description": "查询降水历史排名",
                "parameters": {
                    "start_date": "开始日期",
                    "end_date": "结束日期",
                    "cities": "城市列表",
                    "reference_period": "参考时期"
                }
            },
            "query_precipitation_by_county": {
                "description": "按县查询降水信息",
                "parameters": {
                    "start_date": "开始日期",
                    "end_date": "结束日期",
                    "cities": "城市列表"
                }
            },
            "query_temperature_stats": {
                "description": "查询温度统计信息",
                "parameters": {
                    "start_date": "开始日期",
                    "end_date": "结束日期",
                    "cities": "城市列表"
                }
            },
            "query_temperature_records": {
                "description": "查询气温历史记录",
                "parameters": {
                    "start_date": "开始日期",
                    "end_date": "结束日期",
                    "cities": "城市列表"
                }
            },
            "query_temperature_by_county": {
                "description": "按县查询温度信息",
                "parameters": {
                    "start_date": "开始日期",
                    "end_date": "结束日期",
                    "cities": "城市列表"
                }
            },
            "query_heatwave_events": {
                "description": "查询热浪事件",
                "parameters": {
                    "start_date": "开始日期",
                    "end_date": "结束日期",
                    "cities": "城市列表"
                }
            },
            "query_general_weather_stats": {
                "description": "查询通用天气统计",
                "parameters": {
                    "start_date": "开始日期",
                    "end_date": "结束日期",
                    "cities": "城市列表"
                }
            }
        }
        planner = DataPlanner(available_tools, self.llm_model)
        plan = planner.plan(query_meta, template)
        return plan
    
    def execute_query(self, sub_query: SubQuery) -> Dict[str, Any]:
        """
        执行单个数据查询
        
        Args:
            sub_query: 子查询对象
            
        Returns:
            查询结果
        """
        # 这里应该实际调用相应的工具函数
        # 目前我们模拟返回一些示例数据
        # 在实际应用中，这里会调用真实的工具函数
        if sub_query.tool == "query_precipitation_stats":
            return {
                "avg_precip": 47.0,
                "climatology_diff": 7.0,
                "rank_since_1961": 12
            }
        elif sub_query.tool == "query_precipitation_by_county":
            return {
                "counties": [
                    {"name": "靖安县", "precip": 100.1, "extreme_type": "最多"},
                    {"name": "樟树市", "precip": 11.7, "extreme_type": "最少"}
                ]
            }
        elif sub_query.tool == "query_temperature_stats":
            return {
                "avg_temp": 31.1,
                "diff": 2.4,
                "is_historical_extreme": True
            }
        elif sub_query.tool == "query_heatwave_events":
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
        elif sub_query.tool == "query_general_weather_stats":
            return {
                "start_date": sub_query.params.get("start_date"),
                "end_date": sub_query.params.get("end_date"),
                "city_count": len(sub_query.params.get("cities", [])),
                "data_completeness": 0.95
            }
        else:
            raise ValueError(f"未知工具: {sub_query.tool}")
    
    def validate_plan(self, plan: QueryPlan, template: str) -> ValidationResult:
        """
        验证查询计划是否完整覆盖模板需求
        
        Args:
            plan: 查询计划
            template: 模板文本
            
        Returns:
            验证结果
        """
        # 这里应该由Critic Agent检查计划是否完整
        # 目前我们简单返回OK
        return ValidationResult(status="ok", issues=[])
    
    def generate_report(self, template: str, query_meta: Dict[str, Any], 
                       data: Dict[str, Any]) -> str:
        """
        基于模板和数据生成报告
        
        Args:
            template: 模板文本
            query_meta: 查询元数据
            data: 查询结果数据
            
        Returns:
            生成的报告文本
        """
        # 这里应该使用LLM根据模板和数据生成报告
        # 目前我们简单地替换一些占位符
        report = template
        # 在实际实现中，这里会更复杂，需要根据具体数据填充模板
        return report
    
    def run(self, user_query: Dict[str, Any], template: str) -> str:
        """
        运行整个Agent流程
        
        Args:
            user_query: 用户查询
            template: 模板文本
            
        Returns:
            生成的天气报告
        """
        # 1. 标准化查询
        self.query_meta = self.normalize_query(user_query)
        
        # 2. 规划数据查询
        plan = self.plan_data_queries(self.query_meta, template)
        
        # 3. 验证计划
        validation = self.validate_plan(plan, template)
        if validation.status == "revise":
            # 需要重新规划，这里简化处理
            pass
        
        # 4. 执行查询
        self.data_results = {}
        for sub_query in plan.sub_queries:
            try:
                result = self.execute_query(sub_query)
                self.data_results[sub_query.id] = {
                    "data": result,
                    "status": "success"
                }
            except Exception as e:
                self.data_results[sub_query.id] = {
                    "error": str(e),
                    "status": "failed"
                }
        
        # 5. 生成报告
        report = self.generate_report(template, self.query_meta, self.data_results)
        return report


# 示例使用
if __name__ == "__main__":
    agent = WeatherReportAgent()
    
    # 示例用户查询
    user_query = {
        "start_date": "2024-07-01",
        "end_date": "2024-07-24",
        "cities": ["南昌市"],
        "weather_types": ["降雨", "高温"]
    }
    
    # 示例模板
    template = """7 月 1 日～ 24 日，全市平均降雨量为 {avg_precip} 毫米，较常年同 期 偏少 {climatology_diff} 成 ，为 1961 年以来历史同期 第 {rank_since_1961} 少位 县级以靖安 县 100.1 毫米为最多，樟树市 11.7 毫米为最少。 全市日平均气 温为 {avg_temp} ℃，较常年同期 偏高 {temp_diff} ℃，破 1961 年以来 历史极值， 县级以丰城市 32.1 ℃为最高，铜鼓县 29.6 ℃为最低。 7 月 22 日开 始，我市出现了今年入夏以来最炎热天气，有 6 个县（市、区） 最高气温超过 39 。根据高温热浪监测， 7 月 23 日我市大部分 地区已达到轻度热浪"""
    
    # 运行Agent
    report = agent.run(user_query, template)
    print(report)