"""LLM 层 - 提供统一的 LLM 调用"""
import json
import os
from pathlib import Path
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.callbacks import BaseCallbackHandler


def get_config() -> dict:
    """读取配置文件"""
    config_path = Path(__file__).parent.parent.parent / "config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    llm_config = config.get("llm", {})
    api_key = llm_config.get("api_key", "")
    if api_key.startswith("${") and api_key.endswith("}"):
        env_var = api_key[2:-1]
        llm_config["api_key"] = os.getenv(env_var, "")

    return llm_config


def get_langfuse_config() -> dict:
    """读取 Langfuse 配置"""
    config_path = Path(__file__).parent.parent.parent / "config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    return config.get("langfuse", {})


_langfuse = None


def get_langfuse():
    """获取 Langfuse 实例"""
    global _langfuse
    
    if _langfuse is not None:
        return _langfuse
    
    try:
        from langfuse import Langfuse
    except ImportError:
        print("⚠️ langfuse 未安装: pip install langfuse")
        return None
    
    cfg = get_langfuse_config()
    public_key = cfg.get("public_key", "")
    secret_key = cfg.get("secret_key", "")
    
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY", "") or public_key
    secret_key = os.getenv("LANGFUSE_SECRET_KEY", "") or secret_key
    
    if not public_key or not secret_key:
        return None
    
    _langfuse = Langfuse(
        public_key=public_key,
        secret_key=secret_key,
        host='https://cloud.langfuse.com'
    )
    
    print(f"✅ Langfuse 已初始化")
    return _langfuse


class LangfuseCallbackHandler(BaseCallbackHandler):
    """Langfuse 回调处理器 - 支持 Tool 调用、多轮对话"""
    
    def __init__(self, metadata: dict = None):
        super().__init__()
        self.langfuse = None
        self.trace = None
        self.generation = None
        self.span = None
        self.metadata = metadata or {}
        self.tool_calls = []
        self.message_history = []
    
    def on_llm_start(self, serialized, prompts, **kwargs):
        """LLM 开始调用"""
        self.langfuse = get_langfuse()
        if not self.langfuse:
            return
        
        # 构建 metadata
        meta = {
            **self.metadata,
            "model": "MiniMax-M2.5",
            "temperature": 0.1,
            "user": "stock_analyst"
        }
        
        # 创建 trace（带元数据）
        self.trace = self.langfuse.trace(
            name="stock_analysis",
            metadata=meta
        )
        
        # 添加消息历史到 input
        input_text = ""
        if prompts:
            for p in prompts:
                input_text += p[:500]  # 截断
        
        # 创建 generation
        self.generation = self.trace.generation(
            name="llm_response",
            model="MiniMax-M2.5",
            input=input_text,
            metadata=meta
        )
        
        print(f"🔍 Langfuse: {self.langfuse.get_trace_url()}")
    
    def on_llm_end(self, response, **kwargs):
        """LLM 结束调用"""
        if not self.generation:
            return
        
        try:
            output_text = ""
            if hasattr(response, 'generations') and response.generations:
                for gen in response.generations[0]:
                    output_text = gen.text if hasattr(gen, 'text') else str(gen)
            
            # 处理 usage（MiniMax 格式不同）
            usage = {}
            if hasattr(response, 'llm_output') and response.llm_output:
                raw_usage = response.llm_output.get('usage', {})
                if raw_usage:
                    usage = {
                        "prompt_tokens": raw_usage.get('prompt_tokens', 0),
                        "completion_tokens": raw_usage.get('completion_tokens', 0),
                        "total_tokens": raw_usage.get('total_tokens', 0),
                        "unit": "tokens"
                    }
            
            self.generation.end(
                output=output_text[:2000],
                usage=usage if usage else None
            )
        except Exception as e:
            print(f"⚠️ Langfuse update failed: {e}")
    
    def on_tool_start(self, serialized, input_str, **kwargs):
        """Tool 开始调用"""
        if not self.trace:
            return
        
        tool_name = serialized.get('name', 'unknown')
        
        # 创建 span 记录 tool 调用
        self.span = self.trace.span(
            name=tool_name,
            input=input_str[:500]
        )
        
        self.tool_calls.append({
            "tool": tool_name,
            "input": input_str[:200],
            "start_time": self.trace.get_trace_id()
        })
        
        print(f"🔧 Tool: {tool_name}")
    
    def on_tool_end(self, output, **kwargs):
        """Tool 结束调用"""
        if not self.span:
            return
        
        try:
            self.span.end(output=str(output)[:500])
        except:
            pass
    
    def on_tool_error(self, error, **kwargs):
        """Tool 错误"""
        if self.span:
            try:
                self.span.end(output=f"Error: {error}")
            except:
                pass
    
    def add_message(self, role: str, content: str):
        """添加消息到历史"""
        self.message_history.append({
            "role": role,
            "content": content[:500]
        })
    
    def get_trace_url(self) -> str:
        """获取 Trace URL"""
        if self.langfuse:
            return self.langfuse.get_trace_url()
        return ""


def get_llm(
    url: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.7,
    thinking: bool = False,
    trace: bool = False,
    verbose: bool = False,
    metadata: dict = None,
    **kwargs
) -> ChatOpenAI:
    """获取 LLM 实例
    
    Args:
        trace: 是否启用 Langfuse 追踪
        verbose: 是否打印 prompt/response
        metadata: 自定义元数据
    """
    config = get_config()

    extra_body = {}
    if thinking:
        extra_body["thinking"] = {"type": "enabled"}

    callbacks = []
    
    if verbose:
        from .callbacks import VerboseCallbackHandler
        callbacks.append(VerboseCallbackHandler())
    
    if trace:
        callbacks.append(LangfuseCallbackHandler(metadata=metadata))
    
    return ChatOpenAI(
        base_url=url or config.get("url"),
        model=model or config.get("model"),
        api_key=config.get("api_key"),
        temperature=temperature,
        extra_body=extra_body if extra_body else None,
        callbacks=callbacks if callbacks else None,
        **kwargs
    )


def get_default_llm(trace: bool = False, verbose: bool = False, metadata: dict = None) -> ChatOpenAI:
    """获取默认 LLM 实例"""
    return get_llm(trace=trace, verbose=verbose, metadata=metadata)
