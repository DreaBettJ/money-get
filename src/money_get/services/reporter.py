"""报告生成与推送"""
from typing import Any

from money_get.config import DINGTALK_WEBHOOK, FEISHU_WEBHOOK


def generate_report(content: Any) -> str:
    """生成报告"""
    if isinstance(content, str):
        return content
    return str(content)


def push_to_dingtalk(message: str) -> bool:
    """推送至钉钉"""
    if not DINGTALK_WEBHOOK:
        return False

    import requests

    try:
        data = {"msgtype": "text", "text": {"content": f"money-get: {message}"}}
        resp = requests.post(DINGTALK_WEBHOOK, json=data, timeout=10)
        return resp.status_code == 200
    except Exception:
        return False


def push_to_feishu(message: str) -> bool:
    """推送至飞书"""
    if not FEISHU_WEBHOOK:
        return False

    import requests

    try:
        data = {"msg_type": "text", "content": {"text": f"money-get: {message}"}}
        resp = requests.post(FEISHU_WEBHOOK, json=data, timeout=10)
        return resp.status_code == 200
    except Exception:
        return False


def notify(message: str) -> None:
    """发送通知"""
    push_to_dingtalk(message)
    push_to_feishu(message)
