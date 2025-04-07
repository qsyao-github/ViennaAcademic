"""
Chatbot后端，处理ViennaAcademic解题功能
"""

import asyncio
from typing import Dict

from langchain_core.messages import BaseMessage
from langchain_core.runnables.config import RunnableConfig
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import START, MessagesState, StateGraph
from python.chat_utils.memory import checkpoint_connection
from python.llm_utils.modelclient import deepseek_r1_671b, qwq_32b

select_model_from_num = {
    0: qwq_32b,
    1: deepseek_r1_671b,
}


async def solve_call_model(
    state: MessagesState, config: RunnableConfig
) -> Dict[str, BaseMessage]:
    """进行一轮“解题功能”对话

    Parameters
    ----------
    state: SolveMessageState
        当前状态

    Returns
    ----------
    Dict[str, List[BaseMessage]]
        一轮推理后的状态

    Notes
    ----------
    对于messages，langchain实现了reducer函数，信息默认附加在上一个状态后
    """
    model_num = config["configurable"].get("model_num", 0)
    model = select_model_from_num[model_num]
    response = await model.ainvoke(state["messages"])
    return {"messages": response}


solve_workflow = StateGraph(state_schema=MessagesState)
solve_workflow.add_edge(START, "model")
solve_workflow.add_node("model", solve_call_model)


async def build_solve_app():
    solve_sqlite_checkpointer = AsyncSqliteSaver(checkpoint_connection)
    return solve_workflow.compile(checkpointer=solve_sqlite_checkpointer)


solve_app = asyncio.run(build_solve_app())
