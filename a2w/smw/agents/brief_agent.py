from typing import Any
import logging
from langchain_core.prompts import ChatPromptTemplate
from a2w.configs.smw_config import SmwConfig
from a2w.smw.agents.base_agent import BaseAgent
from a2w.smw.agents.state import StepStatus, WeatherReportState
from a2w.smw.templates.weather_report import WR_PROMPT
from a2w.smw.utils.smw_util import parse_think_content

logger = logging.getLogger(__name__)


class BriefAgent(BaseAgent):
    def __init__(self, llm: Any, config: SmwConfig = None):
        super().__init__(llm, name="BriefAgent", config=config)

    async def build_prompt(self) -> ChatPromptTemplate:
        prompt = ChatPromptTemplate.from_messages([
                ("system", WR_PROMPT["final_brief"]["system"]),
                ('user', WR_PROMPT["final_brief"]["user"])
            ])
        return prompt
    
    async def run(self, state: WeatherReportState) -> dict:
        """
        V0.2需要采纳多路召回 --> 语料库的label匹配 + 语义召回
        V0.1 先采用固定模板
        """
        try:
            state["final_brief"]["recall_template"] = None
            state["final_brief"]["sql_data"] = None
            prompt = await self.build_prompt()
            brief_text = await self.call_llm(prompt, state)
            think_context, no_think_context = parse_think_content(brief_text) # Where should we place the context of think?
            state["final_brief"]["response"] = no_think_context
            state["final_brief"]["think_response"] = think_context
            state["final_brief"]["status"] = StepStatus.SUCCESS
            state["final_brief"]["error"] = None
            self.logger.info("-"*60)
            self.logger.info(f"《The Detailed Weather final_brief》：\n{no_think_context}")
            self.logger.info("-"*60)
            
        except Exception as e:
            self.logger.error(f"The Detailed Weather final_brief Generate Failed: {e}")
            state["final_brief"]["status"] = StepStatus.FAILED
            state["final_brief"]["response"] = ""
            state["final_brief"]["think_response"] = ""
            state["final_brief"]["error"] = e
            raise
        return state
        
    async def call_llm(self, prompt: ChatPromptTemplate, state: WeatherReportState) -> str:
        try:
            chain = prompt | self.llm
            response = await chain.ainvoke({
                "forecast": state["forecast"].get("response"),
                "suggestion": state["suggestion"].get("response"),
                "summary": state["summary"].get("response")
            })
            return response.content
        except Exception as e:
            ValueError(e)
