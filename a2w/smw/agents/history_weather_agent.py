from dataclasses import asdict
from typing import Any, Dict, List, Set
import json
import os
from datetime import datetime, timedelta

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from a2w.configs.smw_config import SmwConfig
from a2w.smw.agents.base_agent import BaseAgent
from a2w.smw.funcalls import TOOLS
from a2w.utils.logger import setup_logger
from a2w.api.middleware.db.base_db import DBConnector
from a2w.smw.agents.state import WeatherReportState, StepStatus, BadcaseType
from a2w.smw.templates.weather_report import WR_PROMPT

# test environment
from a2w.smw.agents.pecw.tool_executor import ToolExecutor
from a2w.smw.utils.smw_util import parse_think_content, parse_json_util, normalize_subquery_params
from a2w.smw.agents.pecw import SubQueryOutput



class HistoryWeatherAgent(BaseAgent):
    def __init__(self, llm: ChatOpenAI, db_connector: DBConnector, config: SmwConfig = None):
        super().__init__(llm, name="HistoryWeatherAgent", config=config)
        self.db = db_connector
        self.logger = setup_logger(name=__class__.__name__)
        # TODO the path should write to .env file
        with open(self.config.get("smw_weather_classify_path"), "r", encoding="utf-8") as f:
            self.build_fixed_template = json.load(f)
    
    async def build_prompt(self) -> ChatPromptTemplate:
        prompt = ChatPromptTemplate.from_messages([
                ("system", WR_PROMPT["history"]["system"]),
                ('user', WR_PROMPT["history"]["user"])
            ])
        return prompt

    async def run(self, state: WeatherReportState) -> WeatherReportState:
        """
        Business Logic:
            思路是: 给现有的模板打上天气类型标签(业务上要不断迭代模板的标签信息), 然后做标签召回, 即省时间又不容易犯错. 内嵌badcase回调机制 不断收集正样本、负样本、硬副样本 为后续调embedding模型做数据准备
        """
        try:
            query_categories = [wt for item in state["init_weather_data"] for wt in item.get("weather_types", [])]
            if not query_categories:
                self.logger.warning("TODO: callback and record the badcase")
                raise ValueError("query_categories is empty")
            history_weather_template, match_score = self.recall_best_template(query_categories, self.build_fixed_template)
            if history_weather_template is None:
            # if history_weather_template is None or match_score==0.0:
                # TODO record data to badcase
                # TODO  badcase data type need to def a type class
                self.logger.warning("TODO: callback and record the badcase")
                badcase_data = {
                    "data": {
                        "base_information": {"task_type": state["task_type"], "station_names": state["station_names"], "start_date": state["start_date"], "end_date": state["end_date"]},
                        "recall_stage": "HistoryWeather",
                        "recall_template": history_weather_template.get("text_content"),
                        "recall_score": match_score
                    }
                }
                self.callback_badcase(data_type=BadcaseType.RECALL_TYPE, data=badcase_data)

            state["history"]["recall_template"] = history_weather_template.get("text_content")
            cntys = await self.db.query_cnty_by_regions(state["station_names"])
            user_query_to_pecw = {
                "start_date": state["start_date"],
                "end_date": state["end_date"],
                "cities": cntys,
                "weather_types": list(dict.fromkeys(query_categories))
            }
            available_tools_des = "\n".join([
            f"---\n函数名称：{tool.name}\n函数描述和参数形式：{tool.description}\n---\n"
            for tool in TOOLS
        ])
            plan_template = WR_PROMPT["history"]["pecw_history"].format(
                available_tools = available_tools_des,
                start_date=state["start_date"],
                end_date=state["end_date"],
                cities=cntys,
                weather_types=list(dict.fromkeys(query_categories)),
                template_analysis=state["history"]["recall_template"]
            )
            pecw_result = await self.pecw_agent.run(user_query=user_query_to_pecw,
                                                                        template=state["history"]["recall_template"],
                                                                          plan_template=plan_template)
            prompt = await self.build_prompt()
            weather_data = [asdict(sub_query_output) for sub_query_output in pecw_result.get("final_report")]
            llm_response = await self.call_llm(prompt, state, weather_data, user_query_to_pecw)
            think_text, history_report = parse_think_content(llm_response)
            state["history"]["response"] = history_report
            state["history"]["think_response"] = think_text
            state["history"]["status"] = StepStatus.SUCCESS
            state["history"]["sql_data"] = pecw_result
            state["history"]["error"] = None
            self.logger.info("-"*60)
            self.logger.info(f"《The History Weather》:\n {history_report}")
            self.logger.info("-"*60)
        except Exception as e:
            self.logger.error(f"The History Weather Generate Failed: {e}")
            state["history"]["status"] = StepStatus.FAILED
            state["history"]["response"] = ""
            state["history"]["think_response"] = ""
            state["history"]["error"] = e

        return state
    
    async def call_llm(self, prompt: ChatPromptTemplate, state: WeatherReportState, weather_data, user_query_to_pecw) -> str:
        try:
            chain = prompt | self.llm
            response = await chain.ainvoke({
                "weather_data": weather_data,
                "raw_information": user_query_to_pecw,
                "template": state["history"]["recall_template"]
            })
            return response.content
        except Exception:
            self.logger.exception("LLM call failed")
            raise

    def recall_best_template(self, query_categories: List[str], templates: List[Dict]):
        query_set = set(query_categories)

        best_score = 0.0
        best_template = None
        def weighted_jaccard(query_cats: Set[str],template_cats: Set[str]) -> float:
            if not query_cats and not template_cats:
                return 1.0
            if not query_cats or not template_cats:
                return 0.0
            return len(query_cats & template_cats) / len(query_cats | template_cats)
        
        for tpl in templates:
            tpl_set = set(tpl.get("weather_categories", []))
            score = weighted_jaccard(query_set, tpl_set)

            if score > best_score:
                best_score = score
                best_template = tpl

        return best_template, score