import time
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from a2w.smw.funcalls import TOOLS


@dataclass
class ExecutionResult:
    query_id: str
    status: str  # "success" | "failed"
    exe_data_result: Optional[Any] = None
    exe_message: Optional[str] = None
    exe_raw_count: Optional[int] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None


class ToolExecutor:
    def __init__(self, tool_registry):
        # name -> LangChain.StructuredTool
        self.tool_registry = tool_registry

    async def execute(self, sub_query: Dict[str, Any]) -> ExecutionResult:
        start_time = time.time()

        query_id = sub_query.get("id", "")
        tool_name = sub_query.get("tool")
        params = sub_query.get("params", {})

        try:
            if tool_name not in self.tool_registry:
                raise ValueError(f"Tool not found: {tool_name}")

            tool = self.tool_registry[tool_name]

            # LangChain's unified entry point: parameter validation + execution
            result = await tool.ainvoke(params)
            if result.get("status") == "success":
                return ExecutionResult(
                    query_id=query_id,
                    status="success",
                    exe_data_result=result.get("data"),
                    exe_message=result.get("message"),
                    exe_raw_count=result.get("row_count"),
                    error=None,
                    execution_time=time.time() - start_time
                )
            else:
                return ExecutionResult(
                    query_id=query_id,
                    status="failed",
                    exe_data_result=None,
                    exe_message=result.get("message"),
                    exe_raw_count=None,
                    error=result.get("message"),
                    execution_time=time.time() - start_time
                )

        except Exception as e:
                return ExecutionResult(
                    query_id=query_id,
                    status="failed",
                    exe_data_result=None,
                    exe_message=None,
                    exe_raw_count=None,
                    error=str(e),
                    execution_time=None
                )

    async def execute_batch(self, sub_queries: List[Dict[str, Any]]) -> List[ExecutionResult]:
        results = []
        for sub_query in sub_queries:
            results.append(await self.execute(sub_query))
        return results

    async def execute_batch_parallel(
        self,
        sub_queries: List[Dict[str, Any]]
    ) -> List[ExecutionResult]:
        tasks = [self.execute(q) for q in sub_queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        final_results = []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                final_results.append(
                    ExecutionResult(
                        query_id=sub_queries[i].get("id"),
                        exe_data_result=None,
                        exe_message=None,
                        exe_raw_count=None,
                        status="failed",
                        error=str(r)
                    )
                )
            else:
                final_results.append(r)

        return final_results
