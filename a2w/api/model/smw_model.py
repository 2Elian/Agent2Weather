import datetime
from typing import Optional, Any, Generic, TypeVar, List
from pydantic import BaseModel, Field
from dateutil.parser import parse

class SmwRequest(BaseModel):
    task_type: str = Field(..., description="任务类型: 气象呈阅件/强天气报告")
    start_date: datetime = Field(..., description="开始日期")
    end_date: datetime = Field(..., description="结束日期")
    station_names: List[str] = Field(..., description="站点名称: [\"宜春国家基准气候站\", \"袁州温汤国家气象观测站\"]")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def get_start_datetime(self) -> datetime:
        if isinstance(self.start_date, str):
            return parse(self.start_date)
        return self.start_date
    
    def get_end_datetime(self) -> datetime:
        if isinstance(self.end_date, str):
            return parse(self.end_date)
        return self.end_date
    
class SmwResponse(BaseModel):
    status: str = Field(..., description="执行状态")
    data: Optional[dict] = Field(None, description="响应数据")
    error: Optional[str] = Field(None, description="错误信息")
    metadata: Optional[dict] = Field(None, description="元数据")
    
    class Config:
        json_json_schema_extra = {
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