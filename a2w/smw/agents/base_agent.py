from abc import ABC, abstractmethod
import json
from typing import Any, Optional
import os
import logging
from langchain_openai.chat_models.base import BaseChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from a2w.smw.agents.state import WeatherReportState, BadcaseType
from a2w.configs.smw_config import SmwConfig
from a2w.smw.agents.pecw import PECWAgent
from a2w.smw.funcalls import TOOLS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    def __init__(self, llm: BaseChatOpenAI, name: str = "BaseAgent", config: SmwConfig = None):
        self.llm = llm
        self.name = name
        self.config = config
        self.badcase_path = self.config.get("badcase_data_path")
        available_tools = {tool.name: tool for tool in TOOLS}
        self.pecw_agent = PECWAgent(tool_registry=available_tools, llm=self.llm)
    
    @abstractmethod
    async def build_prompt(self) -> str:
        raise NotImplementedError
    
    @abstractmethod
    async def run(self, state: WeatherReportState) -> dict:
        raise NotImplementedError
    
    async def call_llm(self, prompt: ChatPromptTemplate) -> str:
        # if no paramters are required, please use this parent class's 'call_llm' function. otherwise, please override 'call_llm'
        try:
            chain = prompt | self.llm
            response = await chain.ainvoke()
            return response.content
        except Exception as e:
            logger.error(f"{self.name} LLM call failed: {str(e)}")
            raise
    
    def callback_badcase(self, data_type: BadcaseType, data: Any = None):
        file_path = os.path.join(self.badcase_path, data_type)
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                content = json.load(f)
            except json.JSONDecodeError:
                content = []
        if isinstance(content, list):
            content.append(data)
        else:
            raise ValueError(f"The JSON root structure must be a List; please check the {file_path} file content.")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(content, f, ensure_ascii=False, indent=2)
        logger.info(f"Append {data_type} badcase data to {file_path} file.")


    def handle_error(self, error: Exception, fallback_text: str = "") -> dict:
        error_msg = f"{self.name} failed to execute: {str(error)}"
        logger.error(error_msg)
        return {"error": error_msg}
