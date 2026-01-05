#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Template-conditioned Generation Module
根据模板和数据生成最终报告
"""

import json
import re
from typing import Dict, List, Any, Optional
from datetime import datetime


class TemplateGenerator:
    """模板生成器"""
    
    def __init__(self):
        """初始化模板生成器"""
        pass
    
    def generate(self, template: str, query_meta: Dict[str, Any], 
                 data_results: Dict[str, Any]) -> str:
        """
        根据模板和数据生成报告
        
        Args:
            template: 模板文本
            query_meta: 查询元数据
            data_results: 数据查询结果
            
        Returns:
            生成的报告文本
        """
        # 处理模板中的占位符
        report = self._fill_placeholders(template, data_results)
        
        # 根据数据动态生成文本片段
        report = self._generate_dynamic_sections(report, data_results)
        
        # 格式化数值
        report = self._format_numbers(report)
        
        return report
    
    def _fill_placeholders(self, template: str, data_results: Dict[str, Any]) -> str:
        """
        填充模板中的占位符
        
        Args:
            template: 模板文本
            data_results: 数据查询结果
            
        Returns:
            填充后的文本
        """
        # 收集所有数据结果中的字段
        all_data = {}
        for query_id, result in data_results.items():
            if result.get("status") == "success" and "data" in result:
                all_data.update(result["data"])
        
        # 替换模板中的占位符
        report = template
        for key, value in all_data.items():
            placeholder = "{" + key + "}"
            if placeholder in report:
                report = report.replace(placeholder, str(value))
        
        return report
    
    def _generate_dynamic_sections(self, report: str, data_results: Dict[str, Any]) -> str:
        """
        根据数据动态生成文本片段
        
        Args:
            report: 报告文本
            data_results: 数据查询结果
            
        Returns:
            生成的报告文本
        """
        # 处理县级极值数据
        county_precip_data = self._extract_county_data(data_results, "rainfall_extremes_by_county")
        if county_precip_data:
            precip_section = self._generate_county_precip_section(county_precip_data)
            # 替换模板中的相应部分
            report = self._replace_section(report, "县级降雨量极值", precip_section)
        
        # 处理高温热浪数据
        heatwave_data = self._extract_heatwave_data(data_results)
        if heatwave_data:
            heatwave_section = self._generate_heatwave_section(heatwave_data)
            # 替换模板中的相应部分
            report = self._replace_section(report, "高温热浪过程", heatwave_section)
        
        # 处理县级气温极值数据
        county_temp_data = self._extract_county_data(data_results, "temperature_extremes_by_county")
        if county_temp_data:
            temp_section = self._generate_county_temp_section(county_temp_data)
            # 替换模板中的相应部分
            report = self._replace_section(report, "县级气温极值", temp_section)
        
        return report
    
    def _extract_county_data(self, data_results: Dict[str, Any], query_type: str) -> List[Dict[str, Any]]:
        """
        提取县级数据
        
        Args:
            data_results: 数据查询结果
            query_type: 查询类型
            
        Returns:
            县级数据列表
        """
        for query_id, result in data_results.items():
            if query_type in query_id and result.get("status") == "success":
                data = result.get("data", {})
                if "counties" in data:
                    return data["counties"]
                # 处理直接返回county数据的情况
                counties = []
                for key in ["county", "name"]:
                    if key in data:
                        counties.append({
                            "name": data[key],
                            "precip": data.get("precip", 0),
                            "temp": data.get("temp", 0),
                            "extreme_type": data.get("extreme_type", "")
                        })
                if counties:
                    return counties
        return []
    
    def _extract_heatwave_data(self, data_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        提取高温热浪数据
        
        Args:
            data_results: 数据查询结果
            
        Returns:
            高温热浪数据列表
        """
        for query_id, result in data_results.items():
            if "heatwave" in query_id and result.get("status") == "success":
                data = result.get("data", {})
                if "events" in data:
                    return data["events"]
                # 处理直接返回事件数据的情况
                if "start_date" in data:
                    return [data]
        return []
    
    def _generate_county_precip_section(self, county_data: List[Dict[str, Any]]) -> str:
        """
        生成县级降雨量极值段落
        
        Args:
            county_data: 县级数据
            
        Returns:
            生成的段落文本
        """
        if not county_data:
            return ""
        
        # 找出最大值和最小值
        max_precip = max(county_data, key=lambda x: x.get("precip", 0)) if county_data else {}
        min_precip = min(county_data, key=lambda x: x.get("precip", float('inf'))) if county_data else {}
        
        section = ""
        if max_precip:
            section += f"县级以{max_precip.get('name', '')} {max_precip.get('precip', 0)} 毫米为最多"
            if min_precip and min_precip.get('name') != max_precip.get('name'):
                section += f"，{min_precip.get('name', '')} {min_precip.get('precip', 0)} 毫米为最少"
            section += "。"
        
        return section
    
    def _generate_heatwave_section(self, heatwave_data: List[Dict[str, Any]]) -> str:
        """
        生成高温热浪段落
        
        Args:
            heatwave_data: 高温热浪数据
            
        Returns:
            生成的段落文本
        """
        if not heatwave_data:
            return ""
        
        sections = []
        for event in heatwave_data:
            start_date = event.get("start_date", "")
            counties = event.get("counties", [])
            intensity = event.get("intensity", "")
            
            # 格式化日期
            if start_date:
                try:
                    date_obj = datetime.strptime(start_date, "%Y-%m-%d")
                    formatted_date = f"{date_obj.month} 月 {date_obj.day} 日"
                except:
                    formatted_date = start_date
            else:
                formatted_date = "近期"
            
            section = f"{formatted_date} 开始，我市出现了高温热浪天气"
            if counties:
                section += f"，有 {len(counties)} 个县（市、区）"
            if intensity:
                section += f"达到{intensity}强度"
            section += "。"
            sections.append(section)
        
        return "".join(sections)
    
    def _generate_county_temp_section(self, county_data: List[Dict[str, Any]]) -> str:
        """
        生成县级气温极值段落
        
        Args:
            county_data: 县级数据
            
        Returns:
            生成的段落文本
        """
        if not county_data:
            return ""
        
        # 找出最高温和最低温
        max_temp = max(county_data, key=lambda x: x.get("temp", 0)) if county_data else {}
        min_temp = min(county_data, key=lambda x: x.get("temp", float('inf'))) if county_data else {}
        
        section = ""
        if max_temp:
            section += f"县级以{max_temp.get('name', '')} {max_temp.get('temp', 0)} ℃为最高"
            if min_temp and min_temp.get('name') != max_temp.get('name'):
                section += f"，{min_temp.get('name', '')} {min_temp.get('temp', 0)} ℃为最低"
            section += "。"
        
        return section
    
    def _replace_section(self, report: str, marker: str, replacement: str) -> str:
        """
        替换报告中的特定段落
        
        Args:
            report: 报告文本
            marker: 标记文本
            replacement: 替换文本
            
        Returns:
            替换后的报告文本
        """
        # 查找标记位置并替换
        if marker in report:
            # 找到标记前后的句子边界
            sentences = report.split("。")
            for i, sentence in enumerate(sentences):
                if marker in sentence:
                    sentences[i] = replacement
                    break
            return "。".join(sentences)
        return report
    
    def _format_numbers(self, report: str) -> str:
        """
        格式化报告中的数值
        
        Args:
            report: 报告文本
            
        Returns:
            格式化后的报告文本
        """
        # 移除多余的空格
        report = re.sub(r'\s+', ' ', report)
        
        # 确保数字格式正确
        report = re.sub(r'(\d+)\s*\.?\s*(\d*)\s*℃', r'\1.\2 ℃', report)
        report = re.sub(r'(\d+)\s*\.?\s*(\d*)\s*毫米', r'\1.\2 毫米', report)
        report = re.sub(r'(\d+)\s*\.?\s*(\d*)\s*成', r'\1.\2 成', report)
        
        # 清理多余的标点
        report = re.sub(r'，\s*，', '，', report)
        report = re.sub(r'。\s*。', '。', report)
        
        return report.strip()


