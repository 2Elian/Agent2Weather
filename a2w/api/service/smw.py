from typing import List, Dict, Any
from a2w.utils import setup_logger
from a2w.smw.executors import WeatherReportWorkflow
from a2w.smw.agents import HistoryWeatherAgent, ForecastWeatherAgent, SuggestionAgent, SummaryAgent, BriefAgent
from a2w.smw.agents.state import WeatherReportState
from a2w.smw.managers.weather_classifier import WeatherClassifier
from a2w.api.core import BusinessError, DependencyError
from a2w.api.core.constants import BusinessErrorInformation

class SmwService:
    def __init__(self):
        self.logger = setup_logger("api.smw.service")
    @staticmethod
    async def execute_weather_report(request, workflow: WeatherReportWorkflow):
        user_input = {
            "task_type": request.task_type,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "station_names": request.station_names
        }
        agent_result = await workflow.run(user_input=user_input)
        return agent_result

    @staticmethod
    async def wr_history(request, workflow: HistoryWeatherAgent):
        metrics_data = await workflow.db.query_weather_metrics(
            regions=request.station_names,
            start_date=request.start_date,
            end_date=request.end_date
        )

        metrics = WeatherClassifier.parse_sql_result(metrics_data)  # List[Dict[str, Any]]
        analyst_result = WeatherClassifier.classify_stations(metrics)  # List[Dict[str, Any]]
        state = WeatherReportState(
            task_type="气象呈阅件",
            start_date=request.start_date,
            end_date=request.end_date,
            station_names=request.station_names,
            init_weather_data=analyst_result,
            history={},
            forecast={},
            suggestion={},
            summary={},
            final_brief={},
            error=None,
            tasks_completed={}
        )
        agent_result = await workflow.run(state)
        return agent_result.get("history")

    @staticmethod
    async def wr_forecast(request, workflow: ForecastWeatherAgent):
        state = WeatherReportState(
            task_type="气象呈阅件",
            start_date=request.start_date,
            end_date=request.end_date,
            station_names=request.station_names,
            init_weather_data=[],
            history={},
            forecast={},
            suggestion={},
            summary={},
            final_brief={},
            error=None,
            tasks_completed={}
        )
        agent_result = await workflow.run(state)
        return agent_result.get("forecast")

    @staticmethod
    async def wr_suggest(request, forecast_workflow: ForecastWeatherAgent, suggest_workflow: SuggestionAgent):
        state = WeatherReportState(
            task_type="气象呈阅件",
            start_date=request.start_date,
            end_date=request.end_date,
            station_names=request.station_names,
            init_weather_data=[],
            history={},
            forecast={},
            suggestion={},
            summary={},
            final_brief={},
            error=None,
            tasks_completed={}
        )
        if request.depends and not request.forecast:
            raise DependencyError(message=BusinessErrorInformation.DEPENDS_SUGGEST)
        if request.depends:
            state["forecast"]["response"] = request.forecast
        else:
            forecast_result = await forecast_workflow.run(state)
            state["forecast"] = forecast_result.get("forecast")
        agent_result = await suggest_workflow.run(state)
        return agent_result.get("suggestion")

    @staticmethod
    async def wr_summary(request, forecast_workflow: ForecastWeatherAgent, suggest_workflow: SuggestionAgent, summary_workflow: SummaryAgent):
        state = WeatherReportState(
            task_type="气象呈阅件",
            start_date=request.start_date,
            end_date=request.end_date,
            station_names=request.station_names,
            init_weather_data=[],
            history={},
            forecast={},
            suggestion={},
            summary={},
            final_brief={},
            error=None,
            tasks_completed={}
        )
        if request.depends and not request.forecast and not request.suggestion:
            raise DependencyError(message=BusinessErrorInformation.DEPENDS_SUMMARY)
        if request.depends:
            state["forecast"]["response"] = request.forecast
            state["suggestion"]["response"] = request.suggestion
        else:
            forecast_result = await forecast_workflow.run(state)
            state["forecast"] = forecast_result.get("forecast")
            suggestion_result = await suggest_workflow.run(state)
            state["suggestion"] = suggestion_result.get("suggestion")
        agent_result = await summary_workflow.run(state)
        return agent_result.get("summary")

    @staticmethod
    async def wr_brief(request, forecast_workflow: ForecastWeatherAgent,
                       suggest_workflow: SuggestionAgent,
                       summary_workflow: SummaryAgent,
                       brief_workflow: BriefAgent):
        state = WeatherReportState(
            task_type="气象呈阅件",
            start_date=request.start_date,
            end_date=request.end_date,
            station_names=request.station_names,
            init_weather_data=[],
            history={},
            forecast={},
            suggestion={},
            summary={},
            final_brief={},
            error=None,
            tasks_completed={}
        )
        if request.depends and not request.forecast and not request.suggestion and not request.suggestion:
            raise DependencyError(message=BusinessErrorInformation.DEPENDS_BRIEF)
        if request.depends:
            state["forecast"]["response"] = request.forecast
            state["suggestion"]["response"] = request.suggestion
            state["summary"]["response"] = request.summary
        else:
            forecast_result = await forecast_workflow.run(state)
            state["forecast"] = forecast_result.get("forecast")
            suggestion_result = await suggest_workflow.run(state)
            state["suggestion"] = suggestion_result.get("suggestion")
            summary_result = await summary_workflow.run(state)
            state["summary"] = summary_result.get("summary")
        agent_result = await brief_workflow.run(state)
        return agent_result.get("final_brief")