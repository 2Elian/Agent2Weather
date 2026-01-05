from typing import Any, Dict, List
from datetime import datetime
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END, CompiledStateGraph

from a2w.configs.smw_config import SmwConfig
from a2w.smw.agents.state import WeatherReportState, StepStatus, SmwReturn
from a2w.smw.managers.weather_classifier import WeatherClassifier, WeatherMetrics
from a2w.smw.agents.history_weather_agent import HistoryWeatherAgent
from a2w.smw.agents.forecast_weather_agent import ForecastWeatherAgent
from a2w.smw.agents.suggestion_agent import SuggestionAgent
from a2w.smw.agents.summary_agent import SummaryAgent
from a2w.smw.agents.brief_agent import BriefAgent
from a2w.api.middleware.db.base_db import DBConnector
from a2w.smw.managers.embedding_recall import EmbeddingRecallManager
from a2w.utils.logger import setup_logger

class WeatherReportWorkflow:
    def __init__(self, llm: ChatOpenAI, db_connector: DBConnector, config: SmwConfig = None):
        self.llm = llm
        self.db = db_connector
        self.embedding_recall_mgr = EmbeddingRecallManager()
        self.history_agent = HistoryWeatherAgent(llm, self.db, config)
        self.forecast_agent = ForecastWeatherAgent(llm, self.db, config)
        self.suggestion_agent = SuggestionAgent(llm, self.embedding_recall_mgr, config)
        self.summary_agent = SummaryAgent(llm, self.embedding_recall_mgr, config)
        self.brief_agent = BriefAgent(llm, config)
        self.graph = self._build_graph()
        self.logger = setup_logger(name=__class__.__name__)
    
    def _build_graph(self):
        workflow = StateGraph(WeatherReportState)
        
        workflow.add_node("input", self.input_node)
        workflow.add_node("weather_type_judge", self.weather_type_judge_node)
        workflow.add_node("history_weather", self.history_weather_node)
        workflow.add_node("forecast_weather", self.forecast_weather_node)
        workflow.add_node("wait_weather_data", self.wait_weather_data_node)  # wait node
        workflow.add_node("suggestion", self.suggestion_node)
        workflow.add_node("summary", self.summary_node)
        workflow.add_node("wait_analysis", self.wait_analysis_node)  # wait node
        workflow.add_node("final_brief", self.final_brief_node)

        workflow.set_entry_point("input")
        workflow.add_edge("input", "weather_type_judge")

        workflow.add_edge("weather_type_judge", "history_weather")
        workflow.add_edge("weather_type_judge", "forecast_weather")

        workflow.add_edge("history_weather", "wait_analysis")
        workflow.add_edge("forecast_weather", "wait_weather_data")

        workflow.add_conditional_edges(
            "wait_weather_data",
            self.route_after_wait_forecast,
            {
                "continue": "suggestion",
                "wait": "wait_weather_data"
            }
        )

        workflow.add_edge("suggestion", "summary")
        workflow.add_edge("summary", "wait_analysis")

        workflow.add_conditional_edges(
            "wait_analysis",
            self.route_after_wait_all_task,
            {
                "continue": "final_brief",
                "wait": "wait_analysis"
            }
        )
        workflow.add_edge("final_brief", END)
        
        return workflow.compile()
    
    async def input_node(self, state: WeatherReportState) -> Dict:
        self.logger.info(f"开始处理任务:《{state['task_type']}》, 站点信息: {state['station_names']}, "
                   f"时间: {state['start_date']} ~ {state['end_date']}")
        required_fields = ["task_type", "start_date", "end_date", "station_names"]
        for field in required_fields:
            if not state.get(field):
                error_msg = f"缺少必填字段: {field}"
                self.logger.error(error_msg)
                return {"error": error_msg}
        return {}
    
    async def weather_type_judge_node(self, state: WeatherReportState) -> List[Dict[str, Any]]:
        try:
            # 用日表判断天气类型
            self.logger.info("开始天气类型判断")
            metrics_data = await self.db.query_weather_metrics(
                regions=state["station_names"],
                start_date=state["start_date"],
                end_date=state["end_date"]
            )

            metrics = WeatherClassifier.parse_sql_result(metrics_data) # List[Dict[str, Any]]
            analyst_result = WeatherClassifier.classify_stations(metrics) # List[Dict[str, Any]]
            self.logger.info(f"初步判断的天气数据: {analyst_result}")
            state["init_weather_data"] = analyst_result
            
        except Exception as e:
            self.logger.error(f"天气类型判断失败: {e}")
            raise
        return state
    
    async def history_weather_node(self, state: WeatherReportState) -> Dict:
        self.logger.info("开始生成前期天气实况")
        return await self.history_agent.run(state)
    
    async def forecast_weather_node(self, state: WeatherReportState) -> Dict:
        self.logger.info("开始生成详细天气预报")
        return await self.forecast_agent.run(state)
    
    async def wait_weather_data_node(self, state: WeatherReportState) -> Dict:
        tasks_completed = state.get("tasks_completed", {})
        has_forecast = bool(state["forecast"].get("response"))
        
        if has_forecast:
            tasks_completed["forecast_ready"] = True
            self.logger.info("详细天气预报已完成")
        else:
            self.logger.info("等待详细天气预报完成ing...")
        state["tasks_completed"] = tasks_completed
        return state
    
    async def suggestion_node(self, state: WeatherReportState) -> Dict:
        self.logger.info("开始生成关注建议")
        return await self.suggestion_agent.run(state)
    
    async def summary_node(self, state: WeatherReportState) -> Dict:
        self.logger.info("开始生成摘要")
        return await self.summary_agent.run(state)
    
    async def wait_analysis_node(self, state: WeatherReportState) -> Dict:
        tasks_completed = state.get("tasks_completed", {})
        has_forecast = bool(state["forecast"].get("response")) and\
                    bool(state["history"].get("response")) and\
                    bool(state["suggestion"].get("response")) and\
                    bool(state["summary"].get("response")) and\
                    bool(state["final_brief"].get("response"))
        
        if has_forecast:
            tasks_completed["all_tasks_ready"] = True
            self.logger.info("所有任务已完成")
        else:
            self.logger.info("等待所有任务完成ing...")
        state["tasks_completed"] = tasks_completed
        return state
    
    
    async def final_brief_node(self, state: WeatherReportState) -> Dict:
        self.logger.info("开始生成简短提示")
        return await self.brief_agent.run(state)

    def route_after_wait_forecast(self, state: WeatherReportState) -> str:
        tasks_completed = state.get("tasks_completed", {})
        if tasks_completed.get("forecast_ready", False):
            return "continue"
        else:
            return "wait"

    def route_after_wait_all_task(self, state: WeatherReportState) -> str:
        tasks_completed = state.get("tasks_completed", {})
        if tasks_completed.get("all_tasks_ready", False):
            return "continue"
        else:
            return "wait"
    
    async def run(self, user_input: Dict) -> SmwReturn:
        start_time = datetime.now()
        self.logger.info("-" * 60)
        self.logger.info(f"任务：{user_input["task_type"]} -> 开始执行: {start_time}")

        initial_state = WeatherReportState(
            task_type=user_input["task_type"],
            start_date=user_input["start_date"],
            end_date=user_input["end_date"],
            station_names=user_input["station_names"],
            init_weather_data=[],
            history={},
            forecast={},
            suggestion={},
            summary={},
            final_brief={},
            error=None,
            tasks_completed={}
        )
        
        try:
            final_state = await self.graph.ainvoke(initial_state)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            self.logger.info(f"任务：{user_input["task_type"]} 执行完成, 耗时: {duration:.2f}秒")
            self.logger.info("-" * 60)

            return SmwReturn(
                status=StepStatus.SUCCESS,
                data={
                    "history_text": final_state.get("history_text", ""),
                    "forecast_text": final_state.get("forecast_text", ""),
                    "suggestion_text": final_state.get("suggestion_text", ""),
                    "summary_text": final_state.get("summary_text", ""),
                    "final_brief": final_state.get("final_brief", "")
                },
                meta_data=
                {
                    "duration": f"{duration:.2f}s",
                    "all_state": final_state
                }
            )
            
        except Exception as e:
            self.logger.error(f"工作流执行失败: {e}")
            return SmwReturn(
                status=StepStatus.FAILED,
                error=e,
                meta_data=
                {
                    "duration": f"{duration:.2f}s",
                    "all_state": final_state
                },
            )
