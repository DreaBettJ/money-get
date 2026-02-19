"""批量回测系统"""
import logging
from money_get.backtest import TimeMachine, BacktestEngine
from money_get.core.db import get_connection
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


def get_available_dates(code: str, min_count: int = 10) -> list:
    """获取有足够数据的回测日期"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT date FROM daily_kline
        WHERE code = ?
        ORDER BY date DESC
        LIMIT 100
    """, (code,))
    
    dates = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    # 排除最后几天（没有次日数据）
    return dates[min_count:]


def simple_strategy(code: str, date: str) -> str:
    """简单策略
    
    基于历史数据做出决策：
    - 资金流入 + 涨幅<5% → 买入
    - 涨幅>5% → 卖出/持有
    - 资金流出 → 观望
    """
    tm = TimeMachine(date)
    
    # 获取数据
    funds = tm.get_fund_flow(code)
    klines = tm.get_kline(code)
    
    if not klines:
        return 'hold'
    
    # 计算近期涨幅
    if len(klines) >= 2:
        change = (klines[0]['close'] - klines[-1]['close']) / klines[-1]['close'] * 100
    else:
        change = 0
    
    # 资金流向
    has_fund_inflow = funds and funds[0].get('main_net_inflow', 0) > 0
    
    # 决策逻辑
    if has_fund_inflow and change < 5:
        return 'buy'
    elif change > 8:
        return 'sell'
    else:
        return 'hold'


def run_batch_backtest(
    code: str, 
    start_date: str = None,
    end_date: str = None,
    days: int = 30
) -> dict:
    """批量回测
    
    Args:
        code: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        days: 回测天数
        
    Returns:
        dict: 回测结果
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"📊 批量回测 - {code}")
    logger.info(f"{'='*60}")
    
    # 获取可用日期
    available_dates = get_available_dates(code)
    
    if not available_dates:
        return {'error': '无可用数据'}
    
    logger.info(f"可用日期: {len(available_dates)}天")
    
    # 确定回测范围
    if end_date:
        end_idx = available_dates.index(end_date) if end_date in available_dates else 0
    else:
        end_idx = 0
    
    if start_date:
        start_idx = available_dates.index(start_date) if start_date in available_dates else days
    else:
        start_idx = min(days, end_idx)
    
    test_dates = available_dates[start_idx:end_idx]
    logger.info(f"回测范围: {test_dates[-1]} ~ {test_dates[0]} ({len(test_dates)}天)")
    
    # 运行回测
    engine = BacktestEngine(10000)
    results = []
    
    for date in test_dates:
        # 策略决策
        decision = simple_strategy(code, date)
        
        # 执行回测
        result = engine.run_single(code, decision, date)
        results.append(result)
        
        logger.info(f"  {date}: {decision} → 次日涨跌: {result.get('profit_pct', 0):.2f}%")
    
    # 统计
    stats = engine.get_stats()
    
    logger.info(f"\n{'='*60}")
    logger.info(f"📈 回测统计")
    logger.info(f"{'='*60}")
    logger.info(f"总决策: {stats['total_decisions']}")
    logger.info(f"买入次数: {stats['buy_decisions']}")
    logger.info(f"正确次数: {stats['correct']}")
    logger.info(f"胜率: {stats['win_rate']:.1f}%")
    logger.info(f"平均收益: {stats['avg_profit']:.3f}%")
    
    return {
        'code': code,
        'dates': test_dates,
        'results': results,
        'stats': stats
    }


def run_multi_stock_backtest(codes: list, days: int = 30) -> dict:
    """多股票回测
    
    Args:
        codes: 股票列表
        days: 每只股票回测天数
        
    Returns:
        dict: 综合回测结果
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"📊 多股票批量回测")
    logger.info(f"{'='*60}")
    logger.info(f"股票数: {len(codes)}")
    logger.info(f"每只回测: {days}天")
    
    all_stats = []
    
    for code in codes:
        try:
            result = run_batch_backtest(code, days=days)
            if 'error' not in result:
                all_stats.append(result['stats'])
        except Exception as e:
            logger.info(f"{code}: 错误 - {e}")
    
    # 汇总统计
    if not all_stats:
        return {'error': '无有效回测结果'}
    
    total_decisions = sum(s['total_decisions'] for s in all_stats)
    total_buy = sum(s['buy_decisions'] for s in all_stats)
    total_correct = sum(s['correct'] for s in all_stats)
    avg_profit = sum(s['avg_profit'] for s in all_stats) / len(all_stats)
    
    overall_win_rate = total_correct / total_buy * 100 if total_buy > 0 else 0
    
    logger.info(f"\n{'='*60}")
    logger.info(f"📈 汇总统计")
    logger.info(f"{'='*60}")
    logger.info(f"股票数: {len(all_stats)}")
    logger.info(f"总决策: {total_decisions}")
    logger.info(f"总买入: {total_buy}")
    logger.info(f"总正确: {total_correct}")
    logger.info(f"总体胜率: {overall_win_rate:.1f}%")
    logger.info(f"平均收益: {avg_profit:.3f}%")
    
    return {
        'stocks': len(all_stats),
        'total_decisions': total_decisions,
        'total_buy': total_buy,
        'total_correct': total_correct,
        'win_rate': overall_win_rate,
        'avg_profit': avg_profit,
        'details': all_stats
    }


# ============ 示例 ============
if __name__ == "__main__":
    # 单股票回测
    logger.info("=== 单股票回测 ===")
    result = run_batch_backtest('600519', days=10)
    
    # 多股票回测
    logger.info("\n=== 多股票回测 ===")
    result = run_multi_stock_backtest(['600519', '300719'], days=10)
