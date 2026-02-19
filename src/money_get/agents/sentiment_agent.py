"""情绪Agent - 分析市场情绪和热点板块"""
from .base import BaseAgent
from .cache import get_cache_key, get_cached_result, save_cache, CACHE_CONFIG
from money_get.db import get_hot_sectors, get_lhb_data
from datetime import datetime, timedelta
from ..logger import logger as _logger
import subprocess
import json


class SentimentAgent(BaseAgent):
    """情绪Agent - 分析市场情绪和热点"""
    
    def __init__(self):
        super().__init__("情绪Agent")
    
    def get_system_prompt(self) -> str:
        return """你是资深市场情绪分析师，专门分析A股市场情绪和热点板块。

你的职责：
1. 分析热点板块持续性
2. 识别市场主线
3. 判断资金活跃度
4. 评估市场情绪（亢奋/谨慎/恐慌）

输出格式要求：
- 用中文输出
- 数据要具体
- 给出明确判断"""
    
    def analyze(self, stock_code: str = None, **kwargs) -> str:
        """分析市场情绪"""
        _logger.info(f"😀 SentimentAgent 开始分析: {stock_code or '大盘'}")
        
        # 获取数据
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        sectors_today = get_hot_sectors(date=today, limit=15)
        sectors_yest = get_hot_sectors(date=yesterday, limit=15)
        lhbs = get_lhb_data(limit=30)
        
        _logger.info(f"😀 SentimentAgent 数据获取完成: {stock_code or '大盘'}")
        
        # 准备数据
        data = {
            'sectors_today': [dict(s) for s in sectors_today] if sectors_today else [],
            'sectors_yest': [dict(s) for s in sectors_yest] if sectors_yest else [],
            'lhb': [dict(l) for l in lhbs] if lhbs else []
        }
        
        # 生成key
        prompt = "分析市场情绪："
        cache_key = get_cache_key(data, prompt)
        
        # 尝试缓存 (1天)
        cached = get_cached_result(cache_key, max_age_days=CACHE_CONFIG['sentiment_agent'])
        if cached:
            return f"[情绪Agent - 缓存]\n{cached}"
        
        # 尝试搜索实时热点
        search_result = self._search_hot()
        
        # 构建提示词
        prompt = self._build_prompt(data, search_result)
        
        # 调用LLM
        result = self.call_llm(prompt)
        
        # 缓存
        save_cache(cache_key, result)
        
        return self.format_output("🎯 市场情绪分析", result)
    
    def _search_hot(self) -> str:
        """搜索实时热点"""
        return ""  # 暂时禁用MCP搜索，避免挂起
        # try:
        #     result = subprocess.run(
        #         ['mcporter', 'call', 'minimax.web_search', 
        #          '--output', 'json', 'query=A股 今日热点板块主线'],
        #         capture_output=True,
        #         text=True,
        #         timeout=10,  # 缩短超时
        #         cwd='/home/lijiang/.openclaw/workspace'
        #     )
        #     output = result.stdout
        #     if output and 'error' not in output:
        #         data = json.loads(output)
        #         items = data.get('data', []) or data.get('organic', [])
        #         if items:
        #             lines = ["实时热点搜索:"]
        #             for item in items[:5]:
        #                 title = item.get('title', '')[:50]
        #                 lines.append(f"- {title}")
        #             return '\n'.join(lines)
        # except:
        #     pass
        return ""
    
    def _build_prompt(self, data: dict, search_result: str = "") -> str:
        """构建提示词"""
        sectors_today = data.get('sectors_today', [])
        sectors_yest = data.get('sectors_yest', [])
        lhbs = data.get('lhb', [])
        
        # 热点板块
        sector_info = "今日热点板块(按涨幅):\n"
        for i, s in enumerate(sectors_today[:8]):
            name = s.get('sector_name', '')
            change = s.get('change_percent', 0)
            sector_info += f"- {name}: {change:+.2f}%\n"
        
        # 跨日趋势
        today_names = {s.get('sector_name', '') for s in sectors_today[:10]}
        yest_names = {s.get('sector_name', '') for s in sectors_yest[:10]}
        main_line = today_names & yest_names
        
        trend_info = "\n连续2天热点:\n"
        if main_line:
            for name in list(main_line)[:5]:
                trend_info += f"- {name}\n"
        else:
            trend_info += "无\n"
        
        # 龙虎榜
        buy_count = sum(1 for l in lhbs[:15] if '买入' in str(l.get('net_amount', '')))
        sell_count = len(lhbs[:15]) - buy_count
        
        lhb_info = f"\n龙虎榜: 买入{buy_count}次, 卖出{sell_count}次\n"
        
        prompt = f"""{sector_info}{trend_info}{lhb_info}

{search_result}

请分析：
1. 当前市场主线（哪些板块持续热）
2. 市场情绪（亢奋/谨慎/恐慌/中性）
3. 资金活跃度
4. 操作建议（进攻/防守/观望）

注意：只输出分析结论。"""
        
        return prompt


def analyze_sentiment(stock_code: str = None) -> str:
    """便捷函数"""
    return SentimentAgent().analyze(stock_code)
