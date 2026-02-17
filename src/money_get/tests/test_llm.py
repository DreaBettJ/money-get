"""LLM 层单元测试 - 真实调用测试"""
import pytest
import logging
from money_get.llm import get_default_llm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestLlmReal:
    """真实 LLM 调用测试"""

    def test_llm_basic_invoke(self):
        """测试 LLM 基本调用"""
        llm = get_default_llm()
        response = llm.invoke("Say hello in one word")

        logger.info(f"Response: {response.content}")

        assert response is not None
        assert hasattr(response, "content")
        assert len(response.content) > 0

    def test_llm_with_message_list(self):
        """测试带消息列表的调用"""
        from langchain_core.messages import HumanMessage

        llm = get_default_llm()
        response = llm.invoke([HumanMessage(content="What is 1+1?")])

        logger.info(f"Response: {response.content}")

        assert response is not None
        assert hasattr(response, "content")
        assert len(response.content) > 0
