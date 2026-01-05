import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

from langgraph.graph import StateGraph, END
from langchain_openai.chat_models.base import BaseChatOpenAI

from a2w.smw.funcalls import TOOLS
from a2w.utils.logger import setup_logger
from a2w.smw.utils.smw_util import log_execution_time
from .data_planner import DataPlanner, QueryPlan
from .tool_executor import ToolExecutor, ExecutionResult
from .recovery_mechanism import RecoveryMechanism, RecoveryOutput
from a2w.smw.utils.smw_util import remove_huoqu


class WorkflowState(Enum):
    QUERY_NORMALIZATION = "query_normalization"
    DATA_PLANNING = "data_planning"
    TOOL_EXECUTION = "tool_execution"
    VALIDATION = "validation"
    RECOVERY = "recovery"
    PROCESS_SINGLE_RECOVERY = "process_single_recovery"
    REPORT_GENERATION = "report_generation"
    COMPLETED = "completed"


@dataclass
class AgentState:
    user_query: Dict[str, Any]
    template: str
    plan_template: str
    normalized_query: Optional[Dict[str, Any]] = None
    query_plan: Optional[QueryPlan] = None
    execution_results: Optional[List[ExecutionResult]] = None
    recovery_queue: Optional[List[RecoveryOutput]] = None
    final_report: Optional[str] = None
    current_state: WorkflowState = WorkflowState.QUERY_NORMALIZATION
    retry_count: int = 0
    max_retries: int = 3

@dataclass
class SubQueryOutput:
    purpose: str
    exe_data_result: Optional[Any] = None

