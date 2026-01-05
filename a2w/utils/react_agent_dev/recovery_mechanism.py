import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class RecoveryAction(Enum):
    RETRY = "retry"
    SKIP = "skip"


@dataclass
class RecoveryOutput:
    query_id: str
    error_information: str
    query_information: Dict[str, Any]
    action: RecoveryAction
    reason: str
    retry_count: int = 0
    max_retries: int = 3


class RecoveryMechanism:
    def __init__(self, available_tools: Dict[str, Any]):
        self.available_tools = available_tools
    
    def validate_execution_results(self, execution_results: List[Dict[str, Any]], original_plan: Dict[str, Any]) -> List[RecoveryOutput]:
        recovery_result: List[RecoveryOutput] = []
        try:
            for result in execution_results:
                query_id = result.get("query_id")
                query_des = RecoveryMechanism.get_sub_query_by_id(original_plan, query_id)
                assert query_des is not None, f"sub_query -> {query_id} -> {query_des} is None"
                if result.get("status") == "failed":
                    error = result.get("error")
                    assert error is not None, f"the {query_id} get a status=failed, but it's error is None."
                    recovery_result.append(
                        RecoveryOutput(
                            query_id=query_id,
                            error_information=error,
                            query_information=query_des,
                            action=RecoveryAction.RETRY,
                            reason="工具执行出错"
                        )
                    )

                elif result.get("status") == "success" and result.get("exe_data_result") is None: # the result.get("exe_data_result") is None equivalent to result.get("exe_row_count")==0
                    error = result.get("error")
                    assert error is not None, f"the {query_id} get a status=failed, but it's error is None."
                    recovery_result.append(
                        RecoveryOutput(
                            query_id=query_id,
                            error_information=error,
                            query_information=query_des,
                            action=RecoveryAction.RETRY,
                            reason="工具执行成功，但得到的数据结果为空"
                        )
                    )
            return recovery_result

        except Exception as e:
            raise

    @classmethod
    def get_sub_query_by_id(plan_dict: Dict[str, Any], query_id: str) -> Dict[str, Any] | None:
        for sq in plan_dict.get("sub_queries", []):
            if sq.get("id") == query_id:
                return sq
        return None

