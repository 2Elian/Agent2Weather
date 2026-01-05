import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

from langgraph.graph import StateGraph, END
from langchain_openai.chat_models.base import BaseChatOpenAI

from .query_decomposer import QueryDecomposer, SubQuery
from .data_planner import DataPlanner, QueryPlan, SubQuery
from .tool_executor import ToolExecutor, ExecutionResult
from .recovery_mechanism import RecoveryMechanism, RecoveryOutput
from .template_generator import TemplateGenerator


@dataclass
class SubQueryOutput:
    id: str
    purpose: str
    tool: str
    params: Dict[str, Any]
    exe_data_result: Any


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
    # validation_result: Optional[ValidationResult] = None
    recovery_queue: Optional[List[RecoveryOutput]] = None
    final_report: Optional[str] = None
    current_state: WorkflowState = WorkflowState.QUERY_NORMALIZATION
    retry_count: int = 0
    max_retries: int = 3


class PECWAgent:
    # init to BaseAgent
    def __init__(self, llm: BaseChatOpenAI, tool_registry: Dict[str, Any] = None):
        self.tool_registry = tool_registry
        self.query_decomposer = QueryDecomposer(tool_registry)
        self.data_planner = DataPlanner(llm)
        self.tool_executor = ToolExecutor()
        self.recovery_mechanism = RecoveryMechanism(tool_registry)
        self.template_generator = TemplateGenerator()
        self.workflow_graph = self._build_workflow()
    
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
    
    async def _plan_data_node(self, state: AgentState) -> Dict[str, Any]:
        plan = await self.data_planner.plan(state.normalized_query, state.plan_template)
        return {
            "query_plan": plan,
            "current_state": WorkflowState.TOOL_EXECUTION
        }
    
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
                    new_execution_results = [result]
                
                # 如果执行成功，从恢复队列中移除该项
                if result.status == "success":
                    new_recovery_queue = state.recovery_queue[1:]
                    return {
                        "execution_results": new_execution_results,
                        "recovery_queue": new_recovery_queue,
                        "current_state": WorkflowState.VALIDATION
                    }
                else:
                    # 如果执行失败，保持恢复队列不变
                    return {
                        "execution_results": new_execution_results,
                        "current_state": WorkflowState.VALIDATION
                    }
        else:
            # 没有恢复队列，执行所有子查询
            sub_queries_dict = [asdict(sq) for sq in state.query_plan.sub_queries]
            results = self.tool_executor.execute_batch(sub_queries_dict)
            
            return {
                "execution_results": results,
                "current_state": WorkflowState.VALIDATION
            }
    
    def _validate_results_node(self, state: AgentState) -> Dict[str, Any]:
        # 如果有恢复队列，说明这是在处理恢复任务
        if state.recovery_queue and len(state.recovery_queue) > 0:
            # 对于恢复队列中的任务，我们需要验证最近的执行结果
            # 创建一个新的恢复队列，只保留需要继续处理的项
            new_recovery_queue = []
            
            # 检查队列中每个恢复项的执行结果
            for recovery_item in state.recovery_queue:
                # 查找对应的执行结果
                execution_result = None
                if state.execution_results:
                    for result in state.execution_results:
                        if result.query_id == recovery_item.query_id:
                            execution_result = result
                            break
                
                # 如果找到了执行结果
                if execution_result:
                    # 检查执行结果是否成功
                    if execution_result.status == "success":
                        # 执行成功，不需要再处理该项
                        pass
                    else:
                        # 执行失败，检查是否达到最大迭代次数
                        if recovery_item.retry_count >= recovery_item.max_retries:
                            # 达到最大迭代次数，不再处理该项
                            pass
                        else:
                            # 否则，继续保留该项在队列中进行下一次尝试
                            new_recovery_queue.append(recovery_item)
                else:
                    # 没有找到执行结果，继续保留该项在队列中
                    new_recovery_queue.append(recovery_item)
            
            return {
                "recovery_queue": new_recovery_queue,
                "current_state": WorkflowState.VALIDATION
            }
        else:
            # 如果没有恢复队列，说明这是初始执行，需要进行全面验证
            plan_dict = {
                "meta": asdict(state.query_plan.meta) if state.query_plan.meta else {},
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
        # 检查恢复队列是否为空
        if state.recovery_queue is not None and len(state.recovery_queue) > 0:
            # 检查队列中是否还有需要处理的项
            for item in state.recovery_queue:
                if item.retry_count < item.max_retries:
                    return "recovery"
        return "end"
    
    def _recovery_action_node(self, state: AgentState) -> Dict[str, Any]:
        # 从队列里取出一个需要重置的数据
        current_recovery_item = state.recovery_queue[0]
        
        # 判断是否达到迭代限度
        if current_recovery_item.retry_count >= current_recovery_item.max_retries:
            # 达到最大迭代次数，该id的sub_query删除掉，包括队列和全局的sub_query，开始下一个队列或结束队列
            new_recovery_queue = state.recovery_queue[1:]  # 移除第一个元素
            
            # 从全局的sub_query中删除
            new_sub_queries = []
            if state.query_plan and state.query_plan.sub_queries:
                for sub_query in state.query_plan.sub_queries:
                    if sub_query.id != current_recovery_item.query_id:
                        new_sub_queries.append(sub_query)
                
                # 更新查询计划
                new_query_plan = QueryPlan(
                    meta=state.query_plan.meta,
                    sub_queries=new_sub_queries,
                    status=state.query_plan.status
                )
            else:
                new_query_plan = state.query_plan
            
            return {
                "current_state": WorkflowState.VALIDATION,
                "recovery_queue": new_recovery_queue,
                "query_plan": new_query_plan
            }

        # 让大语言模型进行分析得到当前query是否是可以被解的
        is_solvable = self._analyze_query_solvable(current_recovery_item, state)
        
        if not is_solvable:
            # 不可以解，该id的sub_query删除掉，包括队列和全局的sub_query，开始下一个队列或结束队列
            new_recovery_queue = state.recovery_queue[1:]  # 移除第一个元素
            
            # 从全局的sub_query中删除
            new_sub_queries = []
            new_execution_results = []
            
            if state.query_plan and state.query_plan.sub_queries:
                for sub_query in state.query_plan.sub_queries:
                    if sub_query.id != current_recovery_item.query_id:
                        new_sub_queries.append(sub_query)
                
                # 更新查询计划
                new_query_plan = QueryPlan(
                    meta=state.query_plan.meta,
                    sub_queries=new_sub_queries,
                    status=state.query_plan.status
                )
            else:
                new_query_plan = state.query_plan
            
            # 同时从执行结果中移除对应的项
            if state.execution_results:
                for exe_result in state.execution_results:
                    if exe_result.query_id != current_recovery_item.query_id:
                        new_execution_results.append(exe_result)
            
            return {
                "current_state": WorkflowState.VALIDATION,
                "recovery_queue": new_recovery_queue,
                "query_plan": new_query_plan,
                "execution_results": new_execution_results
            }
        else:
            # 可以解，生成新的sub_query来替换原来的
            new_sub_query = self._generate_replacement_subquery(current_recovery_item, state)
            
            # 更新查询计划中的sub_query
            updated_sub_queries = []
            if state.query_plan and state.query_plan.sub_queries:
                for sub_query in state.query_plan.sub_queries:
                    if sub_query.id == current_recovery_item.query_id:
                        # 替换为新的sub_query
                        updated_sub_queries.append(new_sub_query)
                    else:
                        updated_sub_queries.append(sub_query)
            
            # 更新查询计划
            updated_query_plan = QueryPlan(
                meta=state.query_plan.meta,
                sub_queries=updated_sub_queries,
                status=state.query_plan.status
            )
            
            # 增加重试计数
            current_recovery_item.retry_count += 1
            
            return {
                "current_state": WorkflowState.TOOL_EXECUTION,
                "recovery_queue": state.recovery_queue,
                "query_plan": updated_query_plan
            }
    
    def _analyze_query_solvable(self, recovery_item: RecoveryOutput, state: AgentState) -> bool:
        """
        让大语言模型分析当前query是否可以被解决
        
        Args:
            recovery_item: 恢复项
            state: 当前状态
            
        Returns:
            是否可以解决
        """
        # 这里应该调用LLM来分析query是否可以被解决
        # 为了简化，我们假设这里进行了分析并得到了结果
        
        # 实际实现中，这里应该：
        # 1. 构建提示词，包含错误信息、查询信息等
        # 2. 调用LLM进行分析
        # 3. 解析LLM的输出
        
        # 目前我们简单地返回True，表示可以解决
        return True
    
    def _generate_replacement_subquery(self, recovery_item: RecoveryOutput, state: AgentState):
        """
        生成替换的sub_query
        
        Args:
            recovery_item: 恢复项
            state: 当前状态
            
        Returns:
            新的SubQuery对象
        """
        # 这里应该调用LLM来生成修复后的sub_query
        # 为了简化，我们使用恢复项中的信息来构建新的sub_query
        
        # 实际实现中，这里应该：
        # 1. 构建提示词，包含错误信息、查询信息、工具描述等
        # 2. 调用LLM来生成修复后的查询参数
        # 3. 创建新的SubQuery对象
        
        # 从query_information中获取原始信息
        query_info = recovery_item.query_information
        
        # 从原始查询信息中提取必要的字段
        purpose = query_info.get('purpose', 'Unknown purpose')
        tool = query_info.get('tool', 'Unknown tool')
        params = query_info.get('params', {})
        expected_fields = query_info.get('expected_fields', [])
        
        # 创建新的SubQuery，使用相同的ID
        new_sub_query = SubQuery(
            id=recovery_item.query_id,
            purpose=purpose,
            tool=tool,
            params=params,
            expected_fields=expected_fields
        )
        
        return new_sub_query

    def _fix_query(self, recovery_item: RecoveryOutput, state: AgentState):
        """
        修复query
        
        Args:
            recovery_item: 恢复项
            state: 当前状态
        """
        # 这里应该调用LLM来修复query
        # 为了简化，我们假设这里进行了修复
        
        # 实际实现中，这里应该：
        # 1. 构建提示词，包含错误信息、查询信息等
        # 2. 调用LLM来生成修复后的查询
        # 3. 更新recovery_item中的查询信息
        
        # 目前我们不做任何操作
        pass

    def _organize_data_node(self, state: AgentState) -> Dict[str, Any]:
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
                    id=sub_query.id,
                    purpose=sub_query.purpose,
                    tool=sub_query.tool,
                    params=sub_query.params,
                    exe_data_result=exe_result.exe_data_result
                )
            )
        return {
            "final_data": finally_result,
            "current_state": WorkflowState.COMPLETED
        }
    
    async def run(self, user_query: Dict[str, Any], template: str, plan_template: str) -> str:
        initial_state = AgentState(
            user_query=user_query,
            template=template,
            plan_template=plan_template
        )
        final_state = await self.workflow_graph.ainvoke(initial_state)
        
        return final_state.final_report, final_state