# 示例使用
if __name__ == "__main__":
    # 创建生成器
    generator = TemplateGenerator()
    
    # 示例模板
    template = """7 月 1 日～ 24 日，全市平均降雨量为 {avg_precip} 毫米，较常年同 期 偏少 {climatology_diff} 成 ，为 1961 年以来历史同期 第 {rank_since_1961} 少位 县级降雨量极值。 全市日平均气 温为 {avg_temp} ℃，较常年同期 偏高 {diff} ℃，破 1961 年以来 历史极值， 县级气温极值。 7 月 22 日开 始，我市出现了高温热浪过程。"""
    
    # 示例查询元数据
    query_meta = {
        "start_date": "2024-07-01",
        "end_date": "2024-07-24",
        "cities": ["南昌市"],
        "weather_types": ["降雨", "高温"]
    }
    
    # 示例数据结果
    data_results = {
        "rainfall_summary_1": {
            "status": "success",
            "data": {
                "avg_precip": 47.0,
                "climatology_diff": 7.0,
                "rank_since_1961": 12
            }
        },
        "temperature_summary_2": {
            "status": "success",
            "data": {
                "avg_temp": 31.1,
                "diff": 2.4,
                "is_historical_extreme": True
            }
        },
        "rainfall_extremes_by_county_3": {
            "status": "success",
            "data": {
                "counties": [
                    {"name": "靖安县", "precip": 100.1, "extreme_type": "最多"},
                    {"name": "樟树市", "precip": 11.7, "extreme_type": "最少"}
                ]
            }
        },
        "temperature_extremes_by_county_4": {
            "status": "success",
            "data": {
                "counties": [
                    {"name": "丰城市", "temp": 32.1, "extreme_type": "最高"},
                    {"name": "铜鼓县", "temp": 29.6, "extreme_type": "最低"}
                ]
            }
        },
        "heatwave_monitor_5": {
            "status": "success",
            "data": {
                "events": [
                    {
                        "start_date": "2024-07-22",
                        "duration": 3,
                        "counties": ["南昌县", "新建区", "安义县", "进贤县", "湾里区", "青山湖区"],
                        "intensity": "轻度"
                    }
                ]
            }
        }
    }
    
    # 生成报告
    report = generator.generate(template, query_meta, data_results)
    
    # 输出结果
    print("生成的报告:")
    print(report)