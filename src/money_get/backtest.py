"""回测系统 - 时间隔离的数据查询"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from money_get.db import get_connection
from money_get.scraper import get_stock_price, get_fund_flow, get_realtime_news
import json


class TimeMachine:
    """时光机 - 回测专用数据查询"""
    
    def __init__(self, backtest_date: str):
        """
        Args:
            backtest_date: 回测日期，格式 YYYY-MM-DD
        """
        self.backtest_date = backtest_date
        self.query_range = 7  # 前后7天
    
    def _get_date_range(self) -> tuple:
        """获取查询日期范围"""
        start = (datetime.strptime(self.backtest_date, '%Y-%m-%d') - timedelta(days=self.query_range)).strftime('%Y-%m-%d')
        end = (datetime.strptime(self.backtest_date, '%Y-%m-%d') + timedelta(days=self.query_range)).strftime('%Y-%m-%d')
        return start, end
    
    def get_kline(self, code: str) -> List[dict]:
        """获取历史K线（时间隔离）
        
        只能获取回测日期前后7天的数据
        """
        start, end = self._get_date_range()
        
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT code, date, open, close, high, low, volume
            FROM daily_kline
            WHERE code = ? AND date BETWEEN ? AND ?
            ORDER BY date
        """, (code, start, end))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'code': row[0],
                'date': row[1],
                'open': row[2],
                'close': row[3],
                'high': row[4],
                'low': row[5],
                'volume': row[6]
            })
        
        conn.close()
        return results
    
    def get_fund_flow(self, code: str) -> List[dict]:
        """获取资金流（时间隔离）"""
        start, end = self._get_date_range()
        
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT code, date, main_net_inflow, small_net_inflow, medium_net_inflow
            FROM fund_flow
            WHERE code = ? AND date BETWEEN ? AND ?
            ORDER BY date
        """, (code, start, end))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'code': row[0],
                'date': row[1],
                'main_net_inflow': row[2],
                'small_net_inflow': row[3],
                'medium_net_inflow': row[4]
            })
        
        conn.close()
        return results
    
    def get_news(self, code: str) -> List[dict]:
        """获取新闻（时间隔离）"""
        start, end = self._get_date_range()
        
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT code, title, pub_date, source
            FROM stock_news
            WHERE code = ? AND pub_date BETWEEN ? AND ?
            ORDER BY pub_date DESC
            LIMIT 20
        """, (code, start, end))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'code': row[0],
                'title': row[1],
                'date': row[2],
                'source': row[3]
            })
        
        conn.close()
        return results
    
    def get_price(self, code: str) -> Optional[dict]:
        """获取回测当日收盘价（用于验证）"""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT code, date, close
            FROM daily_kline
            WHERE code = ? AND date = ?
        """, (code, self.backtest_date))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {'code': row[0], 'date': row[1], 'close': row[2]}
        return None
    
    def get_next_price(self, code: str, days: int = 1) -> Optional[dict]:
        """获取回测次日价格（用于验证）"""
        next_date = (datetime.strptime(self.backtest_date, '%Y-%m-%d') + timedelta(days=days)).strftime('%Y-%m-%d')
        
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT code, date, close
            FROM daily_kline
            WHERE code = ? AND date = ?
        """, (code, next_date))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {'code': row[0], 'date': row[1], 'close': row[2]}
        return None


