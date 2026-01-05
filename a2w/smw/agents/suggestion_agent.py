from typing import Any
import logging

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from a2w.configs.smw_config import SmwConfig
from a2w.smw.agents.base_agent import BaseAgent
from a2w.smw.agents.state import StepStatus, WeatherReportState
from a2w.smw.managers.embedding_recall import EmbeddingRecallManager
from a2w.smw.templates.fixed_template.smw import SUGGEST_TEMPLATE
from a2w.smw.utils.smw_util import parse_think_content
from a2w.smw.templates.weather_report import WR_PROMPT
from a2w.utils.logger import setup_logger

class SuggestionAgent(BaseAgent):
    def __init__(self, llm: ChatOpenAI, embedding_recall_manager: EmbeddingRecallManager = None, config: SmwConfig = None):
        super().__init__(llm, name="SuggestionAgent", config=config)
        self.embedding_recall = embedding_recall_manager
        self.logger = setup_logger(name=__class__.__name__)
    async def build_prompt(self) -> ChatPromptTemplate:
        prompt = ChatPromptTemplate.from_messages([
                ("system", WR_PROMPT["suggestion"]["system"]),
                ('user', WR_PROMPT["suggestion"]["user"])
            ])
        return prompt
    
    async def run(self, state: WeatherReportState) -> dict:
        # TODO 采用固定模板的话 非常不好 参考历史做一个映射吧
        try:
            if not state["forecast"].get("response"):
                self.logger.error("Early-stage data or forecast text missing")
                raise
            recall_template = SUGGEST_TEMPLATE
            state["suggestion"]["recall_template"] = recall_template
            state["suggestion"]["sql_data"] = None
            prompt = await self.build_prompt()
            suggestion_text = await self.call_llm(prompt, state)
            think_context, no_think_context = parse_think_content(suggestion_text) # Where should we place the context of think?
            state["suggestion"]["response"] = no_think_context
            state["suggestion"]["think_response"] = think_context
            state["suggestion"]["status"] = StepStatus.SUCCESS
            state["suggestion"]["error"] = None
            self.logger.info("-"*60)
            self.logger.info(f"《The Detailed Weather suggestion》：\n{no_think_context}")
            self.logger.info("-"*60)
            
        except Exception as e:
            self.logger.error(f"The Detailed Weather suggestion Generate Failed: {e}")
            state["suggestion"]["status"] = StepStatus.FAILED
            state["suggestion"]["response"] = ""
            state["suggestion"]["think_response"] = ""
            state["suggestion"]["error"] = e
            raise
        return state
        
    async def call_llm(self, prompt: ChatPromptTemplate, state: WeatherReportState) -> str:
        try:
            chain = prompt | self.llm
            response = await chain.ainvoke({
                "forecast": state["forecast"].get("response"),
                "template": state["suggestion"]["recall_template"] 
            })
            return response.content
        except Exception as e:
            ValueError(e)
