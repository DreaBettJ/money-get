"""Agent基类"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import os
from pathlib import Path
import json

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent


class BaseAgent(ABC):
    """Agent基类"""
    
    def __init__(self, name: str = None):
        self.name = name or self.__class__.__name__
    
    @abstractmethod
    def analyze(self, stock_code: str, **kwargs) -> str:
        """分析股票"""
        pass
    
    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        return ""
    
    def call_llm(self, prompt: str, system_prompt: str = None) -> str:
        """调用LLM"""
        from money_get.llm import get_llm
        
        llm = get_llm(temperature=0.1)
        
        messages = [
            {"role": "system", "content": system_prompt or self.get_system_prompt()},
            {"role": "user", "content": prompt}
        ]
        
        response = llm.invoke(messages)
        return response.content
    
    def format_output(self, title: str, content: str) -> str:
        """格式化输出"""
        return f"## {title}\n\n{content}"
