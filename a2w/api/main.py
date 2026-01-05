try:
    from contextlib import asynccontextmanager
except ImportError:
    from contextlib2 import asynccontextmanager # type: ignore

from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import sys
import signal

os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''
os.environ['http_proxy'] = ''
os.environ['https_proxy'] = ''
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from a2w.utils import setup_logger
from a2w.api.core.dependencies import get_config, get_factory, close_factory
from a2w.api.controller.smw_controller import smw_router
from a2w.api.middleware.exception.exception_handler import register_exception_handlers

logger = setup_logger("Agent-2-Weather")

@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    logger.info("🚀 Starting the A2W API service...")
    await get_factory()  # 异步初始化数据库和 LLM
    logger.info("✅ A2W API service started successfully")
    try:
        yield
    finally:
        await close_factory()
        logger.info("👋 The A2W API service is shut down")


def create_app() -> FastAPI:
    app = FastAPI(
        title="A2W API",
        description="Welcome to A2W (Agent-to-Weather for Yichun City)",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )
    config = get_config()
    app.add_middleware(
        CORSMiddleware,
        allow_origins="*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(smw_router, prefix=config.get("api_prefix"))

    @app.get("/", tags=["Root"])
    async def root():
        return {
            "message": "A2W API",
            "version": "1.0.0",
            "status": "running",
            "docs": "/docs"
        }

    @app.get("/health", tags=["Health"])
    async def health_check():
        config = get_config()
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "config_valid": config.validate()
        }

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    config = get_config()
    host = config.get("api_host", "0.0.0.0")
    port = int(config.get("api_port", 8001))

    def signal_handler(sig, frame):
        logger.info(f"Signal {sig} received, service is being shut down...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info(f"Start service: {host}:{port}")

    try:
        uvicorn.run(
            "a2w.api.main:app",
            host=host,
            port=port,
            reload=config.get("debug", False),
            log_level="info"
        )
    except KeyboardInterrupt:
        logger.info("Received Ctrl+C, service is shutting down...")
    except Exception as e:
        logger.error(f"Service exited abnormally: {str(e)}")
    finally:
        logger.info("Service is closed")