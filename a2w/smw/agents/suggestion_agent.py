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

logger = logging.getLogger(__name__)


class SuggestionAgent(BaseAgent):
    def __init__(self, llm: ChatOpenAI, embedding_recall_manager: EmbeddingRecallManager, config: SmwConfig = None):
        super().__init__(llm, name="SuggestionAgent", config=config)
        self.embedding_recall = embedding_recall_manager
    
    async def build_prompt(self) -> ChatPromptTemplate:
        prompt = ChatPromptTemplate.from_messages([
                ("system", WR_PROMPT["suggestion"]["system"]),
                ('user', WR_PROMPT["suggestion"]["user"])
            ])
        return prompt
    
    async def run(self, state: WeatherReportState) -> dict:
        """
        V0.2需要采纳多路召回 --> 语料库的label匹配 + 语义召回
        V0.1 先采用固定模板
        """
        try:
            if not state["forecast"].get("response"):
                logger.error("Early-stage data or forecast text missing")
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
                "forecast": state["forecast_text"].get("response"),
                "template": state["suggestion"]["recall_template"] 
            })
            return response.content
        except Exception as e:
            ValueError(e)
