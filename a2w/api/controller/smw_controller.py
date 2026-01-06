from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query

from a2w.api.model import SmwRequest, SmwResponse
from a2w.utils import setup_logger
from a2w.api.service import SmwService
from a2w.smw.executors import WeatherReportWorkflow
from a2w.smw.agents import (
    HistoryWeatherAgent,
    ForecastWeatherAgent,
    SuggestionAgent,
    SummaryAgent,
    BriefAgent,
    )
from a2w.api.core.dependencies import (
    get_wr_async,
    get_wr_history_async,
    get_wr_forecast_async,
    get_wr_suggest_async,
    get_wr_summary_async,
    get_wr_brief_async,
    )

logger = setup_logger("api.routes.smw")
smw_router = APIRouter(prefix="/smw", tags=["SMW"])

# 气象呈阅件接口如下
@smw_router.post("/WeatherReport", response_model=SmwResponse, summary="气象呈阅件服务总接口")
async def execute_weather_report(request: SmwRequest, workflow: WeatherReportWorkflow = Depends(get_wr_async),) -> SmwResponse:
    try:
        result = await SmwService.execute_weather_report(
            request=request,
            workflow = workflow
        )
        return SmwResponse(
            status=result.status,
            data=result.data,
            error=result.error,
            metadata=result.meta_data
        )
    except Exception as e:
        import traceback
        error_detail = f"{type(e).__name__}: {str(e)}"
        logger.error(f"Execution failed: {error_detail}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=error_detail)

@smw_router.post("/WrHistory", response_model=SmwResponse, summary="气象呈阅件服务-前期实况单接口")
async def ReTryWrHistory(request: SmwRequest, workflow: HistoryWeatherAgent = Depends(get_wr_history_async),) -> SmwResponse:
    try:
        result = await SmwService.wr_history(
            request=request,
            workflow = workflow
        )
        data = {"history": result.get("response")}
        meta_data = {"think_content": result.get("think_response"), "sql_data": result.get("sql_data"), "recall_template": result.get("recall_template")}
        return SmwResponse(
            status=result.get("status"),
            data=data,
            error=result.get("error"),
            metadata=meta_data
        )
    except Exception as e:
        import traceback
        error_detail = f"{type(e).__name__}: {str(e)}"
        logger.error(f"Execution failed: {error_detail}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=error_detail)

@smw_router.post("/WrForecast", response_model=SmwResponse, summary="气象呈阅件服务-实况天气单接口")
async def ReTryWrForecast(request: SmwRequest, workflow: ForecastWeatherAgent = Depends(get_wr_forecast_async),) -> SmwResponse:
    try:
        result = await SmwService.wr_forecast(
            request=request,
            workflow = workflow
        )
        data = {"forecast": result.get("response")}
        meta_data = {"think_content": result.get("think_response"), "sql_data": result.get("sql_data"), "recall_template": result.get("recall_template")}
        return SmwResponse(
            status=result.get("status"),
            data=data,
            error=result.get("error"),
            metadata=meta_data
        )
    except Exception as e:
        import traceback
        error_detail = f"{type(e).__name__}: {str(e)}"
        logger.error(f"Execution failed: {error_detail}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=error_detail)

@smw_router.post("/WrSuggest", response_model=SmwResponse, summary="气象呈阅件服务-关注与建议单接口")
async def ReTryWrSuggest(request: SmwRequest,
                          forecast_workflow: ForecastWeatherAgent = Depends(get_wr_forecast_async),
                          suggest_workflow: SuggestionAgent = Depends(get_wr_suggest_async),) -> SmwResponse:
    try:
        result = await SmwService.wr_suggest(
            request=request,
            forecast_workflow = forecast_workflow,
            suggest_workflow=suggest_workflow
        )
        data = {"suggestion": result.get("response")}
        meta_data = {"think_content": result.get("think_response"), "sql_data": result.get("sql_data"), "recall_template": result.get("recall_template")}
        return SmwResponse(
            status=result.get("status"),
            data=data,
            error=result.get("error"),
            metadata=meta_data
        )
    except Exception as e:
        import traceback
        error_detail = f"{type(e).__name__}: {str(e)}"
        logger.error(f"Execution failed: {error_detail}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=error_detail)

@smw_router.post("/WrSummary", response_model=SmwResponse, summary="气象呈阅件服务-摘要单接口")
async def ReTryWrSummary(request: SmwRequest,
                          forecast_workflow: ForecastWeatherAgent = Depends(get_wr_forecast_async),
                          suggest_workflow: SuggestionAgent = Depends(get_wr_suggest_async),
                          summary_workflow: SummaryAgent = Depends(get_wr_summary_async),) -> SmwResponse:
    try:
        result = await SmwService.wr_summary(
            request=request,
            forecast_workflow = forecast_workflow,
            suggest_workflow=suggest_workflow,
            summary_workflow=summary_workflow
        )
        data = {"summary": result.get("response")}
        meta_data = {"think_content": result.get("think_response"), "sql_data": result.get("sql_data"), "recall_template": result.get("recall_template")}
        return SmwResponse(
            status=result.get("status"),
            data=data,
            error=result.get("error"),
            metadata=meta_data
        )
    except Exception as e:
        import traceback
        error_detail = f"{type(e).__name__}: {str(e)}"
        logger.error(f"Execution failed: {error_detail}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=error_detail)

@smw_router.post("/WrBrief", response_model=SmwResponse, summary="气象呈阅件服务-标题单接口")
async def ReTryWrBrief(request: SmwRequest,
                          forecast_workflow: ForecastWeatherAgent = Depends(get_wr_forecast_async),
                          suggest_workflow: SuggestionAgent = Depends(get_wr_suggest_async),
                          summary_workflow: SummaryAgent = Depends(get_wr_summary_async),
                          brief_workflow: BriefAgent = Depends(get_wr_brief_async)) -> SmwResponse:
    try:
        result = await SmwService.wr_brief(
            request=request,
            forecast_workflow = forecast_workflow,
            suggest_workflow=suggest_workflow,
            summary_workflow=summary_workflow,
            brief_workflow=brief_workflow
        )
        data = {"final_brief": result.get("response")}
        meta_data = {"think_content": result.get("think_response"), "sql_data": result.get("sql_data"), "recall_template": result.get("recall_template")}
        return SmwResponse(
            status=result.get("status"),
            data=data,
            error=result.get("error"),
            metadata=meta_data
        )
    except Exception as e:
        import traceback
        error_detail = f"{type(e).__name__}: {str(e)}"
        logger.error(f"Execution failed: {error_detail}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=error_detail)


