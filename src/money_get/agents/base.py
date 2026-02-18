"""Agent基类"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import os
from pathlib import Path
import json
import requests
from money_get.context import (
    ContextScope,
    get_isolated_context,
    format_context_for_agent,
    get_current_stock
)

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent


def get_api_config() -> dict:
    """获取 API 配置"""
    config_path = PROJECT_ROOT.parent / "config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    return config.get("llm", {})


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
    
    def analyze_with_context(self, stock_code: str, extra_prompt: str = "", **kwargs) -> str:
        """在隔离上下文中分析股票"""
        with ContextScope(stock_code):
            context = get_isolated_context(stock_code)
            context_str = format_context_for_agent(context, stock_code)
            
            full_prompt = f"""{context_str}

## 本次分析任务
{extra_prompt}

请基于以上上下文进行分析。"""
            
            result = self.analyze(stock_code, prompt=full_prompt, **kwargs)
            return result
    
    def call_llm(self, prompt: str, system_prompt: str = None) -> str:
        """调用LLM"""
        config = get_api_config()
        
        url = config.get("url", "https://api.minimax.chat/v1") + "/text/chatcompletion_v2"
        api_key = config.get("api_key", "")
        model = config.get("model", "MiniMax-M2.5")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        messages = [
            {"role": "system", "content": system_prompt or self.get_system_prompt()},
            {"role": "user", "content": prompt}
        ]
        
        data = {
            "model": model,
            "messages": messages,
            "temperature": 0.1
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=120)
        response.raise_for_status()
        
        result = response.json()
        return result["choices"][0]["message"]["content"]
    
    def format_output(self, title: str, content: str) -> str:
        """格式化输出"""
        return f"## {title}\n\n{content}"
