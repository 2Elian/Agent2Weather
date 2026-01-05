#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Query Decomposer Module
将用户查询分解为可执行的数据查询子任务
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict


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
class DecomposedQuery:
    """分解后的查询"""
    meta: Dict[str, Any]
    sub_queries: List[SubQuery]


class QueryDecomposer:
    """查询分解器"""
    
    def __init__(self, available_tools: Dict[str, Any]):
        """
        初始化查询分解器
        
        Args:
            available_tools: 可用工具的schema列表
        """
        self.available_tools = available_tools
    
    def decompose(self, user_query: Dict[str, Any], template: str) -> DecomposedQuery:
        """
        将用户查询分解为子查询
        
        Args:
            user_query: 用户查询，包含开始日期、结束日期、城市列表、天气类型列表
            template: 模板文本
            
        Returns:
            分解后的查询对象
        """
        # 提取元数据
        meta = {
            "start_date": user_query.get("start_date"),
            "end_date": user_query.get("end_date"),
            "cities": user_query.get("cities", []),
            "weather_types": user_query.get("weather_types", [])
        }
        
        # 根据模板内容和用户需求生成子查询
        sub_queries = self._generate_sub_queries(meta, template)
        
        return DecomposedQuery(meta=meta, sub_queries=sub_queries)
    
    def _generate_sub_queries(self, meta: Dict[str, Any], template: str) -> List[SubQuery]:
        """
        根据元数据和模板生成子查询列表
        
        Args:
            meta: 查询元数据
            template: 模板文本
            
        Returns:
            子查询列表
        """
        sub_queries = []
        
        # 分析模板中的关键信息需求
        weather_types = meta.get("weather_types", [])
        
        # 为每种天气类型生成相应的查询
        if "降雨" in weather_types or "降水" in weather_types:
            sub_queries.append(SubQuery(
                id="rainfall_summary",
                purpose="统计期间内全市平均降雨量及与常年对比",
                required_by_template=True,
                tool="query_precipitation_stats",
                params={
                    "start_date": meta["start_date"],
                    "end_date": meta["end_date"],
                    "cities": meta["cities"],
                    "aggregation": "mean_vs_climatology"
                },
                expected_fields=["avg_precip", "climatology_diff", "rank_since_1961"]
            ))
            
            sub_queries.append(SubQuery(
                id="rainfall_extremes_by_county",
                purpose="县级降雨量极值",
                required_by_template=True,
                tool="query_precipitation_by_county",
                params={
                    "start_date": meta["start_date"],
                    "end_date": meta["end_date"],
                    "cities": meta["cities"]
                },
                expected_fields=["county", "precip"]
            ))
        
        if "高温" in weather_types or "气温" in weather_types:
            sub_queries.append(SubQuery(
                id="temperature_summary",
                purpose="全市平均气温及历史极值",
                required_by_template=True,
                tool="query_temperature_stats",
                params={
                    "start_date": meta["start_date"],
                    "end_date": meta["end_date"],
                    "cities": meta["cities"]
                },
                expected_fields=["avg_temp", "diff", "is_historical_extreme"]
            ))
            
            sub_queries.append(SubQuery(
                id="heatwave_monitor",
                purpose="高温热浪过程描述",
                required_by_template=True,
                tool="query_heatwave_events",
                params={
                    "start_date": meta["start_date"],
                    "end_date": meta["end_date"],
                    "cities": meta["cities"]
                },
                expected_fields=["start_date", "counties", "intensity"]
            ))
        
        # 添加通用的统计数据查询
        sub_queries.append(SubQuery(
            id="general_stats",
            purpose="基础气象统计数据",
            required_by_template=False,
            tool="query_general_weather_stats",
            params={
                "start_date": meta["start_date"],
                "end_date": meta["end_date"],
                "cities": meta["cities"]
            },
            expected_fields=["start_date", "end_date", "city_count"]
        ))
        
        return sub_queries


# 示例使用
if __name__ == "__main__":
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
    
    # 创建分解器
    decomposer = QueryDecomposer(available_tools)
    
    # 示例用户查询
    user_query = {
        "start_date": "2024-07-01",
        "end_date": "2024-07-24",
        "cities": ["南昌市", "九江市", "景德镇市"],
        "weather_types": ["降雨", "高温"]
    }
    
    # 示例模板
    template = """7 月 1 日～ 24 日，全市平均降雨量为 47.0 毫米，较常年同 期 偏少 7.0 成 ，为 1961 年以来历史同期 第 12 少位 县级以靖安 县 100.1 毫米为最多，樟树市 11.7 毫米为最少。 全市日平均气 温为 31.1 ℃，较常年同期 偏高 2.4 ℃，破 1961 年以来 历史极值， 县级以丰城市 32.1 ℃为最高，铜鼓县 29.6 ℃为最低。 7 月 22 日开 始，我市出现了今年入夏以来最炎热天气，有 6 个县（市、区） 最高气温超过 39 。根据高温热浪监测， 7 月 23 日我市大部分 地区已达到轻度热浪"""
    
    # 执行分解
    result = decomposer.decompose(user_query, template)
    
    # 输出结果
    print("查询元数据:")
    print(json.dumps(result.meta, ensure_ascii=False, indent=2))
    print("\n子查询列表:")
    for i, sub_query in enumerate(result.sub_queries):
        print(f"\n子查询 {i+1}:")
        print(json.dumps(asdict(sub_query), ensure_ascii=False, indent=2))