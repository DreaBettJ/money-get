"""统一的股票分析 Agent

支持：
1. 普通分析 - 实时数据
2. 回测模式 - 时间旅行
3. 决策仪表盘 - 内置交易纪律
4. 市场情绪分析
5. 回测评估
"""
from typing import List, Dict, Optional
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool


class StockAgent:
    """统一的股票分析 Agent"""
    
    # 内置交易纪律
    BIAS_THRESHOLD = 5  # 乖离率阈值
    
    def __init__(
        self,
        backtest_date: str = None,  # 回测模式：指定日期
        initial_capital: float = 10000,
        verbose: bool = True,
        trace: bool = True
    ):
        """
        Args:
            backtest_date: 回测日期，如 "2025-06-01"，None 表示实时模式
            initial_capital: 初始资金（回测用）
            verbose: 是否打印详情
            trace: 是否追踪到 Langfuse
        """
        self.backtest_date = backtest_date
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.positions = {}  # 持仓
        self.trades = []    # 交易记录
        self.verbose = verbose
        self.trace = trace
        
        # 工具列表
        self.tools = self._create_tools()
    
    def _create_tools(self):
        """创建工具列表"""
        
        @tool
        def get_stock_price(code: str) -> str:
            """获取股票当前价格"""
            from money_get.db import get_kline
            
            limit = 1
            if self.backtest_date:
                # 回测模式：只获取指定日期之前的数据
                klines = self._get_kline_until(code, self.backtest_date, 1)
            else:
                klines = get_kline(code, limit)
            
            if not klines:
                return f"股票 {code} 暂无数据"
            
            k = klines[0]
            change = ((k['close'] - k['open']) / k['open'] * 100)
            return f"{code}: 收盘 {k['close']}元, 涨跌 {change:+.2f}%"
        
        @tool
        def get_stock_kline(code: str, days: int = 30) -> str:
            """获取股票K线数据"""
            if self.backtest_date:
                klines = self._get_kline_until(code, self.backtest_date, days)
            else:
                from money_get.db import get_kline
                klines = get_kline(code, limit=days)
            
            if not klines:
                return f"股票 {code} 暂无数据"
            
            result = f"## {code} K线\n"
            for k in klines[:5]:
                change = ((k['close'] - k['open']) / k['open'] * 100)
                result += f"- {k['date']}: {k['close']:.0f} ({change:+.1f}%)\n"
            return result
        
        @tool
        def get_technical_indicators(code: str) -> str:
            """获取技术指标"""
            if self.backtest_date:
                ind = self._get_indicators_at(code, self.backtest_date)
            else:
                from money_get.db import get_indicators
                ind = get_indicators(code)
            
            if not ind:
                return f"股票 {code} 暂无技术指标"
            
            result = f"## 技术指标\n"
            if ind.get('ma5') and ind.get('ma20'):
                trend = "多头" if ind['ma5'] > ind['ma20'] else "空头"
                result += f"- MA5={ind['ma5']:.0f}, MA20={ind['ma20']:.0f} ({trend})\n"
            if ind.get('macd'):
                signal = "金叉" if ind['macd'] > 0 else "死叉"
                result += f"- MACD={ind['macd']:.2f} ({signal})\n"
            return result
        
        @tool
        def get_fund_flow(code: str, days: int = 5) -> str:
            """获取资金流向"""
            if self.backtest_date:
                flows = self._get_fund_flow_until(code, self.backtest_date, days)
            else:
                from money_get.db import get_fund_flow_data
                flows = get_fund_flow_data(code, limit=days)
            
            if not flows:
                return f"股票 {code} 暂无资金流向"
            
            result = "## 资金流向\n"
            for f in flows[:3]:
                main = f.get('main_net_inflow', 0)
                direction = "净买入" if main > 0 else "净卖出"
                result += f"- {f['date']}: 主力 {main/10000:.1f}万 ({direction})\n"
            return result
        
        @tool
        def get_news(code: str, limit: int = 5) -> str:
            """获取新闻"""
            if self.backtest_date:
                news_list = self._get_news_until(code, self.backtest_date, limit)
            else:
                from money_get.db import get_news
                news_list = get_news(code, limit=limit)
            
            if not news_list:
                return f"股票 {code} 暂无新闻"
            
            result = "## 新闻\n"
            for n in news_list[:3]:
                result += f"- {n.get('title', '')[:40]}\n"
            return result
        
        @tool
        def buy_stock(code: str, price: float, shares: int = 100) -> str:
            """买入股票
            
            Args:
                code: 股票代码
                price: 买入价格
                shares: 股数，默认100股
            """
            if self.backtest_date is None:
                return "❌ 买入功能仅在回测模式可用"
            
            amount = price * shares
            if amount > self.current_capital:
                return f"❌ 资金不足，当前 {self.current_capital:.2f} 元"
            
            self.trades.append({
                "date": self.backtest_date,
                "stock": code,
                "action": "BUY",
                "price": price,
                "shares": shares,
                "amount": amount
            })
            
            self.positions[code] = self.positions.get(code, 0) + shares
            self.current_capital -= amount
            
            return f"✅ 买入 {code} {shares}股 @ {price}元 = {amount:.2f}元"
        
        @tool
        def sell_stock(code: str, price: float) -> str:
            """卖出股票
            
            Args:
                code: 股票代码
                price: 卖出价格
            """
            if self.backtest_date is None:
                return "❌ 卖出功能仅在回测模式可用"
            
            if code not in self.positions or self.positions[code] <= 0:
                return f"❌ {code} 无持仓"
            
            shares = self.positions[code]
            amount = price * shares
            
            self.trades.append({
                "date": self.backtest_date,
                "stock": code,
                "action": "SELL",
                "price": price,
                "shares": shares,
                "amount": amount
            })
            
            self.current_capital += amount
            self.positions[code] = 0
            
            return f"✅ 卖出 {code} {shares}股 @ {price}元 = {amount:.2f}元"
        
        @tool
        def get_position() -> str:
            """获取当前持仓"""
            if not self.positions:
                return "无持仓"
            
            result = "## 当前持仓\n"
            for code, shares in self.positions.items():
                if shares > 0:
                    # 获取当前价格
                    if self.backtest_date:
                        klines = self._get_kline_until(code, self.backtest_date, 1)
                    else:
                        from money_get.db import get_kline
                        klines = get_kline(code, limit=1)
                    
                    price = klines[0]['close'] if klines else 0
                    value = shares * price
                    result += f"- {code}: {shares}股 @ {price:.0f}元 = {value:.0f}元\n"
            
            result += f"\n💰 现金: {self.current_capital:.2f}元"
            return result
        
        @tool
        def get_hot_sectors(limit: int = 10) -> str:
            """获取热点板块
            
            Returns:
                当日热点板块排行
            """
            from money_get.db import get_hot_sectors
            
            if self.backtest_date:
                # 回测模式
                sectors = self._get_sectors_until(self.backtest_date, limit)
            else:
                sectors = get_hot_sectors(limit=limit)
            
            if not sectors:
                return "暂无热点板块数据"
            
            result = "## 热点板块\n"
            for s in sectors[:10]:
                name = s.get('sector_name', '')
                change = s.get('change_percent', 0)
                lead = s.get('lead_stock', '')
                result += f"- {name}: {change:+.2f}% (领涨: {lead})\n"
            return result
        
        @tool
        def search_internet(query: str) -> str:
            """搜索互联网获取信息
            
            用于搜索：
            - 市场主线/热点概念
            - 政策方向
            - 行业动态
            
            Args:
                query: 搜索关键词
            """
            try:
                # 优先使用 MCP MiniMax
                from mcporter import call_minimax_web_search
                result = call_minimax_web_search(query=query)
                
                if result and 'data' in result:
                    items = result['data'][:5]
                    response = f"## 搜索结果: {query}\n\n"
                    for item in items:
                        title = item.get('title', '')
                        snippet = item.get('snippet', '')[:100]
                        url = item.get('url', '')
                        response += f"- {title}\n  {snippet}...\n  来源: {url}\n\n"
                    return response
            except:
                pass
            
            # 备用：直接请求
            try:
                import requests
                url = "https://api.minimax.chat/v1/search"
                # 如果 MCP 不可用，返回提示
                return "搜索功能需要配置 MCP MiniMax，请先配置 mcporter"
            except:
                pass
            
            return "搜索功能暂时不可用"
        
        @tool
        def get_policy_news() -> str:
            """获取政策相关新闻
            
            Returns:
                近期政策动向
            """
            query = "A股 政策 利好 利空"
            return search_internet(query)
        
        @tool
        def get_market_sentiment() -> str:
            """获取市场情绪
            
            Returns:
                市场情绪分析（涨停/跌停数、涨跌家数、资金流向）
            """
            # 从龙虎榜获取市场整体情绪
            if self.backtest_date:
                lhbs = self._get_lhb_until(self.backtest_date, 20)
            else:
                from money_get.db import get_lhb_data
                lhbs = get_lhb_data(limit=20)
            
            result = "## 市场情绪\n"
            
            # 统计买卖方向
            buy_count = 0
            sell_count = 0
            total_net = 0
            
            for l in lhbs[:10]:
                net = l.get('net_amount', '')
                if '净买入' in str(net) or '万' in str(net):
                    buy_count += 1
                elif '净卖出' in str(net):
                    sell_count += 1
            
            result += f"- 龙虎榜统计: 买入 {buy_count} 次, 卖出 {sell_count} 次\n"
            
            # 热点板块情绪
            if self.backtest_date:
                sectors = self._get_sectors_until(self.backtest_date, 5)
            else:
                from money_get.db import get_hot_sectors
                sectors = get_hot_sectors(limit=5)
            
            if sectors:
                up_count = sum(1 for s in sectors if s.get('change_percent', 0) > 0)
                result += f"- 热点板块: {up_count}/{len(sectors)} 上涨\n"
            
            # 总结情绪
            if buy_count > sell_count:
                result += "\n🎯 情绪判断: 偏多（资金活跃）"
            elif sell_count > buy_count:
                result += "\n🎯 情绪判断: 偏空（资金观望）"
            else:
                result += "\n🎯 情绪判断: 中性"
            
            return result
        
        @tool
        def identify_market_theme() -> str:
            """识别当前市场主线热点
            
            结合热点板块、资金流向、龙虎榜、跨日趋势综合判断当前主线
            
            Returns:
                当前市场主线热点分析
            """
            import subprocess
            import json
            from datetime import datetime, timedelta
            
            try:
                from money_get.db import get_hot_sectors, get_lhb_data
                
                # 1. 获取最近3天热点板块
                today = datetime.now().strftime("%Y-%m-%d")
                yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
                
                sectors_today = get_hot_sectors(date=today, limit=15)
                sectors_yest = get_hot_sectors(date=yesterday, limit=15)
                
                response = "## 🔥 当前市场主线热点分析\n\n"
                
                # 2. 热点板块分析
                response += "### 📊 今日热点板块排行\n"
                if sectors_today:
                    for i, s in enumerate(sectors_today[:6], 1):
                        name = s.get('sector_name', '')
                        change = s.get('change_percent', 0)
                        response += f"{i}. {name}: {change:+.2f}%\n"
                
                # 3. 跨日趋势分析
                response += "\n### 📈 跨日趋势（寻找主线）\n"
                
                # 统计哪些板块连续在前列
                today_names = {s.get('sector_name', '') for s in sectors_today[:10]}
                yest_names = {s.get('sector_name', '') for s in sectors_yest[:10]}
                
                # 连续2天在热点前10 = 主线
                main_line = today_names & yest_names
                if main_line:
                    response += "连续2天热点：\n"
                    for name in list(main_line)[:3]:
                        response += f"  ✅ {name}\n"
                else:
                    response += "无明显主线，热点轮动快\n"
                
                # 4. 资金流向
                response += "\n### 💰 资金流向\n"
                lhbs = get_lhb_data(limit=30)
                
                buy_count = 0
                sell_count = 0
                hot_stocks = []
                
                for l in lhbs[:15]:
                    net = str(l.get('net_amount', ''))
                    if '买入' in net or ('万' in net and '卖出' not in net):
                        buy_count += 1
                        hot_stocks.append(l.get('name', ''))
                    else:
                        sell_count += 1
                
                response += f"买入: {buy_count}次, 卖出: {sell_count}次\n"
                if hot_stocks[:3]:
                    response += f"热门股: {', '.join(hot_stocks[:3])}\n"
                
                # 5. 尝试搜索消息面（如果可用）
                response += "\n### 📰 消息面\n"
                try:
                    # 需要在正确目录运行以找到 MCP 配置
                    result = subprocess.run(
                        ['mcporter', 'call', 'minimax.web_search', 
                         '--output', 'json', 'query=A股 今日热点板块 机器人 AI 有色金属'],
                        capture_output=True,
                        text=True,
                        timeout=15,
                        cwd='/home/lijiang/.openclaw/workspace'
                    )
                    output = result.stdout
                    if output and 'error' not in output:
                        data = json.loads(output)
                        items = data.get('data', []) or data.get('organic', [])
                        if items:
                            response += "今日热点：\n"
                            for item in items[:3]:
                                title = item.get('title', '')[:40]
                                response += f"  • {title}\n"
                    else:
                        response += "搜索暂不可用\n"
                except:
                    response += "搜索暂不可用\n"
                
                # 6. 综合判断
                response += "\n---\n## 🎯 主线判断\n"
                
                if sectors_today:
                    sector_str = ','.join([s.get('sector_name', '') for s in sectors_today[:5]])
                    
                    # 关键词匹配
                    themes = []
                    if any(kw in sector_str for kw in ['AI', '算力', '科技', '电子', '计算机', '半导体']):
                        themes.append(("AI/算力", "科技主线"))
                    if any(kw in sector_str for kw in ['新能源', '汽车', '锂电', '电池', '光伏']):
                        themes.append(("新能源车", "产业趋势"))
                    if any(kw in sector_str for kw in ['医药', '医疗', '生物']):
                        themes.append(("医药", "超跌反弹"))
                    if any(kw in sector_str for kw in ['有色', '金属', '黄金', '铜', '稀土']):
                        themes.append(("有色金属", "涨价逻辑"))
                    if any(kw in sector_str for kw in ['军工', '国防', '航天', '航空']):
                        themes.append(("国防军工", "政策催化"))
                    if any(kw in sector_str for kw in ['传媒', '影视', '游戏', '数字']):
                        themes.append(("传媒数字", "消费复苏"))
                    
                    if themes:
                        for i, (name, reason) in enumerate(themes, 1):
                            response += f"{i}. **{name}** - {reason}\n"
                    else:
                        response += "当前热点分散，建议观望\n"
                
                # 7. 操作建议
                response += "\n---\n## 💡 操作建议\n"
                
                if main_line and len(main_line) >= 2:
                    response += "主线明确，可围绕热点板块操作\n"
                else:
                    response += "热点轮动快，建议低吸为主\n"
                
                if buy_count > sell_count:
                    response += "资金活跃，可适当参与\n"
                elif sell_count > buy_count:
                    response += "资金观望，谨慎为主\n"
                
                return response
                
            except Exception as e:
                return f"分析失败: {e}"
                
                return response
                
            except Exception as e:
                return f"分析失败: {e}"
        
        return [get_stock_price, get_stock_kline, get_technical_indicators, 
                get_fund_flow, get_news, buy_stock, sell_stock, get_position,
                get_hot_sectors, search_internet, get_policy_news, get_market_sentiment,
                identify_market_theme]
    
    # ==================== 数据查询 ====================
    
    def _get_kline_until(self, code: str, end_date: str, limit: int) -> List[Dict]:
        """获取指定日期之前的K线"""
        from money_get.db import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT date, open, close, high, low, volume
            FROM daily_kline
            WHERE code = ? AND date <= ?
            ORDER BY date DESC
            LIMIT ?
        """, (code, end_date, limit))
        conn.close()
        return [dict(row) for row in cursor.fetchall()]
    
    def _get_indicators_at(self, code: str, date: str) -> Optional[Dict]:
        """获取指定日期的指标"""
        from money_get.db import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM indicators
            WHERE code = ? AND date <= ?
            ORDER BY date DESC LIMIT 1
        """, (code, date))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    def _get_fund_flow_until(self, code: str, end_date: str, limit: int) -> List[Dict]:
        """获取指定日期之前的资金流向"""
        from money_get.db import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM fund_flow
            WHERE code = ? AND date <= ?
            ORDER BY date DESC LIMIT ?
        """, (code, end_date, limit))
        conn.close()
        return [dict(row) for row in cursor.fetchall()]
    
    def _get_news_until(self, code: str, end_date: str, limit: int) -> List[Dict]:
        """获取指定日期之前的新闻"""
        from money_get.db import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT title, pub_date FROM stock_news
            WHERE code = ? AND (pub_date <= ? OR pub_date IS NULL)
            ORDER BY pub_date DESC LIMIT ?
        """, (code, end_date, limit))
        conn.close()
        return [dict(row) for row in cursor.fetchall()]
    
    def _get_lhb_until(self, end_date: str, limit: int) -> List[Dict]:
        """获取指定日期之前的龙虎榜"""
        from money_get.db import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM lhb_data
            WHERE date <= ?
            ORDER BY date DESC
            LIMIT ?
        """, (end_date, limit))
        conn.close()
        return [dict(row) for row in cursor.fetchall()]
    
    def _get_sectors_until(self, end_date: str, limit: int) -> List[Dict]:
        """获取指定日期之前的热点板块"""
        from money_get.db import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT sector_name, change_percent, lead_stock
            FROM hot_sectors
            WHERE date <= ?
            ORDER BY date DESC, change_percent DESC
            LIMIT ?
        """, (end_date, limit))
        conn.close()
        return [dict(row) for row in cursor.fetchall()]
    
    # ==================== 核心方法 ====================
    
    def analyze(self, stock_code: str, question: str = None) -> str:
        """分析股票
        
        Args:
            stock_code: 股票代码
            question: 问题
        
        Returns:
            分析结果
        """
        from money_get.llm import get_llm
        from money_get.memory import get_principles, get_patterns
        
        # 获取原则和规律
        principles = get_principles() or "只买行业龙头，不追高只低吸"
        patterns = get_patterns() or "MA5上穿MA20是买入信号"
        
        # 构建 system prompt
        mode = f"[回测模式 - 当前日期: {self.backtest_date}]" if self.backtest_date else "[实时模式]"
        
        system_prompt = f"""你是一位专业的A股交易员。

{mode}

## 用户投资原则
{principles}

## 历史规律
{patterns}

你可以使用以下工具：
- get_stock_price: 获取当前价格
- get_stock_kline: 获取K线数据
- get_technical_indicators: 获取技术指标
- get_fund_flow: 获取资金流向
- get_news: 获取新闻
- get_hot_sectors: 获取热点板块
- search_internet: 搜索互联网（市场主线、政策方向）
- get_policy_news: 获取政策相关新闻
- buy_stock: 买入股票（仅回测模式）
- sell_stock: 卖出股票（仅回测模式）
- get_position: 获取当前持仓

请根据问题调用相关工具进行分析，考虑：
1. 市场主线/热点板块（该股票是否在主线上）
2. 政策方向（是否有利好/利空）
3. 市场情绪（资金活跃度）
4. 技术面（均线、MACD等）
5. 资金面（主力动向）

【重要】输出格式要求：
最后必须输出「决策仪表盘」，格式如下：

🎯 决策仪表盘
📊 分析结果
- 股票: [代码]
- 评分: [0-100分]
- 建议: [买入/卖出/观望]

✅ 检查清单（每项标记满足/注意/不满足）
- [ ] 行业龙头
- [ ] 均线多头(MA5>MA10>MA20)
- [ ] MACD金叉
- [ ] 乖离率<5%（严禁追高）
- [ ] 主力净流入
- [ ] 在市场主线上

🚨 风险提示（如有）

🎯 精确点位
- 买入价: [价格]
- 止损价: [价格]
- 目标价: [价格]
"""
        
        # 构建消息
        messages = [SystemMessage(content=system_prompt)]
        
        user_q = question or f"请分析股票 {stock_code}，给出买卖建议"
        messages.append(HumanMessage(content=user_q))
        
        # 获取 LLM
        llm = get_llm(
            temperature=0.1,
            thinking=True,
            trace=self.trace,
            verbose=self.verbose
        ).bind_tools(self.tools)
        
        # 调用
        response = llm.invoke(messages)
        
        return response.content if hasattr(response, 'content') else str(response)
    
    def run_backtest(self, stocks: List[str], weeks: int = 52) -> Dict:
        """运行回测
        
        Args:
            stocks: 股票列表
            weeks: 回测周数
        
        Returns:
            回测结果
        """
        from datetime import datetime, timedelta
        
        # 从 2025-01-01 开始
        current_date = datetime(2025, 1, 1)
        
        results = []
        
        for week in range(weeks):
            date_str = current_date.strftime("%Y-%m-%d")
            
            if self.verbose:
                print(f"\n{'='*50}")
                print(f"第 {week + 1} 周: {date_str}")
                print(f"{'='*50}")
            
            # 分析每只股票
            for stock in stocks:
                result = self.analyze(stock)
                results.append({
                    "date": date_str,
                    "stock": stock,
                    "result": result[:200]
                })
            
            # 推进一周
            current_date += timedelta(days=7)
            
            # 更新回测日期
            self.backtest_date = date_str
        
        # 评估回测结果
        evaluation = self._evaluate_backtest()
        
        # 总结
        return {
            "initial_capital": self.initial_capital,
            "current_capital": self.current_capital,
            "positions": self.positions,
            "trades": self.trades,
            "results": results,
            "total_return": (self.current_capital - self.initial_capital) / self.initial_capital * 100,
            "evaluation": evaluation
        }
    
    def _evaluate_backtest(self) -> Dict:
        """评估回测结果"""
        trades = self.trades
        
        if not trades:
            return {"error": "暂无交易记录"}
        
        # 配对买卖
        buy_trades = {}  # {stock: [trade]}
        sell_trades = {}
        
        for t in trades:
            stock = t["stock"]
            if t["action"] == "BUY":
                if stock not in buy_trades:
                    buy_trades[stock] = []
                buy_trades[stock].append(t)
            else:
                if stock not in sell_trades:
                    sell_trades[stock] = []
                sell_trades[stock].append(t)
        
        # 计算盈亏
        wins = 0
        losses = 0
        profits = []
        
        for stock, sells in sell_trades.items():
            buys = buy_trades.get(stock, [])
            for i, sell in enumerate(sells):
                if i < len(buys):
                    profit = sell["amount"] - buys[i]["amount"]
                    profits.append(profit)
                    if profit > 0:
                        wins += 1
                    else:
                        losses += 1
        
        total = wins + losses
        win_rate = wins / total * 100 if total > 0 else 0
        
        return {
            "total_trades": len(trades),
            "wins": wins,
            "losses": losses,
            "win_rate": f"{win_rate:.1f}%",
            "total_profit": sum(profits),
            "avg_profit": sum(profits) / len(profits) if profits else 0,
            "max_profit": max(profits) if profits else 0,
            "max_loss": min(profits) if profits else 0
        }


# ==================== 便捷函数 ====================

def analyze(stock_code: str, question: str = None) -> str:
    """实时分析"""
    agent = StockAgent(backtest_date=None)
    return agent.analyze(stock_code, question)


def backtest(stocks: List[str], weeks: int = 52, initial_capital: float = 10000) -> Dict:
    """运行回测
    
    Args:
        stocks: 股票列表
        weeks: 周数
        initial_capital: 初始资金
    """
    agent = StockAgent(
        backtest_date="2025-01-01",
        initial_capital=initial_capital,
        verbose=True,
        trace=True
    )
    return agent.run_backtest(stocks, weeks)