class PECWAgent:
    # init to BaseAgent
    def __init__(self, llm: BaseChatOpenAI, tool_registry: Dict[str, Any] = None):
        self.tool_registry = {tool.name: tool for tool in TOOLS}
        self.data_planner = DataPlanner(llm)
        self.tool_executor = ToolExecutor(self.tool_registry)
        self.recovery_mechanism = RecoveryMechanism(available_tools=tool_registry, llm=llm)
        self.workflow_graph = self._build_workflow()
        self.logger = setup_logger(name=__class__.__name__)
    
    def _build_workflow(self) -> StateGraph:
        workflow = StateGraph(AgentState)

        workflow.add_node("normalize_query", self._normalize_query_node)
        workflow.add_node("plan_data", self._plan_data_node)
        workflow.add_node("execute_tools", self._execute_tools_node)
        workflow.add_node("validate_results", self._validate_results_node)
        workflow.add_node("recovery_action", self._recovery_action_node)
        workflow.add_node("organize_data", self._organize_data_node)

        workflow.add_edge("normalize_query", "plan_data")
        workflow.add_edge("plan_data", "execute_tools")
        workflow.add_edge("execute_tools", "validate_results")
        
        workflow.add_conditional_edges(
            "validate_results",
            self._route_after_validation,
            {
                "recovery": "recovery_action",
                "end": "organize_data"
            }
        )
        
        workflow.add_edge("recovery_action", "execute_tools")
        workflow.set_entry_point("normalize_query")
        
        return workflow.compile()
    
    async def _normalize_query_node(self, state: AgentState) -> Dict[str, Any]:
        normalized = {
            "start_date": state.user_query.get("start_date"),
            "end_date": state.user_query.get("end_date"),
            "cities": state.user_query.get("cities", []),
            "weather_types": state.user_query.get("weather_types", [])
        }
        return {
            "normalized_query": normalized,
            "current_state": WorkflowState.DATA_PLANNING
        }
    @log_execution_time(func_name="PlanDataNode")
    async def _plan_data_node(self, state: AgentState) -> Dict[str, Any]:
        plan = await self.data_planner.plan(state.normalized_query, state.plan_template)
        return {
            "query_plan": plan,
            "current_state": WorkflowState.TOOL_EXECUTION
        }
    
    @log_execution_time(func_name="ExecuteToolsNode")
    async def _execute_tools_node(self, state: AgentState) -> Dict[str, Any]:
        if state.recovery_queue and len(state.recovery_queue) > 0:
            # get first queue of the recovery queue 
            current_recovery_item = state.recovery_queue[0]
            target_sub_query = None
            if state.query_plan and state.query_plan.sub_queries:
                for sub_query in state.query_plan.sub_queries:
                    if sub_query.id == current_recovery_item.query_id:
                        target_sub_query = asdict(sub_query)
                        break
            result = None
            if target_sub_query:
                result = self.tool_executor.execute(target_sub_query)
                new_execution_results = []
                if state.execution_results:
                    # Refactor execution_results: New overwrites old, no change
                    for existing_result in state.execution_results:
                        if existing_result.query_id != current_recovery_item.query_id:
                            new_execution_results.append(existing_result)
                    new_execution_results.append(result)
                else:
                    raise
                if result.status == "success":
                    new_recovery_queue = state.recovery_queue[1:]
                    return {
                        "execution_results": new_execution_results,
                        "recovery_queue": new_recovery_queue,
                        "current_state": WorkflowState.VALIDATION
                    }
                else:
                    return {
                        "execution_results": new_execution_results,
                        "current_state": WorkflowState.VALIDATION
                    }
        sub_queries_dict = [asdict(sq) for sq in state.query_plan.sub_queries]
        results = await self.tool_executor.execute_batch(sub_queries_dict)
        return {
            "execution_results": results,
            "current_state": WorkflowState.VALIDATION
        }
    
    @log_execution_time(func_name="ValidateResultNode")
    def _validate_results_node(self, state: AgentState) -> Dict[str, Any]:
        if state.recovery_queue and len(state.recovery_queue) > 0:
            new_recovery_queue = []
            for recovery_item in state.recovery_queue:
                execution_result = None # 队列里面存在 且 在execution_results里面的 是需要处理的
                if state.execution_results:
                    for result in state.execution_results:
                        if result.query_id == recovery_item.query_id:
                            execution_result = result
                            break
                if execution_result:
                    if execution_result.status == "success":
                        pass
                    else:
                        new_recovery_queue.append(recovery_item)
                else:
                    raise IndexError("队列里面有的在执行结果里面一定得有 看看是哪里的逻辑出现了问题")
            state.recovery_queue = new_recovery_queue
            return {
                "recovery_queue": new_recovery_queue,
                "current_state": WorkflowState.VALIDATION
            }
        
        plan_dict = {
            "meta": state.query_plan.meta if state.query_plan.meta else {},
            "sub_queries": [asdict(sq) for sq in state.query_plan.sub_queries] if state.query_plan else []
        }
        
        recovery_queue = self.recovery_mechanism.validate_execution_results(
            [asdict(er) for er in state.execution_results] if state.execution_results else [],
            plan_dict
        )
        return {
            "recovery_queue": recovery_queue,
            "current_state": WorkflowState.VALIDATION
        }
    
    def _route_after_validation(self, state: AgentState) -> str:
        if state.recovery_queue is not None and len(state.recovery_queue) > 0:
            return "recovery"
        return "end"
    
    @log_execution_time(func_name="RecoveryActionNode")
    def _recovery_action_node(self, state: AgentState) -> Dict[str, Any]:
        if not state.recovery_queue or len(state.recovery_queue) == 0:
            return {
                "current_state": WorkflowState.VALIDATION,
            }
        current_recovery_item = state.recovery_queue[0]
        if current_recovery_item is None:
            return {
                "current_state": WorkflowState.VALIDATION,
            }
        if current_recovery_item.retry_count >= current_recovery_item.max_retries:
            new_recovery_queue, new_query_plan, new_exe_results = self._remove_sub_query(state=state, current_recovery_item=current_recovery_item)
            return {
                "current_state": WorkflowState.VALIDATION,
                "recovery_queue": new_recovery_queue,
                "query_plan": new_query_plan,
                "execution_results": new_exe_results
            }
        self.logger.info(f"{1/len(state.recovery_queue)*100}/% Processing Recovery Queue item: Query_id={current_recovery_item.query_id}, Retry={current_recovery_item.retry_count}")
        self.logger.info(f"RecoverInformation: {current_recovery_item}")
        is_solvable = self.recovery_mechanism.get_is_solvable(current_recovery_item=current_recovery_item) # TODO bool type -> to llm 都到recovery里面做
        
        if not is_solvable:
            new_recovery_queue, new_query_plan, new_exe_results = self._remove_sub_query(state=state, current_recovery_item=current_recovery_item)
            return {
                "current_state": WorkflowState.VALIDATION,
                "recovery_queue": new_recovery_queue,
                "query_plan": new_query_plan,
                "execution_results": new_exe_results
            }
        else:
            new_sub_query = self.recovery_mechanism.generate_retry_result(current_recovery_item, state.query_plan)
            current_recovery_item.retry_count += 1
            updated_sub_queries = []
            if state.query_plan and state.query_plan.sub_queries:
                for sub_query in state.query_plan.sub_queries:
                    if sub_query.id == current_recovery_item.query_id:
                        updated_sub_queries.append(new_sub_query)
                    else:
                        updated_sub_queries.append(sub_query)
            updated_query_plan = QueryPlan(
                meta=state.query_plan.meta,
                sub_queries=updated_sub_queries,
                status=state.query_plan.status
            )
            return {
                "current_state": WorkflowState.TOOL_EXECUTION,
                "recovery_queue": state.recovery_queue,
                "query_plan": updated_query_plan,
            }
    
    def _remove_sub_query(self, state: AgentState, current_recovery_item: RecoveryOutput):
        new_recovery_queue = state.recovery_queue[1:]  # remove the recovery data
        # remove the current subquery from the global subquery and exe_result.
        new_sub_queries = []
        new_exe_results = []
        for sub_query in state.query_plan.sub_queries:
            if sub_query.id != current_recovery_item.query_id:
                new_sub_queries.append(sub_query)
        new_query_plan = QueryPlan(meta=state.query_plan.meta, sub_queries=new_sub_queries, status=state.query_plan.status)
        for exe_result in state.execution_results:
            if exe_result.query_id != current_recovery_item.query_id:
                new_exe_results.append(exe_result)
        
        return new_recovery_queue, new_query_plan, new_exe_results

    def _organize_data_node(self, state: AgentState) -> List[SubQueryOutput]:
        # For security reasons, a verification should be performed.
        if state.recovery_queue and len(state.recovery_queue) > 0:
            raise ValueError("队列里面还有未处理的执行结果 但走到了归纳数据的节点")
        currently_exe_result = state.execution_results
        for exe_result in currently_exe_result:
            if exe_result.status == "error":
                raise ValueError("执行结果里面仍有error，但却提前走到了归纳数据的节点")
        assert len(state.query_plan.sub_queries) == len(state.execution_results), "sub_queries与exe_result的长度不匹配 请检查代码逻辑"
        finally_result = []
        for sub_query, exe_result in zip(state.query_plan.sub_queries, state.execution_results):
            assert sub_query.id == exe_result.query_id, f"sub_query.id != exe_result.query_id"
            finally_result.append(
                SubQueryOutput(
                    purpose=remove_huoqu(sub_query.purpose),
                    exe_data_result=exe_result.exe_data_result
                )
            )
        return finally_result, state
    
    async def run(self, user_query: Dict[str, Any], template: str, plan_template: str) -> str:
        initial_state = AgentState(
            user_query=user_query,
            template=template,
            plan_template=plan_template
        )
        finally_result, state = await self.workflow_graph.ainvoke(initial_state)
        
        return finally_result, state
