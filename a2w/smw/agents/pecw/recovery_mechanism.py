import ast
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from a2w.smw.funcalls import TOOLS
from a2w.smw.templates.common import COMMON_PROMPT
from a2w.smw.utils.smw_util import normalize_subquery_params_single, parse_think_content
from a2w.smw.agents.pecw.data_planner import SubQuery, QueryPlan


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
    def __init__(self, available_tools: Dict[str, Any], llm: ChatOpenAI):
        self.available_tools = available_tools
        self.llm = llm
    
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
                    # assert error is not None, f"the {query_id} get a status=failed, but it's error is None."
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

    @staticmethod
    def get_sub_query_by_id(plan_dict: Dict[str, Any], query_id: str) -> Dict[str, Any] | None:
        for sq in plan_dict.get("sub_queries", []):
            if sq.get("id") == query_id:
                return sq
        return None

    def get_is_solvable(self, current_recovery_item: RecoveryOutput) -> bool:
        prompt = ChatPromptTemplate.from_messages([
                ("system", COMMON_PROMPT["is_solve"]["system"]),
                ('user', COMMON_PROMPT["is_solve"]["user"])
            ])
        available_tools_des = "\n".join([
        f"---\n函数名称：{tool.name}\n函数描述和参数形式：{tool.description}\n---\n"
        for tool in TOOLS
        ])
        query_information = current_recovery_item.query_information
        error_information = current_recovery_item.reason
        purpose = query_information.get("purpose")
        current_tool = query_information.get("tool")
        current_params = query_information.get("params")
        current_func_des = self.available_tools.get(current_tool).description

        chain = prompt | self.llm
        llm_response = chain.invoke({
            "available_tools": available_tools_des,
            "purpose": purpose,
            "func_name": current_tool,
            "params": current_params,
            "func_des": current_func_des,
            "error_information": error_information
        })
        think_text, context_part = parse_think_content(llm_response.content)
        result = context_part.strip().upper()

        if result not in ("YES", "NO"):
            raise ValueError(f"Invalid solvable judgment: {context_part}")

        return result == "YES"


    def generate_retry_result(self, current_recovery_item: RecoveryOutput, query_plan: QueryPlan) -> SubQuery:
        prompt = ChatPromptTemplate.from_messages([
                ("system", COMMON_PROMPT["retry"]["system"]),
                ('user', COMMON_PROMPT["retry"]["user"])
            ])
        available_tools_des = "\n".join([
        f"---\n函数名称：{tool.name}\n函数描述和参数形式：{tool.description}\n---\n"
        for tool in TOOLS
        ])
        query_information = current_recovery_item.query_information
        error_information = current_recovery_item.reason
        purpose = query_information.get("purpose")
        current_tool = query_information.get("tool")
        current_params = query_information.get("params")
        current_func_des = self.available_tools.get(current_tool).description
        start_date = query_plan.meta.get("start_date")
        end_date = query_plan.meta.get("end_date")
        cnty = query_plan.meta.get("cities")
        weather_types = query_plan.meta.get("weather_types")
        chain = prompt | self.llm
        llm_response = chain.invoke({
            "available_tools": available_tools_des,
            "start_date": start_date,
            "end_date": end_date,
            "cnty": cnty,
            "weather_types": weather_types,
            "purpose": purpose,
            "func_name": current_tool,
            "params": current_params,
            "func_des": current_func_des,
            "error_information": error_information
        })
        think_text, context_part = parse_think_content(llm_response.content)
        obj = normalize_subquery_params_single(json.loads(context_part))

        return SubQuery(
            id=current_recovery_item.query_id,
            purpose=purpose,
            tool=obj.get("tool"),
            params=obj.get("params"),
            expected_fields=query_information.get("expected_fields")
        )