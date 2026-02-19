"""策略化回测框架

支持：
1. 自定义入场信号
2. 阶梯止盈
3. 止损
4. 多维度评估
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


class Strategy:
    """交易策略"""
    
    def __init__(
        self,
        name: str = "默认策略",
        # 入场信号
        entry_signals: List[str] = None,
        # 阶梯止盈 [(止盈点, 卖出比例), ...]
        tiers: List[tuple] = None,
        # 止损
        stop_loss: float = -5,
        # 止盈后保本
        trail_stop: float = 0,  # 如 5%，止盈后变成保本
    ):
        self.name = name
        self.entry_signals = entry_signals or ["板块首次启动"]
        self.tiers = tiers or [
            (10, 0.20),   # 10%止盈卖20%
            (15, 0.20),   # 15%止盈卖20%
            (20, 0.20),   # 20%止盈卖20%
            (30, 0.40),   # 30%清仓
        ]
        self.stop_loss = stop_loss
        self.trail_stop = trail_stop
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "entry_signals": self.entry_signals,
            "tiers": self.tiers,
            "stop_loss": self.stop_loss,
            "trail_stop": self.trail_stop
        }
    
    @classmethod
    def from_dict(cls, d: dict) -> 'Strategy':
        return cls(**d)


class BacktestEngine:
    """回测引擎"""
    
    def __init__(
        self,
        initial_capital: float = 10000,
        verbose: bool = True,
        strategy: Strategy = None
    ):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = {}  # {stock: shares}
        self.entry_price = {}  # {stock: 入场价}
        self.peak_price = {}  # {stock: 最高价}
        
        self.trades = []  # 交易记录
        self.signals = []  # 信号记录
        self.daily_values = []  # 每日市值
        
        self.verbose = verbose
        self.strategy = strategy or Strategy()
    
    def reset(self):
        """重置"""
        self.cash = self.initial_capital
        self.positions = {}
        self.entry_price = {}
        self.peak_price = {}
        self.trades = []
        self.signals = []
        self.daily_values = []
    
    def can_buy(self, price: float) -> bool:
        """能否买入（100元起）"""
        return self.cash > 100  # 至少100元
    
    def buy(self, stock: str, price: float, reason: str = ""):
        """买入（按半仓，不整手）"""
        # 按资金比例买入，不整手
        target_amount = self.cash * 0.5
        shares = int(target_amount / price)
        if shares < 1:
            return False
        
        amount = shares * price
        self.cash -= amount
        self.positions[stock] = self.positions.get(stock, 0) + shares
        self.entry_price[stock] = price
        self.peak_price[stock] = price
        
        self.trades.append({
            "date": datetime.now().strftime("%Y-%m-%d"),
            "stock": stock,
            "action": "BUY",
            "price": price,
            "shares": shares,
            "amount": amount,
            "reason": reason
        })
        
        if self.verbose:
            logger.info(f"  ✅ 买入 {stock} @ {price} x {shares}")
        
        return True
    
    def sell(self, stock: str, price: float, shares: int = None, reason: str = ""):
        """卖出"""
        if stock not in self.positions or self.positions[stock] <= 0:
            return False
        
        if shares is None:
            shares = self.positions[stock]
        
        shares = min(shares, self.positions[stock])
        amount = shares * price
        
        self.cash += amount
        self.positions[stock] -= shares
        remaining = self.positions[stock]
        
        self.trades.append({
            "date": datetime.now().strftime("%Y-%m-%d"),
            "stock": stock,
            "action": "SELL",
            "price": price,
            "shares": shares,
            "amount": amount,
            "reason": reason,
            "profit": (price - self.entry_price.get(stock, price)) * shares,
            "profit_pct": (price - self.entry_price.get(stock, price)) / self.entry_price.get(stock, price) * 100
        })
        
        if remaining == 0:
            del self.positions[stock]
            del self.entry_price[stock]
            del self.peak_price[stock]
        
        if self.verbose:
            logger.info(f"  ❌ 卖出 {stock} @ {price} x {shares}")
        
        return True
    
    def check_signals(self, stock: str, price: float, data: dict) -> List[str]:
        """检查是否触发入场信号"""
        signals = []
        
        # 简化：基于数据判断
        # 实际应该让 LLM 判断
        
        # 板块首次启动
        if data.get("is_hot_sector"):
            signals.append("板块首次启动")
        
        # 均线金叉
        ma5 = data.get("ma5", 0)
        ma10 = data.get("ma10", 0)
        ma20 = data.get("ma20", 0)
        if ma5 > ma10 > ma20:
            signals.append("均线金叉")
        
        # MACD金叉
        if data.get("macd", 0) > 0:
            signals.append("MACD金叉")
        
        return signals
    
    def check_exit(self, stock: str, current_price: float) -> tuple:
        """
        检查是否触发出场
        Returns: (action, shares, reason)
        """
        if stock not in self.positions or self.positions[stock] <= 0:
            return None, 0, ""
        
        entry = self.entry_price.get(stock, current_price)
        profit_pct = (current_price - entry) / entry * 100
        
        # 更新最高价
        if current_price > self.peak_price.get(stock, 0):
            self.peak_price[stock] = current_price
        
        # 1. 止损
        if profit_pct <= self.strategy.stop_loss:
            return "STOP_LOSS", self.positions[stock], f"止损 {profit_pct:.1f}%"
        
        # 2. 阶梯止盈
        tiers = self.strategy.tiers
        
        # 检查每档止盈
        for target_profit, sell_pct in tiers:
            # 峰值盈利是否达到目标
            peak_profit = (self.peak_price.get(stock, entry) - entry) / entry * 100
            if peak_profit >= target_profit:
                # 检查是否已触发过这一档（简化）
                shares = int(self.positions[stock] * sell_pct / 100) * 100
                if shares >= 100:
                    return "TAKE_PROFIT", shares, f"止盈 {target_profit}%"
        
        return None, 0, ""
    
    def get_position_value(self, prices: dict) -> float:
        """获取持仓市值"""
        value = 0
        for stock, shares in self.positions.items():
            price = prices.get(stock, 0)
            value += shares * price
        return value
    
    def get_total_value(self, prices: dict) -> float:
        """获取总市值"""
        return self.cash + self.get_position_value(prices)
    
    def evaluate(self) -> dict:
        """评估回测结果"""
        trades = self.trades
        sell_trades = [t for t in trades if t["action"] == "SELL"]
        
        if not sell_trades:
            return {
                "error": "无卖出记录"
            }
        
        # 统计
        wins = 0
        losses = 0
        profits = []
        
        for t in sell_trades:
            profit = t.get("profit", 0)
            profits.append(profit)
            if profit > 0:
                wins += 1
            else:
                losses += 1
        
        total = wins + losses
        win_rate = wins / total * 100 if total > 0 else 0
        
        # 盈亏比
        avg_win = sum(p for p in profits if p > 0) / wins if wins > 0 else 0
        avg_loss = abs(sum(p for p in profits if p < 0) / losses) if losses > 0 else 1
        profit_ratio = avg_win / avg_loss if avg_loss > 0 else 0
        
        # 最大回撤
        peak = self.initial_capital
        max_drawdown = 0
        running = self.initial_capital
        
        for value in self.daily_values:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # 最终收益
        final_value = self.daily_values[-1] if self.daily_values else self.initial_capital
        total_return = (final_value - self.initial_capital) / self.initial_capital * 100
        
        return {
            "initial_capital": self.initial_capital,
            "final_value": final_value,
            "total_return": f"{total_return:.2f}%",
            "total_trades": len(sell_trades),
            "wins": wins,
            "losses": losses,
            "win_rate": f"{win_rate:.1f}%",
            "profit_ratio": f"{profit_ratio:.2f}",
            "avg_win": f"{avg_win:.2f}",
            "avg_loss": f"{avg_loss:.2f}",
            "max_drawdown": f"{max_drawdown:.2f}%",
            "signals_triggered": len(self.signals),
            "trades": trades,  # 返回交易记录
        }
    
    def print_evaluation(self):
        """打印评估结果"""
        ev = self.evaluate()
        
        logger.info("\n" + "="*50)
        logger.info("📊 回测评估")
        logger.info("="*50)
        
        if "error" in ev:
            logger.info(f"❌ {ev['error']}")
            return
        
        logger.info(f"💰 初始资金: {ev['initial_capital']}元")
        logger.info(f"📈 最终市值: {ev['final_value']:.2f}元")
        logger.info(f"📊 总收益: {ev['total_return']}")
        
        logger.info(f"\n📈 交易统计")
        logger.info(f"  - 总交易: {ev['total_trades']}次")
        logger.info(f"  - 盈利: {ev['wins']}次")
        logger.info(f"  - 亏损: {ev['losses']}次")
        logger.info(f"  - 胜率: {ev['win_rate']}")
        
        logger.info(f"\n💹 盈亏")
        logger.info(f"  - 盈亏比: {ev['profit_ratio']}")
        logger.info(f"  - 平均盈利: {ev['avg_win']}元")
        logger.info(f"  - 平均亏损: {ev['avg_loss']}元")
        logger.info(f"  - 最大回撤: {ev['max_drawdown']}")
        
        logger.info(f"\n🔔 信号触发: {ev['signals_triggered']}次")
        
        logger.info("="*50)


def quick_backtest(
    stocks: List[str],
    strategy: Strategy = None,
    start_date: str = "2025-01-01",
    end_date: str = "2025-12-31",
    initial_capital: float = 10000,
    verbose: bool = True
) -> dict:
    """快速回测
    
    Args:
        stocks: 股票列表
        strategy: 策略
        start_date: 开始日期
        end_date: 结束日期
        initial_capital: 初始资金
    
    Returns:
        评估结果
    """
    from money_get.core.db import get_kline
    
    if strategy is None:
        strategy = Strategy()
    
    engine = BacktestEngine(initial_capital, verbose, strategy)
    
    # 按日期遍历
    current = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    
    while current <= end:
        date_str = current.strftime("%Y-%m-%d")
        
        # 获取当日及之前的收盘价（取最近的）
        prices = {}
        for stock in stocks:
            # 获取足够多的历史数据
            klines = get_kline(stock, limit=100)
            for k in klines:
                if k['date'] <= date_str:
                    prices[stock] = k['close']
                    break
        
        if not prices:
            current += timedelta(days=1)
            continue
        
        # 检查持仓
        for stock in list(engine.positions.keys()):
            if stock in prices:
                # 检查出场
                action, shares, reason = engine.check_exit(stock, prices[stock])
                if action:
                    engine.sell(stock, prices[stock], shares, reason)
        
        # 检查入场信号（简化：每天检查一次）
        for stock in stocks:
            if stock in prices and stock not in engine.positions:
                # 简化：每20天尝试入场一次（模拟信号）
                # 实际应该让 LLM 判断信号
                day_num = (current.date() - datetime.strptime(start_date, "%Y-%m-%d").date()).days
                
                # 模拟信号：每20天一次
                if day_num % 20 == 0 and engine.can_buy(prices[stock]):
                    engine.buy(stock, prices[stock], "模拟信号")
        
        # 记录市值
        total = engine.get_total_value(prices)
        engine.daily_values.append(total)
        
        current += timedelta(days=1)
    
    # 最终清仓
    for stock in list(engine.positions.keys()):
        if stock in prices:
            engine.sell(stock, prices[stock], 0, "回测结束")
    
    # 保存回测交易记录到数据库
    result = engine.evaluate()
    
    # 写入数据库
    try:
        from money_get.core.db import insert_trade
        for t in engine.trades:
            insert_trade(
                stock_code=t.get("stock", ""),
                stock_name=t.get("stock", ""),
                direction=t.get("action", "").lower(),
                price=t.get("price", 0),
                quantity=t.get("shares", 0),
                trade_date=t.get("date", ""),
                reason=f"[回测] {t.get('reason', '')}",
                notes=f"策略:{strategy.name if strategy else '默认'}"
            )
        result["saved_trades"] = len(engine.trades)
    except Exception as e:
        result["save_error"] = str(e)
    
    return result


# ==================== 便捷函数 ====================

def run_strategy_backtest(
    stocks: List[str],
    strategy: dict = None,
    **kwargs
) -> dict:
    """运行策略回测"""
    if strategy:
        strat = Strategy.from_dict(strategy)
    else:
        strat = Strategy()
    
    return quick_backtest(stocks, strat, **kwargs)
