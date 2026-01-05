from datetime import datetime
from enum import Enum
from typing import Dict, TypedDict, Any, Optional, List

from pydantic import BaseModel

class StepStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"

class BadcaseType(Enum):
    RECALL_TYPE = "recall"

class WeatherReportState(TypedDict):
    task_type: str
    start_date: datetime  # 开始日期 YYYY-MM-DD
    end_date: datetime  # 结束日期 YYYY-MM-DD
    station_names: List[str]

    init_weather_data: List[Dict[str, Any]]  # 初步返回的天气数据

    history_weather_data: Optional[Any]  # 前期天气数据(A2SQL查询结果)
    forecast_weather_data: Optional[Any]  # 预报天气数据(A2SQL查询结果)
    
    # 状态结果
    history: Dict[str, Any]  # 前期天气实况
    forecast: Dict[str, Any]  # 详细天气预报
    suggestion: Dict[str, Any]  # 关注与建议
    summary: Dict[str, Any]  # 摘要
    final_brief: Dict[str, Any]  # 最终简短提示

    error: Optional[str]

    tasks_completed: Dict[str, bool]
    
    def __init__(self):
        self.task_type = ""
        self.start_date = ""
        self.end_date = ""
        self.station_names = []
        self.init_weather_data = []
        self.history = {}
        self.forecast = {}
        self.suggestion = {}
        self.summary = {}
        self.final_brief = {}
        self.error = None
        self.tasks_completed = {}

class SmwReturn(BaseModel):
    status: str
    data: Optional[Dict[str, str]] = None
    meta_data: Optional[Dict[str, Any]]
    error: Optional[str] = None


class PowerfulWeatherReportState(TypedDict):
    # 用户输入
    task_type: str  # 任务类型：气象呈阅件/强天气报告
    start_date: str  # 开始日期 YYYY-MM-DD
    end_date: str  # 结束日期 YYYY-MM-DD
    region: str  # 地区范围
