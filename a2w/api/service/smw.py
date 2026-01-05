from typing import List, Dict, Any

from a2w.utils import setup_logger
from a2w.smw.executors import WeatherReportWorkflow

logger = setup_logger("api.smw.service")

class SmwService:
    @staticmethod
    async def execute_weather_report(request, workflow: WeatherReportWorkflow):
        user_input = {
            "task_type": request.task_type,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "station_names": request.station_names
        }
        result = await workflow.run(user_input=user_input)
        return result