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
        _logger.info("⚠️ langfuse 未安装: pip install langfuse")
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
    
    _logger.info(f"✅ Langfuse 已初始化")
    return _langfuse


class LangfuseCallbackHandler(BaseCallbackHandler):
    """Langfuse 回调处理器 - 完整追踪版"""
    
    def __init__(self, metadata: dict = None):
        super().__init__()
        self.langfuse = None
        self.metadata = metadata or {}
        self.call_count = 0
        self.messages = []
        self.trace_id = None
    
    def on_llm_start(self, serialized, prompts, **kwargs):
        """LLM 开始调用"""
        self.langfuse = get_langfuse()
        self.call_count += 1
        
        from .logger import logger as _logger
        
        # 创建 trace
        if self.langfuse:
            try:
                self.trace_id = self.langfuse.create_trace_id()
                _logger.info(f"🔍 [Trace] {self.trace_id[:8]}... LLM调用 #{self.call_count}")
            except Exception as e:
                _logger.warning(f"⚠️ Trace创建失败: {e}")
        
        # 记录提示词
        _logger.info(f"🤖 LLM调用 #{self.call_count} 提示词:")
        for i, p in enumerate(prompts):
            _logger.info(f"  [Prompt {i}]: {p[:500]}...")
    
    def on_llm_end(self, response, **kwargs):
        """LLM 结束调用"""
        from .logger import logger as _logger
        
        # 记录结果
        output = ""
        if hasattr(response, 'generations') and response.generations:
            for gen in response.generations[0]:
                output = gen.text if hasattr(gen, 'text') else str(gen)
        
        trace_info = f" [Trace: {self.trace_id[:8]}...]" if self.trace_id else ""
        _logger.info(f"🤖 LLM结果 #{self.call_count}{trace_info}: {output[:300]}...")
        
        # 记录到 Langfuse
        if self.langfuse and self.trace_id:
            try:
                # 使用 update_trace_id 来标记完成
                self.langfuse.update_trace_id(
                    trace_id=self.trace_id,
                    trace={
                        "input": "prompt logged",
                        "output": output[:500] if output else "completed"
                    }
                )
            except Exception as e:
                _logger.warning(f"⚠️ Trace更新失败: {e}")
    
    def on_chat_model_start(self, serialized, messages, **kwargs):
        """记录聊天消息开始"""
        from .logger import logger as _logger
        self.messages = messages
        
        trace_info = f" [Trace: {self.trace_id[:8]}...]" if self.trace_id else ""
        _logger.info(f"📝 聊天消息数: {len(messages)}{trace_info}")
        for i, msg in enumerate(messages):
            _logger.info(f"  [{i}] {type(msg).__name__}: {str(msg)[:200]}...")
    
    def get_trace_url(self) -> str:
        """获取 Trace URL"""
        if self.langfuse and self.trace_id:
            try:
                # 从 public_key 提取 project_id
                pk = self.langfuse.public_key
                project_id = pk.split('-')[1] if '-' in pk else "unknown"
                return f"https://cloud.langfuse.com/project/{project_id}/traces/{self.trace_id}"
            except:
                pass
        return ""
            try:
                return f"https://cloud.langfuse.com"
            except:
                pass
        return ""


def get_llm(
    url: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.3,
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
    
    # 导入日志
    from .logger import logger as _logger
    _logger.info(f"LLM调用: model={model or config.get('model')}, temperature={temperature}, trace={trace}")

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
