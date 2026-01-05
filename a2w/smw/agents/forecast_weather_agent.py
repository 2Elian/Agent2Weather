import json
from typing import Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from a2w.configs.smw_config import SmwConfig
from a2w.smw.agents.state import WeatherReportState, StepStatus
from a2w.smw.agents.base_agent import BaseAgent
from a2w.api.middleware.db.base_db import DBConnector
from a2w.smw.templates.fixed_template.smw import SPECIFIC_WEATHER_TEMPLATE
from a2w.smw.templates.weather_report import WR_PROMPT
from a2w.smw.utils.smw_util import parse_think_content
from a2w.utils.logger import setup_logger

class ForecastWeatherAgent(BaseAgent):
    def __init__(self, llm: ChatOpenAI, db_connector: DBConnector, config: SmwConfig = None):
        super().__init__(llm, name="ForecastWeatherAgent", config=config)
        self.db = db_connector
        self.logger = setup_logger(name=__class__.__name__)

    async def build_prompt(self) -> ChatPromptTemplate:
        prompt = ChatPromptTemplate.from_messages([
                ("system", WR_PROMPT["forecast"]["system"]),
                ('user', WR_PROMPT["forecast"]["user"])
            ])
        return prompt
    
    async def run(self, state: WeatherReportState) -> WeatherReportState:
        # V0.1.0 done
        try:
            self.logger.info(f"Query Weather Forecast Date: {state['start_date']} ~ {state['end_date']}")
            # TODO: recall a template --> After recall the template, record the state of recalled--> state["recall_template"].append({"stage": "forecast", "template": str})
            # here we use a fixed template for recall.
            recall_template = SPECIFIC_WEATHER_TEMPLATE
            state["forecast"]["recall_template"] = recall_template
            forecast_data = await self.db.query_detailed_weather_from_hourTable(
                regions=state["station_names"],
                start_date=state["start_date"],
                end_date=state["end_date"],
                aggregation="half", # optional["hourly", "half", "daily"]
                station_name_to_cnty = True
            )
            if not forecast_data:
                state["forecast"]["sql_data"] = ""
                self.logger.error("Forecast Weather Data Query is None")
                raise
            state["forecast"]["sql_data"] = forecast_data
            prompt = await self.build_prompt()
            forecast_text = await self.call_llm(prompt, state)
            think_context, no_think_context = parse_think_content(forecast_text) # Where should we place the context of think?
            state["forecast"]["response"] = no_think_context
            state["forecast"]["think_response"] = think_context
            state["forecast"]["status"] = StepStatus.SUCCESS
            state["forecast"]["error"] = None
            self.logger.info("-"*60)
            self.logger.info(f"《The Detailed Weather Forecast》：\n{no_think_context}")
            self.logger.info("-"*60)
            
        except Exception as e:
            self.logger.error(f"The Detailed Weather Forecast Generate Failed: {e}")
            state["forecast"]["status"] = StepStatus.FAILED
            state["forecast"]["response"] = ""
            state["forecast"]["think_response"] = ""
            state["forecast"]["error"] = e
            raise
        return state
        
    async def call_llm(self, prompt: ChatPromptTemplate, state: WeatherReportState) -> str:
        try:
            chain = prompt | self.llm
            response = await chain.ainvoke({
                "weather_data": json.dumps(state["forecast"]["sql_data"], ensure_ascii=False),
                "template": state["forecast"]["recall_template"] 
            })
            return response.content
        except Exception as e:
            ValueError(e)