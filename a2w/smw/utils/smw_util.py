import asyncio
import functools
import json
import logging
import re
import sys
import time
from typing import Callable, List, Tuple, Dict, Any
import ast

def parse_think_content(content: str) -> Tuple[str, Dict[str, Any]]:
    think_match = re.search(r"<think>\s*(.*?)\s*</think>", content, re.DOTALL)
    think_text = think_match.group(1).strip() if think_match else ""
    context_part = content.split("</think>")[-1].strip()
    return think_text, context_part

def parse_json_util(json_str: str) -> List[Dict[str, Any]]:
    json_match = re.search(r'```json\s*([\s\S]*?)\s*```', json_str)
    if json_match:
        json_str = json_match.group(1)
    else:
        start_idx = json_str.find('[')
        end_idx = json_str.rfind(']')
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_str = json_str[start_idx:end_idx+1]
    if not json_str:
        raise ValueError("未能在响应中找到JSON数据")
    
    try:
        query_tasks = json.loads(json_str)
        if not isinstance(query_tasks, list):
            raise ValueError("解析结果不是列表类型")
        
        return query_tasks
        
    except json.JSONDecodeError as e:
        raise e
    
def normalize_subquery_params(sub_queries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Normalize params in sub_queries:
    - Ensure list-type params are real lists, not stringified lists
    - Only touch `params`
    - Safe for LLM-generated plans
    """

    normalized_sub_queries = []

    for sq in sub_queries:
        sq = dict(sq)  # shallow copy
        params = sq.get("params", {})

        if not isinstance(params, dict):
            sq["params"] = params
            normalized_sub_queries.append(sq)
            continue

        normalized_params = {}
        for k, v in params.items():
            # Case 1: already list
            if isinstance(v, list):
                normalized_params[k] = v
                continue

            # Case 2: stringified list → try recover
            if isinstance(v, str):
                v_strip = v.strip()
                if v_strip.startswith("[") and v_strip.endswith("]"):
                    try:
                        parsed = ast.literal_eval(v_strip)
                        if isinstance(parsed, list):
                            normalized_params[k] = parsed
                            continue
                    except Exception:
                        pass

            # Case 3: keep original
            normalized_params[k] = v

        sq["params"] = normalized_params
        normalized_sub_queries.append(sq)

    return normalized_sub_queries

def normalize_subquery_params_single(sub_query: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize params in a single sub_query:
    - Ensure list-type params are real lists, not stringified lists
    - Only touch `params`
    - Safe for LLM-generated plans
    """

    sq = dict(sub_query)  # shallow copy
    params = sq.get("params", {})

    if not isinstance(params, dict):
        sq["params"] = params
        return sq

    normalized_params = {}

    for k, v in params.items():
        # Case 1: already a list
        if isinstance(v, list):
            normalized_params[k] = v
            continue

        # Case 2: stringified list -> try to recover
        if isinstance(v, str):
            v_strip = v.strip()
            if v_strip.startswith("[") and v_strip.endswith("]"):
                try:
                    parsed = ast.literal_eval(v_strip)
                    if isinstance(parsed, list):
                        normalized_params[k] = parsed
                        continue
                except Exception:
                    pass

        # Case 3: keep original
        normalized_params[k] = v

    sq["params"] = normalized_params
    return sq

def remove_huoqu(text: str) -> str:
    """
    Remove all occurrences of the word "获取" from the input string.
    """
    return text.replace("获取", "")

def get_logger(name: str = "app_logger",
               level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.propagate = False

    return logger

BLUE = "\033[94m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"

def log_execution_time(
    func_name: str = None,
    logger_name: str = None,
    log_state: bool = True
):
    """
    装饰器：记录函数执行前后状态与耗时，并带彩色日志输出。
    
    参数：
        func_name: 日志显示名称（默认=函数名）
        logger_name: logger 名称（默认=函数名）
        log_state: 是否打印执行结束后的 state（默认 True）
    """
    def decorator(func: Callable):
        log = get_logger(logger_name or func_name or func.__name__)

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            display_name = func_name or func.__name__
            log.info(f"{BLUE}[{display_name}] Starting...{RESET}")

            start_time = time.perf_counter()
            result = None
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                elapsed = time.perf_counter() - start_time
                log.info(f"{YELLOW}[{display_name}] Return Value:\n{result}{RESET}")
                log.info(f"{RED}[{display_name}] End --> Time: {elapsed:.4f}s{RESET}")

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            display_name = func_name or func.__name__
            log.info(f"{BLUE}[{display_name}] Starting...{RESET}")

            start_time = time.perf_counter()
            result = None
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                elapsed = time.perf_counter() - start_time
                log.info(f"{YELLOW}[{display_name}] Return Value:\n{result}{RESET}")
                log.info(f"{RED}[{display_name}] End --> Time: {elapsed:.4f}s{RESET}")

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator

if __name__ == "__main__":
    json_str = """
    {
        "data": "error",
        "params": "[\\"1\\", \\"2\\"]"
    }
    """
    res = normalize_subquery_params_single(json.loads(json_str))
    print(res)