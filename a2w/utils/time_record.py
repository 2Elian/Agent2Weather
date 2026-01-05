import time
import asyncio
from functools import wraps
from typing import Callable, Any
from a2w.utils.logger import setup_logger

def time_recorder(func_name: str = None):
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            logger = setup_logger(name="TimeLogger")
            name = func_name if func_name else func.__name__
            try:
                result = await func(*args, **kwargs)
                elapsed = time.time() - start_time
                logger.info(f"Execution completed: \"{name}\", Time elapsed: \"{elapsed:.3f}\" seconds")
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(f"Execution failed: \"{name}\", Time elapsed: \"{elapsed:.3f}\" seconds --> Error: {e}")
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            logger = setup_logger(name="TimeLogger")
            
            name = func_name if func_name else func.__name__
            
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                logger.info(f"Execution completed: \"{name}\", Time elapsed: \"{elapsed:.3f}\" seconds")
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(f"Execution failed: \"{name}\", Time elapsed: \"{elapsed:.3f}\" seconds --> Error: {e}")
                raise
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator