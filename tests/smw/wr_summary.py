#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 1/5/2026 6:14 PM
# @Author  : lizimo@nuist.edu.cn
# @File    : wt_history.py
# @Description:
from typing import List, Optional, Dict, Any
import os
import time
from langchain_openai import ChatOpenAI
from a2w.configs.smw_config import SmwConfig
from a2w.utils.time_record import time_recorder
from a2w.api.middleware.db.sql_connector import SQLServerConnector
from a2w.smw.managers.weather_classifier import WeatherClassifier
from a2w.smw.agents.state import WeatherReportState
from a2w.smw.agents import ForecastWeatherAgent, SummaryAgent, SuggestionAgent
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
        smw_config.set(key="smw_weather_classify_path",
                       value=r"G:\项目成果打包\气象局服务材料写作系统\宜春\RAG\Weather-Agent-YiChun\data\sm\weather_classification_results.json")
        smw_config.set(key="badcase_data_path",
                       value=r"G:\项目成果打包\气象局服务材料写作系统\宜春\RAG\Weather-Agent-YiChun\data\badcase")
        print(smw_config)
        self.forecast_instance = ForecastWeatherAgent(llm=self.llm_instance, db_connector=self.db, config=smw_config)
        self.summary_instance = SummaryAgent(llm=self.llm_instance, embedding_recall_manager=None, config=smw_config)
        self.suggest_instance = SuggestionAgent(llm=self.llm_instance, embedding_recall_manager=None, config=smw_config)
    @classmethod
    async def create(cls, host: str, port: str, database: str, username: str, password: str) -> "TestDB":
        db = SQLServerConnector(host, port, database, username, password)
        await db.connect()
        return cls(db)

    async def close(self):
        await self.db.close()

    @time_recorder(func_name="ForeCastTester")
    async def forecast(self, regions: List[str], start_date: str, end_date: str):
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
        return result["forecast"]

    @time_recorder(func_name="SuggestTester")
    async def suggest(self, regions: List[str], start_date: str, end_date: str) -> Optional[Dict[str, Any]]:
        forecast_result = await self.forecast(
            regions=regions,
            start_date=start_date,
            end_date=end_date
        )
        state = WeatherReportState(
            task_type="气象呈阅件",
            start_date=start_date,
            end_date=end_date,
            station_names=regions,
            init_weather_data=None,
            history={},
            forecast=forecast_result,
            suggestion={},
            summary={},
            final_brief={},
            error=None,
            tasks_completed={}
        )
        result = await self.suggest_instance.run(state=state)
        return result

    @time_recorder(func_name="SummaryTester")
    async def summary(self, regions: List[str], start_date: str, end_date: str) -> Optional[Dict[str, Any]]:
        state = await self.suggest(regions=regions, start_date=start_date, end_date=end_date)
        result = await self.summary_instance.run(state)
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
        result = await test_db.summary(
            regions=["赤岸观下气象观测站", "丰城秀市座山"],
            start_date="2025-06-08",
            end_date="2025-06-12",
        )
        print(result)
    finally:
        await test_db.close()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())