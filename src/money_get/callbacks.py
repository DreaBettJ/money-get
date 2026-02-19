"""自定义回调处理器"""
import logging
import json
import os
from pathlib import Path
from datetime import datetime
from langchain_core.callbacks import BaseCallbackHandler

logger = logging.getLogger(__name__)


class VerboseCallbackHandler(BaseCallbackHandler):
    """打印 prompt 和 response 到终端"""
    
    def on_llm_start(self, serialized, prompts, **kwargs):
        _logger.info("\n" + "="*50)
        _logger.info("📤 PROMPT (LLM Input)")
        _logger.info("="*50)
        for i, p in enumerate(prompts):
            logger.info(f"\n--- Message {i+1} ---")
            # 截断太长
            logger.info(p[:2000] if len(p) > 2000 else p)
        logger.info("")
    
    def on_llm_end(self, response, **kwargs):
        _logger.info("="*50)
        _logger.info("📥 RESPONSE (LLM Output)")
        _logger.info("="*50)
        # 打印内容
        if hasattr(response, 'generations') and response.generations:
            for gen in response.generations[0]:
                content = gen.text if hasattr(gen, 'text') else str(gen)
                logger.info(content[:2000] if len(content) > 2000 else content)
        _logger.info("\n" + "="*50)
        
        # 打印 token 使用
        if hasattr(response, 'llm_output') and response.llm_output:
            usage = response.llm_output.get('usage', {})
            logger.info(f"📊 Token: prompt={usage.get('prompt_tokens', 0)}, "
                  f"completion={usage.get('completion_tokens', 0)}, "
                  f"total={usage.get('total_tokens', 0)}")
            _logger.info("="*50 + "\n")
    
    def on_llm_error(self, error, **kwargs):
        logger.info(f"\n❌ LLM Error: {error}\n")


class TraceCallbackHandler(BaseCallbackHandler):
    """记录 prompt 和 response 到日志文件"""
    
    def __init__(self):
        super().__init__()
        self.trace_file = Path(__file__).parent.parent.parent / "data" / "traces"
        self.trace_file.mkdir(parents=True, exist_ok=True)
        self.trace_file = self.trace_file / f"trace_{datetime.now().strftime('%Y%m%d')}.jsonl"
    
    def on_llm_start(self, serialized, prompts, **kwargs):
        entry = {
            "type": "start",
            "timestamp": datetime.now().isoformat(),
            "prompts": prompts
        }
        self._write(entry)
    
    def on_llm_end(self, response, **kwargs):
        # 获取输出
        output_text = ""
        if hasattr(response, 'generations') and response.generations:
            for gen in response.generations[0]:
                output_text = gen.text if hasattr(gen, 'text') else str(gen)
        
        # 获取 token
        usage = {}
        if hasattr(response, 'llm_output') and response.llm_output:
            usage = response.llm_output.get('usage', {})
        
        entry = {
            "type": "end",
            "timestamp": datetime.now().isoformat(),
            "output": output_text[:5000],  # 限制长度
            "usage": usage
        }
        self._write(entry)
    
    def on_llm_error(self, error, **kwargs):
        entry = {
            "type": "error",
            "timestamp": datetime.now().isoformat(),
            "error": str(error)
        }
        self._write(entry)
    
    def _write(self, entry):
        try:
            with open(self.trace_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
            logger.info(f"📝 Traced to: {self.trace_file}")
        except Exception as e:
            logger.info(f"⚠️ Trace write failed: {e}")
