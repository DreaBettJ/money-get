"""推送服务

使用 OpenClaw 的 message 工具推送分析结果
"""
from typing import Dict, Any, Optional
import json
from pathlib import Path


def get_config() -> dict:
    """获取配置"""
    config_path = Path(__file__).parent.parent.parent / "config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def push_to_user(message: str, user_id: str = None) -> Dict[str, Any]:
    """推送消息给用户
    
    使用 OpenClaw 的 message 工具发送
    """
    try:
        from openclaw_tools import message
        
        config = get_config()
        push_config = config.get("push", {})
        
        # 默认使用 QQ
        channel = push_config.get("type", "qqbot")
        
        # 如果没有指定 user_id，从配置获取
        if not user_id:
            user_id = push_config.get("user_id", "33D10A193DA3C9C65811ED025D4D3782")
        
        # 发送消息
        result = message(
            action="send",
            channel=channel,
            message=message,
            userId=user_id
        )
        
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


def format_stock_analysis(stock_code: str, analysis: str) -> str:
    """格式化股票分析推送消息"""
    return f"""📈 股票分析报告 - {stock_code}

{analysis}

---
💡 由 money-get 自动推送"""


def format_market_analysis(analysis: str) -> str:
    """格式化市场分析推送消息"""
    return f"""🌍 市场分析报告

{analysis}

---
💡 由 money-get 自动推送"""


def format_daily_summary(data: Dict) -> str:
    """格式化每日摘要"""
    summary = "📊 每日数据摘要\n\n"
    
    if "stocks" in data:
        summary += "📈 关注股票:\n"
        for stock in data["stocks"]:
            summary += f"  • {stock['name']}: {stock['price']} ({stock['change']}%)\n"
    
    if "hot_sectors" in data:
        summary += "\n🔥 热点板块:\n"
        for sector in data["hot_sectors"][:5]:
            summary += f"  • {sector['name']}: {sector['change']}%\n"
    
    summary += "\n---\n💡 由 money-get 自动推送"
    
    return summary


def push_stock_analysis(stock_code: str, analysis: str, user_id: str = None) -> Dict[str, Any]:
    """推送股票分析结果"""
    message = format_stock_analysis(stock_code, analysis)
    return push_to_user(message, user_id)


def push_market_analysis(analysis: str, user_id: str = None) -> Dict[str, Any]:
    """推送市场分析结果"""
    message = format_market_analysis(analysis)
    return push_to_user(message, user_id)


def push_daily_summary(data: Dict, user_id: str = None) -> Dict[str, Any]:
    """推送每日摘要"""
    message = format_daily_summary(data)
    return push_to_user(message, user_id)


# 测试推送
if __name__ == "__main__":
    # 测试发送
    result = push_to_user("🧪 money-get 推送测试成功！")
    print(result)
