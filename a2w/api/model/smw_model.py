from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel,Field,ConfigDict,field_validator
from dateutil.parser import parse


class SmwRequest(BaseModel):
    task_type: str = Field(
        ...,
        description="任务类型: 气象呈阅件 / 强天气报告"
    )
    start_date: str = Field(
        ...,
        description="开始日期（支持 ISO8601 或常见时间字符串）"
    )
    end_date: str = Field(
        ...,
        description="结束日期（支持 ISO8601 或常见时间字符串）"
    )
    station_names: List[str] = Field(
        ...,
        description='站点名称列表，例如 ["宜春国家基准气候站", "袁州温汤国家气象观测站"]'
    )
    depends: bool = Field(
        False,
        description="是否依赖前序结果（true/false）"
    )
    forecast: str = Field(
        "",
        description="如果依赖于前序结果 必须提供预报文本 --> 只需要传递response字段即可"
    )
    suggestion: str = Field(
        "",
        description="如果依赖于前序结果 必须提供建议文本"
    )
    summary: str = Field(
        "",
        description="如果依赖于前序结果 必须提供摘要文本"
    )
    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def parse_datetime(cls, v):
        if not isinstance(v, str):
            return str(v)
        return v
    def get_start_datetime(self) -> str:
        return self.start_date

    def get_end_datetime(self) -> str:
        return self.end_date


class SmwResponse(BaseModel):
    status: str = Field(
        ...,
        description="执行状态: success / failed"
    )

    data: Optional[Dict[str, Any]] = Field(
        None,
        description="响应数据"
    )

    error: Optional[str] = Field(
        None,
        description="错误信息"
    )

    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="元数据"
    )
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "data": {
                    "result": {
                        "sql": "SELECT name, salary FROM instructor WHERE dept_name = 'Computer Science'"
                    }
                },
                "error": None,
                "metadata": {}
            }
        }
    )
