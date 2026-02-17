"""交易记录"""
from dataclasses import dataclass, asdict
from typing import Optional

from money_get.config import TRADES_FILE
from money_get.data.storage import load_json, append_json


@dataclass
class Trade:
    """交易记录模型"""

    stock_code: str
    stock_name: str
    direction: str  # "buy" / "sell"
    price: float
    quantity: int
    date: str
    reason: str = ""
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def save_trade(trade: Trade) -> None:
    """保存交易记录"""
    append_json(TRADES_FILE, trade.to_dict())


def get_trades(stock_code: Optional[str] = None) -> list:
    """获取交易记录"""
    trades = load_json(TRADES_FILE)

    if stock_code:
        trades = [t for t in trades if t.get("stock_code") == stock_code]

    return trades


def get_stats() -> dict:
    """获取统计信息"""
    trades = get_trades()

    if not trades:
        return {
            "total": 0,
            "win_rate": 0,
            "profit_ratio": 0,
        }

    # 按股票配对计算盈亏
    positions = {}
    wins = 0
    losses = 0
    total_profit = 0
    total_loss = 0

    for t in trades:
        code = t["stock_code"]
        direction = t["direction"]
        price = t["price"]
        quantity = t["quantity"]

        if direction == "buy":
            if code not in positions:
                positions[code] = []
            positions[code].append({"price": price, "quantity": quantity})
        else:  # sell
            if code in positions and positions[code]:
                buy = positions[code].pop(0)
                profit = (price - buy["price"]) * quantity
                if profit > 0:
                    wins += 1
                    total_profit += profit
                else:
                    losses += 1
                    total_loss += abs(profit)

    total = wins + losses
    win_rate = wins / total if total > 0 else 0
    profit_ratio = total_profit / total_loss if total_loss > 0 else 0

    return {
        "total": total,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "profit_ratio": profit_ratio,
    }