class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, initial_capital: float = 10000):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.positions = {}  # {code: {'shares': int, 'price': float}}
        self.trades = []  # 交易记录
        self.results = []  # 回测结果
    
    def buy(self, code: str, price: float, date: str):
        """买入"""
        shares = int(self.capital / price / 100) * 100  # 整手
        if shares < 100:
            return False
        
        cost = shares * price
        self.positions[code] = {
            'shares': shares,
            'price': price,
            'date': date
        }
        self.capital -= cost
        
        self.trades.append({
            'date': date,
            'action': 'buy',
            'code': code,
            'price': price,
            'shares': shares,
            'cost': cost
        })
        return True
    
    def sell(self, code: str, price: float, date: str) -> float:
        """卖出"""
        if code not in self.positions:
            return 0
        
        pos = self.positions[code]
        shares = pos['shares']
        revenue = shares * price
        profit = revenue - pos['shares'] * pos['price']
        
        self.capital += revenue
        del self.positions[code]
        
        self.trades.append({
            'date': date,
            'action': 'sell',
            'code': code,
            'price': price,
            'shares': shares,
            'revenue': revenue,
            'profit': profit
        })
        
        return profit
    
    def get_value(self, prices: dict) -> float:
        """计算总资产"""
        position_value = sum(
            pos['shares'] * prices.get(code, 0)
            for code, pos in self.positions.items()
        )
        return self.capital + position_value
    
    def run_single(self, code: str, decision: str, date: str) -> dict:
        """单次回测
        
        Args:
            code: 股票代码
            decision: 决策 (buy/sell/hold)
            date: 回测日期
            
        Returns:
            dict: 回测结果
        """
        tm = TimeMachine(date)
        
        # 获取数据（时间隔离）
        klines = tm.get_kline(code)
        funds = tm.get_fund_flow(code)
        news = tm.get_news(code)
        
        # 当日价格
        current_price = tm.get_price(code)
        if not current_price:
            return {'error': '无当日数据'}
        
        # 次日价格（验证用）
        next_price = tm.get_next_price(code, 1)
        
        # 执行决策
        result = {
            'date': date,
            'code': code,
            'decision': decision,
            'price': current_price['close'],
            'next_price': next_price['close'] if next_price else None,
            'kline_count': len(klines),
            'fund_count': len(funds),
            'news_count': len(news)
        }
        
        if decision == 'buy':
            self.buy(code, current_price['close'], date)
            if next_price:
                # 计算次日收益
                profit_pct = (next_price['close'] - current_price['close']) / current_price['close'] * 100
                result['profit_pct'] = profit_pct
                result['correct'] = profit_pct > 0  # 次日上涨则正确
                
        elif decision == 'sell':
            profit = self.sell(code, current_price['close'], date)
            result['profit'] = profit
        
        self.results.append(result)
        return result
    
    def get_stats(self) -> dict:
        """获取回测统计"""
        if not self.results:
            return {}
        
        total = len(self.results)
        buy_results = [r for r in self.results if r.get('decision') == 'buy']
        
        if buy_results:
            correct = sum(1 for r in buy_results if r.get('correct'))
            avg_profit = sum(r.get('profit_pct', 0) for r in buy_results) / len(buy_results)
            win_rate = correct / len(buy_results) * 100
        else:
            correct = 0
            avg_profit = 0
            win_rate = 0
        
        return {
            'total_decisions': total,
            'buy_decisions': len(buy_results),
            'correct': correct,
            'win_rate': win_rate,
            'avg_profit': avg_profit,
            'final_capital': self.capital + sum(
                pos['shares'] * pos['price'] for pos in self.positions.values()
            ),
            'trades': self.trades
        }


def run_backtest(code: str, dates: List[str]) -> dict:
    """运行回测
    
    Args:
        code: 股票代码
        dates: 回测日期列表
        
    Returns:
        dict: 回测统计
    """
    engine = BacktestEngine(10000)
    
    for date in dates:
        tm = TimeMachine(date)
        
        # 获取数据
        klines = tm.get_kline(code)
        funds = tm.get_fund_flow(code)
        
        # 简单策略：资金流入+涨幅<5% → 买入
        current = tm.get_price(code)
        if not current:
            continue
        
        has_fund = funds and funds[0].get('main_net_inflow', 0) > 0
        change_pct = 0  # 需要从K线计算
        
        if has_fund:
            decision = 'buy'
        else:
            decision = 'hold'
        
        # 执行回测
        engine.run_single(code, decision, date)
    
    return engine.get_stats()


# ============ 示例 ============
if __name__ == "__main__":
    # 测试时光机
    print("=== 测试时光机 ===")
    tm = TimeMachine("2025-06-01")
    
    print(f"回测日期: 2025-06-01")
    print(f"查询范围: {tm._get_date_range()}")
    
    # 获取数据
    klines = tm.get_kline('600519')
    print(f"\nK线数据: {len(klines)}条")
    if klines:
        print(f"  首条: {klines[0]}")
        print(f"  末条: {klines[-1]}")
