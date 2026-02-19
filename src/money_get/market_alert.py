"""新闻异动监控模块

功能：
1. 定时获取最新新闻
2. 检测重大利好/利空
3. 触发分析并推送
"""
import re
from datetime import datetime
from typing import List, Dict, Tuple
from money_get.db import get_news, insert_news


# 重大利好关键词
BULLISH_KEYWORDS = [
    # 业绩
    "预增", "大增", "扭亏", "盈利", "业绩增长", "净利润增长",
    # 并购
    "并购", "重组", "收购", "定增", "募资",
    # 回购
    "回购", "增持", "增持计划", "拟增持",
    # 涨价
    "涨价", "提价", "上调", "价格上涨",
    # 订单
    "中标", "签订", "订单", "合同",
    # 政策
    "政策支持", "获批", "试点",
]

# 重大利空关键词
BEARISH_KEYWORDS = [
    # 减持
    "减持", "拟减持", "清仓式减持", "大宗减持",
    # 亏损
    "预亏", "亏损", "业绩下降", "大幅下降",
    # 风险
    "诉讼", "仲裁", "处罚", "调查", "立案",
    # 退市
    "退市", "ST", "*ST", "风险警示",
    # 造假
    "财务造假", "虚假陈述", "欺诈",
]


def detect_news_sentiment(title: str, content: str = "") -> Tuple[str, str]:
    """检测新闻情感和类型
    
    Returns:
        (sentiment, reason): sentiment=利好/利空/中性, reason=匹配到的关键词
    """
    text = (title + " " + (content or "")).upper()
    title_upper = title.upper()
    
    # 检查利好
    bullish_matches = []
    for keyword in BULLISH_KEYWORDS:
        if keyword.upper() in title_upper:
            bullish_matches.append(keyword)
    
    if bullish_matches:
        return "利好", ",".join(bullish_matches[:2])
    
    # 检查利空
    bearish_matches = []
    for keyword in BEARISH_KEYWORDS:
        if keyword.upper() in title_upper:
            bearish_matches.append(keyword)
    
    if bearish_matches:
        return "利空", ",".join(bearish_matches[:2])
    
    return "中性", ""


def filter_market_news(news_list: List[Dict]) -> Dict[str, List[Dict]]:
    """筛选市场异动新闻
    
    Returns:
        {"利好": [...], "利空": [...], "中性": [...]}
    """
    result = {
        "利好": [],
        "利空": [],
        "中性": []
    }
    
    for news in news_list:
        title = news.get("title", "")
        content = news.get("content", "") or ""
        
        sentiment, reason = detect_news_sentiment(title, content)
        
        news_with_reason = {
            **news,
            "sentiment": sentiment,
            "reason": reason,
            "detected_at": datetime.now().isoformat()
        }
        
        result[sentiment].append(news_with_reason)
    
    return result


def get_breaking_news(code: str = None, limit: int = 20) -> List[Dict]:
    """获取需要关注的异动新闻
    
    Args:
        code: 股票代码，不传则获取所有
        limit: 获取数量
    
    Returns:
        重大异动新闻列表
    """
    news = get_news(code, limit=limit)
    
    # 检测异动
    categorized = filter_market_news(news)
    
    # 优先返回利好，然后利空
    breaking = []
    breaking.extend(categorized["利空"][:3])  # 利空优先看
    breaking.extend(categorized["利好"][:5])  # 利好次之
    
    return breaking


def format_alert(news_list: List[Dict]) -> str:
    """格式化异动提醒"""
    if not news_list:
        return "今日无重大异动新闻"
    
    lines = ["📊 市场异动监控", "="*30, ""]
    
    # 按类型分组
    bullish = [n for n in news_list if n.get("sentiment") == "利好"]
    bearish = [n for n in news_list if n.get("sentiment") == "利空"]
    
    if bullish:
        lines.append("🔥 【利好】")
        for i, news in enumerate(bullish[:5], 1):
            title = news.get("title", "")[:40]
            reason = news.get("reason", "")
            code = news.get("code", "")
            lines.append(f"{i}. [{code}] {title}")
            if reason:
                lines.append(f"   → {reason}")
        lines.append("")
    
    if bearish:
        lines.append("⚠️ 【利空】")
        for i, news in enumerate(bearish[:3], 1):
            title = news.get("title", "")[:40]
            reason = news.get("reason", "")
            code = news.get("code", "")
            lines.append(f"{i}. [{code}] {title}")
            if reason:
                lines.append(f"   → {reason}")
        lines.append("")
    
    return "\n".join(lines)


# 便捷函数
def check_market_movement() -> str:
    """检查市场异动（便捷函数）"""
    breaking = get_breaking_news(limit=30)
    return format_alert(breaking)
