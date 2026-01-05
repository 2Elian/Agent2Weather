import json
import re
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

from langchain_openai.chat_models.base import BaseChatOpenAI

from a2w.smw.utils.smw_util import parse_think_content, parse_json_util, normalize_subquery_params


class QueryStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    REVISED = "revised"


@dataclass
class SubQuery:
    id: str
    purpose: str
    tool: str
    params: Dict[str, Any]
    expected_fields: List[str]


@dataclass
class QueryPlan:
    meta: Dict[str, Any]
    sub_queries: List[SubQuery]
    llm_response_meta: Dict[str, Any]
    status: QueryStatus = QueryStatus.PENDING


class DataPlanner:
    def __init__(self, llm: BaseChatOpenAI):
        self.llm = llm
    
    async def plan(self, query_meta: Dict[str, Any], plan_prompt: str) -> QueryPlan:
        # TODO 需要try 和except 然后动态以下status的枚举
        response = await self._generate_sub_queries(plan_prompt)
        think_text, context_part = parse_think_content(response.content)
        sub_queries = self.params_validation(normalize_subquery_params(parse_json_util(context_part)))
        llm_response_meta = {
            "think_content": think_text,
            "token_status": response.response_metadata,
        }
        plan = QueryPlan(meta=query_meta, sub_queries=sub_queries, status=QueryStatus.SUCCESS, llm_response_meta=llm_response_meta)
        return plan
    
    async def _generate_sub_queries(self, plan_prompt: str) -> List[SubQuery]:
        # LOOP Module NotImplement --> V2解决
        messages = [
            (
                "system",
                "You are a helpful translator. Translate the user sentence to French.",
            ),
            ("human", plan_prompt),
        ]
        result = await self.llm.ainvoke(messages)
        return result
    
    def params_validation(self, sub_queries: List[Dict[str, Any]]) -> List[SubQuery]:
        validated_queries = []
        for sq in sub_queries:
            required_keys = ["purpose", "tool", "params", "expected_fields"]
            for key in required_keys:
                if key not in sq:
                    raise ValueError(f"The subquery is missing the required field: {key}, and the subquery content is: {sq}.")
            if not isinstance(sq["params"], dict):
                raise ValueError(f"The subquery `params` must be a dictionary, and the subquery content is: `{sq}`.")
            if not isinstance(sq["expected_fields"], list):
                raise ValueError(f"The subquery `expected_fields` must be a list, and the subquery content is: {sq}")
            subquery_obj = SubQuery(
                id=str(uuid.uuid4()),
                purpose=sq["purpose"],
                tool=sq["tool"],
                params=sq["params"],
                expected_fields=sq["expected_fields"]
            )

            validated_queries.append(subquery_obj)

        return validated_queries