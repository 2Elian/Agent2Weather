from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query

from a2w.api.model import SmwRequest, SmwResponse
from a2w.utils import setup_logger
from a2w.api.service import SmwService
from a2w.smw.executors import WeatherReportWorkflow
from a2w.api.core.dependencies import get_wr_async

logger = setup_logger("api.routes.smw")
smw_router = APIRouter(prefix="/smw", tags=["SMW"])

@smw_router.post("/WeatherReport", response_model=SmwResponse, summary="气象呈阅件服务接口")
async def execute_nl2sql(request: SmwRequest, workflow: WeatherReportWorkflow = Depends(get_wr_async),) -> SmwResponse:
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
