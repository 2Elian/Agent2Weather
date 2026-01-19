from abc import ABC, abstractmethod
from typing import Optional

from langchain_openai import ChatOpenAI

from a2w.configs.smw_config import SmwConfig
from a2w.smw.executors import WeatherReportWorkflow
from a2w.smw.agents import HistoryWeatherAgent, ForecastWeatherAgent, SuggestionAgent, SummaryAgent, BriefAgent
from a2w.api.middleware.db.sql_connector import SQLServerConnector
from a2w.configs import GlobalConfig

class WorkflowFactory(ABC):
    @abstractmethod
    def create_weather_report_workflow(self) -> WeatherReportWorkflow:
        raise NotImplementedError
    @abstractmethod
    def create_powerful_weather_report_workflow(self) -> WeatherReportWorkflow:
        raise NotImplementedError
    @abstractmethod
    def create_nl2sql_workflow(self) -> WeatherReportWorkflow:
        raise NotImplementedError

class ProductionWorkflowFactory(WorkflowFactory):
    def __init__(self, config: GlobalConfig):
        self.config = config
        self.llm_instance = ChatOpenAI(
            model=self.config.get("model_name"),
            api_key=self.config.get("openai_api_key"),
            base_url=self.config.get("openai_api_base"),
        )
        self.db: Optional[SQLServerConnector] = None
        self.smw_config = SmwConfig()

    async def initialize(self):
        if self.db is None:
            self.db = SQLServerConnector(
                self.config.get("db_host"), self.config.get("db_port"), self.config.get("db_name"), self.config.get("db_username"), self.config.get("db_password")
            )
            await self.db.connect()

    def create_weather_report_workflow(self) -> WeatherReportWorkflow:
        return WeatherReportWorkflow(
            llm = self.llm_instance,
            db_connector=self.db,
            config=self.smw_config
        )

    def create_wr_history(self) -> HistoryWeatherAgent:
        return HistoryWeatherAgent(
            llm = self.llm_instance,
            db_connector=self.db,
            config=self.smw_config
        )
    def create_wr_forecast(self) -> ForecastWeatherAgent:
        return ForecastWeatherAgent(
            llm = self.llm_instance,
            db_connector=self.db,
            config=self.smw_config
        )
    def create_wr_suggest(self) -> SuggestionAgent:
        return SuggestionAgent(
            llm = self.llm_instance,
            embedding_recall_manager=None,
            config=self.smw_config
        )
    def create_wr_summary(self) -> SummaryAgent:
        return SummaryAgent(
            llm = self.llm_instance,
            embedding_recall_manager=None,
            config=self.smw_config
        )
    def create_wr_brief(self) -> BriefAgent:
        return BriefAgent(
            llm = self.llm_instance,
            config=self.smw_config
        )
    def create_powerful_weather_report_workflow(self) -> WeatherReportWorkflow:
        raise NotImplementedError
    def create_nl2sql_workflow(self) -> WeatherReportWorkflow:
        raise NotImplementedError
    async def close(self):
        await self.db.close()
    
_factory: Optional[WorkflowFactory] = None
_config: Optional[GlobalConfig] = None

def get_config() -> GlobalConfig:
    global _config
    if _config is None:
        _config = GlobalConfig()
    return _config

async def get_factory() -> ProductionWorkflowFactory:
    global _factory
    if _factory is None:
        config = get_config()
        _factory = ProductionWorkflowFactory(config)
        await _factory.initialize()
    return _factory

async def get_wr_async() -> WeatherReportWorkflow:
    factory = await get_factory()
    return factory.create_weather_report_workflow()

async def get_wr_history_async() -> HistoryWeatherAgent:
    factory = await get_factory()
    return factory.create_wr_history()

async def get_wr_forecast_async() -> ForecastWeatherAgent:
    factory = await get_factory()
    return factory.create_wr_forecast()

async def get_wr_suggest_async() -> SuggestionAgent:
    factory = await get_factory()
    return factory.create_wr_suggest()

async def get_wr_summary_async() -> SummaryAgent:
    factory = await get_factory()
    return factory.create_wr_summary()

async def get_wr_brief_async() -> BriefAgent:
    factory = await get_factory()
    return factory.create_wr_brief()


# async def get_pwr_async() -> WeatherReportWorkflow:
#     factory = await get_factory()
#     return factory.create_powerful_weather_report_workflow()
#
# async def get_nl2sql_async() -> WeatherReportWorkflow:
#     factory = await get_factory()
#     return factory.create_nl2sql_workflow()

async def close_factory():
    global _factory
    if _factory:
        await _factory.close()
        _factory = None

async def get_db_connector_async() -> SQLServerConnector:
    factory = await get_factory()
    return factory.db