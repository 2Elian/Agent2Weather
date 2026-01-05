import asyncio
from typing import Any, List, Dict, Optional
import logging
from abc import ABC, abstractmethod

class DBConnector(ABC):
    @abstractmethod
    async def connect(self):
        raise NotImplementedError
    
    @abstractmethod
    async def close(self):
        raise NotImplementedError
    
    @abstractmethod
    async def execute_query(self, sql: str) -> Optional[List[Dict[str, Any]]]:
        raise NotImplementedError
    
    @abstractmethod
    async def query_weather_metrics(self, region: str, start_date: str, end_date: str) -> Optional[Dict[str, Any]]:
        """查询天气指标数据"""
        raise NotImplementedError
    
    @abstractmethod
    async def query_detailed_weather_from_dayTable(self,  regions: List[str],  start_date: str,  end_date: str, detail_level: str = "standard") -> List[Dict[str, Any]]:
        """查询日表数据"""
        raise NotImplementedError
    
    @abstractmethod
    async def query_detailed_weather_from_hourTable(self, regions: List[str], start_date: str, end_date: str,aggregation: str = "daily", station_name_to_cnty: bool = False) -> List[Dict[str, Any]]:
        """查询小时表数据"""
        raise NotImplementedError
    
    async def query_cnty_by_regions(self, regions: List[str]) -> List[str]:
        """根据 station_name 查询对应的区县"""
        raise NotImplementedError