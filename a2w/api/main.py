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
import asyncio

os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''
os.environ['http_proxy'] = ''
os.environ['https_proxy'] = ''
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from a2w.utils import setup_logger
from a2w.api.core.dependencies import init_dependencies, get_config
from a2w.api.controller import nl2sql_router
from a2w.api.middleware.exception.exception_handler import register_exception_handlers

logger = setup_logger("api", log_file="logs/api.log")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting the A2W API service...")
    init_dependencies()
    logger.info("✅ A2W API service started successfully") 
    yield
    logger.info("👋 The A2W API service is being shut down...")


def create_app() -> FastAPI:
    app = FastAPI(
        title="A2W API",
        description="Wecomle to A2W(Agent-to-Weather to Yichun City)",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )
    config = get_config()
    origins = config.get("cors_origins", "*").split(",") if config.get("cors_origins") else ["*"]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)
    app.include_router(nl2sql_router, prefix="/api/v1")
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
    port = int(config.get("api_port", 9023))
    def signal_handler(sig, frame):
        logger.info(f"Signal {sig} received, service is being shut down...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    logger.info(f"Start service: {host}:{port}")
    try:
        uvicorn.run(
            "a2sql.api.main:app",
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
