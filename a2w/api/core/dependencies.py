from abc import ABC, abstractmethod
from typing import Optional

from langchain_openai import ChatOpenAI

from a2w.configs.smw_config import SmwConfig
from a2w.smw.executors import WeatherReportWorkflow
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
    def __init__(self, config: GlobalConfig, ):
        self.config = config
        self.llm_instance = ChatOpenAI(
            model=self.config.model_name,
            api_key=self.config.openai_api_key,
            base_url=self.config.openai_api_base,
            temperature=0.2
        )
        self.db = SQLServerConnector(
            host=self.config.db_host,
            port=self.config.db_port,
            database=self.config.db_name,
            username=self.config.db_username,
            password=self.config.db_password
        )
        self.smw_config = SmwConfig()

    async def initialize(self):
        await self.db.connect()
        return self
        
    def create_weather_report_workflow(self) -> WeatherReportWorkflow:
        return WeatherReportWorkflow(
            llm = self.llm_instance,
            db_connector=self.db,
            config=self.smw_config
        )
    def create_powerful_weather_report_workflow(self) -> WeatherReportWorkflow:
        raise NotImplementedError
    def create_nl2sql_workflow(self) -> WeatherReportWorkflow:
        raise NotImplementedError
    async def close(self):
        if hasattr(self, 'db') and self.db:
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

async def get_pwr_async() -> WeatherReportWorkflow:
    factory = await get_factory()
    return factory.create_powerful_weather_report_workflow()

async def get_nl2sql_async() -> WeatherReportWorkflow:
    factory = await get_factory()
    return factory.create_nl2sql_workflow()

async def close_factory():
    global _factory
    if _factory:
        await _factory.close()
        _factory = None