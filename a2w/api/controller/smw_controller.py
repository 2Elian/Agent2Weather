from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query

from a2w.api.model import SmwRequest, SmwResponse
from a2w.utils import setup_logger
from a2w.api.service import SmwService
from a2w.smw.executors import WeatherReportWorkflow
from a2w.api.core.dependencies import get_wr_async, get_pwr_async, get_config

logger = setup_logger("api.routes.smw")
router = APIRouter(prefix="/smw", tags=["SMW"])

@router.post("/WeatherReport", response_model=SmwResponse, summary="气象呈阅件服务接口")
async def execute_nl2sql(request: SmwRequest, workflow: WeatherReportWorkflow = Depends(get_wr_async),) -> SmwResponse:
    try:
        result = await SmwService.execute_weather_report(
            request=request,
            workflow = workflow
        )
        
        # TODO 返回值可能不对
        return SmwResponse(
            status=result.status.value,
            data={"result": result.data} if result.is_success() else None,
            error=result.error,
            metadata=result.metadata
        )
    except Exception as e:
        import traceback
        error_detail = f"{type(e).__name__}: {str(e)}"
        logger.error(f"Execution failed: {error_detail}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=error_detail)
