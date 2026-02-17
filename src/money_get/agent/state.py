"""Agent 状态定义"""
from typing import Any, TypedDict


class AgentState(TypedDict):
    """Agent 状态"""

    messages: list  # 对话历史
    task: str  # 当前任务
    context: dict  # 上下文数据
    result: Any  # 执行结果
