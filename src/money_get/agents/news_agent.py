"""消息Agent - 分析新闻和政策（含异动监控）"""
from .base import BaseAgent
from .cache import get_cache_key, get_cached_result, save_cache, CACHE_CONFIG
from money_get.db import get_news, get_stock


class NewsAgent(BaseAgent):
    """消息Agent - 分析新闻和政策"""
    
    def __init__(self):
        super().__init__("消息Agent")
    
    def get_system_prompt(self) -> str:
        return """你是资深财经新闻分析师，专门分析股票相关的新闻和公告。

你的职责：
1. 分析公司新闻（业绩、并购、减持等）
2. 分析行业政策
3. 判断利好/利空
4. 评估影响程度
5. 识别市场异动

输出格式要求：
- 用中文输出
- 重点突出利好/利空
- 给出影响程度判断"""
    
    def analyze(self, stock_code: str, **kwargs) -> str:
        """分析新闻"""
        # 获取数据
        news = get_news(stock_code, limit=20)
        stock = get_stock(stock_code) or {}
        
        # 准备数据
        data = {
            'stock_code': stock_code,
            'stock_name': stock.get('name') or stock_code,
            'news': [dict(n) for n in news] if news else []
        }
        
        # 生成key
        prompt = "分析以下股票的新闻："
        cache_key = get_cache_key(data, prompt)
        
        # 尝试缓存 (12小时)
        cached = get_cached_result(cache_key, max_age_days=CACHE_CONFIG['news_agent'])
        if cached:
            return f"[消息Agent - 缓存]\n{cached}"
        
        # 构建提示词
        prompt = self._build_prompt(data)
        
        # 调用LLM
        result = self.call_llm(prompt)
        
        # 缓存
        save_cache(cache_key, result)
        
        return self.format_output(f"📰 新闻分析 - {stock.get('name', stock_code)}", result)
    
    def _build_prompt(self, data: dict) -> str:
        """构建提示词"""
        stock_name = data.get('stock_name', '')
        news = data.get('news', [])
        
        news_info = f"股票: {stock_name}\n\n最新新闻:\n"
        for i, n in enumerate(news[:10]):
            title = n.get('title', '')[:60]
            pub_date = n.get('pub_date', '')
            source = n.get('source', '')
            news_info += f"{i+1}. [{pub_date}] {title}\n"
            if source:
                news_info += f"   来源: {source}\n"
        
        prompt = f"""{news_info}

请分析：
1. 整体新闻情绪（利好/利空/中性）
2. 最重要的3条新闻及影响
3. 是否有重大利空（减持、亏损、诉讼等）
4. 给出操作建议

注意：只输出分析结论。"""
        
        return prompt


def analyze_news(stock_code: str) -> str:
    """便捷函数"""
    return NewsAgent().analyze(stock_code)
