from typing import List, Optional, Dict, Any
import os
import time
from langchain_openai import ChatOpenAI
from a2w.configs.smw_config import SmwConfig
from a2w.utils.time_record import time_recorder
from a2w.api.middleware.db.sql_connector import SQLServerConnector
from a2w.smw.managers.weather_classifier import WeatherClassifier
from a2w.smw.agents.state import WeatherReportState
from a2w.smw.agents import ForecastWeatherAgent, HistoryWeatherAgent
from a2w.smw.funcalls.db_function_call import set_sqlserver_exe
import asyncio

os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''
os.environ['http_proxy'] = ''
os.environ['https_proxy'] = ''
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'

class TestDB:
    def __init__(self, db: SQLServerConnector):
        self.db = db
        self.llm_instance = ChatOpenAI(
            model="qwen30b",
            api_key="NuistMathAutoModelForCausalLM",
            base_url="http://172.16.107.15:23333/v1",
            temperature=0.2
        )
        set_sqlserver_exe(db_instance=self.db)
        smw_config = SmwConfig()
        smw_config.set(key="smw_weather_classify_path", value=r"G:\项目成果打包\气象局服务材料写作系统\宜春\RAG\Weather-Agent-YiChun\data\sm\weather_classification_results.json")
        smw_config.set(key="badcase_data_path", value=r"G:\项目成果打包\气象局服务材料写作系统\宜春\RAG\Weather-Agent-YiChun\data\badcase")
        print(smw_config)
        self.forecast_instance = ForecastWeatherAgent(llm=self.llm_instance, db_connector=self.db, config=smw_config)
        self.history_instance = HistoryWeatherAgent(llm=self.llm_instance, db_connector=self.db, config=smw_config)

    @classmethod
    async def create(cls, host: str, port: str, database: str, username: str, password: str) -> "TestDB":
        db = SQLServerConnector(host, port, database, username, password)
        await db.connect()
        return cls(db)

    async def close(self):
        await self.db.close()

    @time_recorder(func_name="ForeCastTester")
    async def forecast(self, regions: List[str], start_date: str, end_date: str) -> Optional[Dict[str, Any]]:
        # done
        state = WeatherReportState(
            task_type="气象呈阅件",
            start_date=start_date,
            end_date=end_date,
            station_names=regions,
            init_weather_data=[],
            history={},
            forecast={},
            suggestion={},
            summary={},
            final_brief={},
            error=None,
            tasks_completed={}
        )
        result = await self.forecast_instance.run(state=state)
        return result
    
    @time_recorder(func_name="HistoryTester")
    async def history(self, regions: List[str], start_date: str, end_date: str) -> Optional[Dict[str, Any]]:
        metrics_data = await self.db.query_weather_metrics(
            regions=regions,
            start_date=start_date,
            end_date=end_date
        )

        metrics = WeatherClassifier.parse_sql_result(metrics_data) # List[Dict[str, Any]]
        analyst_result = WeatherClassifier.classify_stations(metrics) # List[Dict[str, Any]]
        state = WeatherReportState(
            task_type="气象呈阅件",
            start_date=start_date,
            end_date=end_date,
            station_names=regions,
            init_weather_data=analyst_result,
            history={},
            forecast={},
            suggestion={},
            summary={},
            final_brief={},
            error=None,
            tasks_completed={}
        )
        result = await self.history_instance.run(state=state)
        return result

    

async def main():
    test_db = await TestDB.create(
        host="172.16.107.15",
        port="1433",
        database="A2W_YiChun",
        username="sa",
        password="YourStrong!Passw0rd"
    )

    try:
        result = await test_db.history(
            regions=["万载杨源村", "宜丰谭山院前"],
            start_date="2025-01-01",
            end_date="2025-01-07",
        )
        print(result)
    finally:
        await test_db.close() 

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())