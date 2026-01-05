from typing import Any
import logging

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from a2w.configs.smw_config import SmwConfig
from a2w.smw.agents.base_agent import BaseAgent
from a2w.smw.agents.state import StepStatus, WeatherReportState
from a2w.smw.managers.embedding_recall import EmbeddingRecallManager
from a2w.smw.templates.fixed_template.smw import SUMMARY_TEMPLATE
from a2w.smw.templates.weather_report import WR_PROMPT
from a2w.smw.utils.smw_util import parse_think_content
from a2w.utils.logger import setup_logger

class SummaryAgent(BaseAgent):
    def __init__(self, llm: ChatOpenAI, embedding_recall_manager: EmbeddingRecallManager, config: SmwConfig = None):
        super().__init__(llm, name="SummaryAgent", config=config)
        self.embedding_recall = embedding_recall_manager
        self.logger = setup_logger(name=__class__.__name__)
    async def build_prompt(self) -> ChatPromptTemplate:
        prompt = ChatPromptTemplate.from_messages([
                ("system", WR_PROMPT["summary"]["system"]),
                ('user', WR_PROMPT["summary"]["user"])
            ])
        return prompt
    
    async def run(self, state: WeatherReportState) -> WeatherReportState:
        """
        V0.2需要采纳多路召回 --> 语料库的label匹配 + 语义召回
        V0.1 先采用固定模板
        """
        try:
            recall_template = SUMMARY_TEMPLATE
            state["summary"]["recall_template"] = recall_template
            state["summary"]["sql_data"] = None
            prompt = await self.build_prompt()
            summary_text = await self.call_llm(prompt, state)
            think_context, no_think_context = parse_think_content(summary_text) # Where should we place the context of think?
            state["summary"]["response"] = no_think_context
            state["summary"]["think_response"] = think_context
            state["summary"]["status"] = StepStatus.SUCCESS
            state["summary"]["error"] = None
            self.logger.info("-"*60)
            self.logger.info(f"《The Detailed Weather summary》：\n{no_think_context}")
            self.logger.info("-"*60)
            
        except Exception as e:
            self.logger.error(f"The Detailed Weather summary Generate Failed: {e}")
            state["summary"]["status"] = StepStatus.FAILED
            state["summary"]["response"] = ""
            state["summary"]["think_response"] = ""
            state["summary"]["error"] = e
            raise
        return state
        
    async def call_llm(self, prompt: ChatPromptTemplate, state: WeatherReportState) -> str:
        try:
            chain = prompt | self.llm
            response = await chain.ainvoke({
                "forecast": state["forecast"].get("response"),
                "suggestion": state["suggestion"].get("response"),
                "template": state["summary"]["recall_template"] 
            })
            return response.content
        except Exception as e:
            ValueError(e)
