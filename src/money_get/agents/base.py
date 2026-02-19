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
from ..logger import logger as _logger

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent


def get_api_config() -> dict:
    """获取 API 配置"""
    config_path = PROJECT_ROOT.parent / "config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    # 合并 llm 和 langfuse 配置
    llm_cfg = config.get("llm", {})
    llm_cfg["langfuse"] = config.get("langfuse", {})
    return llm_cfg


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
        import uuid
        
        config = get_api_config()
        
        url = config.get("url", "https://api.minimax.chat/v1") + "/text/chatcompletion_v2"
        api_key = config.get("api_key", "")
        model = config.get("model", "MiniMax-M2.5")
        
        # 生成 trace_id
        trace_id = str(uuid.uuid4())
        
        # 尝试使用 Langfuse 记录
        langfuse = None
        try:
            from langfuse import Langfuse
            cfg = config.get("langfuse", {})
            if cfg.get("public_key") and cfg.get("secret_key"):
                langfuse = Langfuse(
                    public_key=cfg["public_key"],
                    secret_key=cfg["secret_key"]
                )
                langfuse.trace_id = trace_id
        except:
            pass
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        system_msg = system_prompt or self.get_system_prompt()
        
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt}
        ]
        
        # 详细日志
        _logger.info(f"🤖 [{self.name}] 调用LLM [Trace: {trace_id[:8]}...]")
        _logger.info(f"   System: {system_msg[:200]}...")
        _logger.info(f"   User: {prompt[:300]}...")
        
        data = {
            "model": model,
            "messages": messages,
            "temperature": 0.3
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=120)
        response.raise_for_status()
        
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        
        _logger.info(f"   Result [Trace: {trace_id[:8]}...]: {content[:300]}...")
        
        # 记录到 Langfuse
        if langfuse:
            try:
                # 创建 trace
                trace_id = langfuse.create_trace_id(seed=trace_id)
                # 使用 span 记录
                with langfuse.start_as_current_span(
                    name=self.name,
                    trace_context={"trace_id": trace_id}
                ) as span:
                    span.input = {"messages": messages}
                    span.output = content[:500]
                    span.metadata = {"model": model, "temperature": 0.3}
                _logger.info(f"   📊 Langfuse 已记录 [Trace: {trace_id[:8]}...]")
            except Exception as e:
                _logger.warning(f"   ⚠️ Langfuse 记录失败: {e}")
        
        return content
    
    def format_output(self, title: str, content: str) -> str:
        """格式化输出"""
        return f"## {title}\n\n{content}"
