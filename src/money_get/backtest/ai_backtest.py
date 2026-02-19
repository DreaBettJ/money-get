"""智能选股系统回测 - 验证AI决策准确性"""
import logging
from money_get.backtest import TimeMachine, BacktestEngine
from money_get.core.db import get_connection
from money_get.core.scraper import get_stock_price
import json

# 创建日志
logger = logging.getLogger('money_get.ai_backtest')
if not logger.handlers:
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler('/home/lijiang/code/money-get/logs/ai_backtest.log')
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    # 同时输出到控制台
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(console)


class AIBacktest:
    """AI决策回测"""
    
    def __init__(self, initial_capital: float = 10000):
        self.engine = BacktestEngine(initial_capital)
        self.decisions = []
    
    def analyze_with_timemachine(self, code: str, date: str) -> dict:
        """使用时光机进行AI分析
        
        只能在回测日期前后7天内获取数据
        """
        tm = TimeMachine(date)
        
        # 1. 获取历史K线
        klines = tm.get_kline(code)
        
        # 2. 获取资金流
        funds = tm.get_fund_flow(code)
        
        # 3. 获取新闻
        news = tm.get_news(code)
        
        # 4. 获取当日收盘价
        current = tm.get_price(code)
        
        # 5. 简单AI分析（基于因子）
        decision = self._simple_ai_analysis(klines, funds, news, current)
        
        return {
            'date': date,
            'code': code,
            'klines': klines,
            'funds': funds,
            'news': news,
            'current_price': current,
            'decision': decision
        }
    
    def _simple_ai_analysis(self, klines: list, funds: list, news: list, current: dict) -> str:
        """简单AI分析逻辑
        
        基于因子评分做出决策
        """
        score = 0
        reasons = []
        
        # 1. 资金因子 (25%) - 如果有数据
        if funds:
            main_net = funds[0].get('main_net_inflow', 0) or 0
            if main_net > 500:
                score += 25
                reasons.append(f"主力净流入{main_net:.0f}")
            elif main_net > 0:
                score += 10
                reasons.append("主力资金正流入")
        
        # 2. 动量因子 (35%) - 基于K线
        if klines and len(klines) >= 5:
            # 计算5日涨幅
            change = (klines[0]['close'] - klines[-1]['close']) / klines[-1]['close'] * 100
            
            if -3 <= change <= 5:
                score += 35
                reasons.append(f"温和涨跌{change:.1f}%")
            elif change < -3:
                score += 20
                reasons.append(f"超跌{change:.1f}%")
            elif change > 10:
                score -= 15
                reasons.append(f"涨幅过大{change:.1f}%")
        
        # 3. 成交量因子 (20%)
        if klines and len(klines) >= 3:
            avg_vol = sum(k['volume'] for k in klines[:3]) / min(3, len(klines))
            if avg_vol > 30000:
                score += 20
                reasons.append("成交量活跃")
        
        # 4. 新闻因子 (20%)
        if news:
            score += 20
            reasons.append(f"有{len(news)}条新闻")
        
        # 默认加分（确保有决策）
        if not reasons:
            score += 30
            reasons.append("数据不足，默认关注")
        
        # 决策
        if score >= 50:
            return 'buy'
        elif score <= 25:
            return 'sell'
        else:
            return 'hold'
    
    def run_single(self, code: str, date: str) -> dict:
        """单次回测"""
        logger.info(f"=== 回测 {code} @ {date} ===")
        
        # 使用时光机分析
        analysis = self.analyze_with_timemachine(code, date)
        
        if not analysis['current_price']:
            logger.warning(f"{date}: 无价格数据")
            return {'error': '无价格数据', 'date': date, 'code': code}
        
        decision = analysis['decision']
        current_price = analysis['current_price']['close']
        
        # 日志记录分析结果
        logger.info(f"日期: {date}")
        logger.info(f"数据: K线{len(analysis['klines'])}条, 资金流{len(analysis['funds'])}条, 新闻{len(analysis['news'])}条")
        logger.info(f"收盘价: {current_price}")
        logger.info(f"决策: {decision}")
        
        # 执行回测
        result = self.engine.run_single(code, decision, date)
        
        # 记录决策 - 使用engine返回的结果
        profit_pct = result.get('profit_pct')
        correct = result.get('correct')
        
        self.decisions.append({
            'date': date,
            'code': code,
            'decision': decision,
            'price': current_price,
            'next_price': result.get('next_price'),
            'profit_pct': profit_pct,
            'correct': correct
        })
        
        # 日志记录结果
        if profit_pct is not None:
            status = "✅" if profit_pct > 0 else "❌"
            logger.info(f"结果: 次日涨跌 {profit_pct:+.2f}% {status}")
        else:
            logger.info(f"结果: 无次日数据")
        
        return result
    
    def run_batch(self, code: str, dates: list) -> dict:
        """批量回测"""
        logger.info("="*60)
        logger.info(f"🤖 AI决策回测 - {code}")
        logger.info("="*60)
        
        success = 0
        fail = 0
        
        for date in dates:
            try:
                result = self.run_single(code, date)
                
                if 'error' not in result:
                    d = self.decisions[-1]
                    profit = d.get('profit_pct')
                    if profit is not None:
                        status = "✅" if profit > 0 else "❌"
                        logger.info(f"  {date}: {d['decision']:4s} → {profit:+.2f}% {status}")
                    else:
                        logger.info(f"  {date}: {d['decision']:4s} → 无次日数据")
                    success += 1
                else:
                    fail += 1
            except Exception as e:
                logger.info(f"  {date}: 错误 - {e}")
                fail += 1
        
        return self.get_stats()
    
    def get_stats(self) -> dict:
        """获取统计"""
        if not self.decisions:
            return {}
        
        buys = [d for d in self.decisions if d['decision'] == 'buy']
        sells = [d for d in self.decisions if d['decision'] == 'sell']
        holds = [d for d in self.decisions if d['decision'] == 'hold']
        
        # 买入正确率 - 基于实际次日涨跌
        buy_with_profit = [d for d in buys if d.get('profit_pct') is not None and d.get('profit_pct') != 0]
        buy_correct = sum(1 for d in buy_with_profit if d.get('profit_pct', 0) > 0)
        
        # 有实际收益的买入
        buy_with_profit_pct = [d['profit_pct'] for d in buy_with_profit]
        buy_win_rate = buy_correct / len(buy_with_profit) * 100 if buy_with_profit else 0
        
        # 平均收益
        avg_profit = sum(buy_with_profit_pct) / len(buy_with_profit_pct) if buy_with_profit_pct else 0
        
        return {
            'total': len(self.decisions),
            'buy': len(buys),
            'sell': len(sells),
            'hold': len(holds),
            'buy_correct': buy_correct,
            'buy_with_profit': len(buy_with_profit),
            'buy_win_rate': buy_win_rate,
            'avg_profit': avg_profit,
            'final_capital': self.engine.capital,
            'decisions': self.decisions
        }


def get_test_dates(code: str, count: int = 20) -> list:
    """获取测试日期"""
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
    
    # 排除最后10天（没有次日验证数据）
    return dates[10:10+count]


def run_ai_backtest(code: str, days: int = 20) -> dict:
    """运行AI回测
    
    Args:
        code: 股票代码
        days: 回测天数
        
    Returns:
        dict: 回测结果
    """
    # 获取测试日期
    dates = get_test_dates(code, days)
    
    if not dates:
        return {'error': '无可用日期'}
    
    logger.info(f"回测日期范围: {dates[-1]} ~ {dates[0]}")
    
    # 运行回测
    backtest = AIBacktest(10000)
    stats = backtest.run_batch(code, dates)
    
    # 打印统计
    logger.info(f"\n{'='*60}")
    logger.info(f"📊 回测统计")
    logger.info(f"{'='*60}")
    logger.info(f"总决策: {stats['total']}")
    logger.info(f"买入: {stats['buy']}")
    logger.info(f"卖出: {stats['sell']}")
    logger.info(f"持有: {stats['hold']}")
    logger.info(f"\n买入统计:")
    logger.info(f"  正确: {stats['buy_correct']}/{stats['buy']}")
    logger.info(f"  胜率: {stats['buy_win_rate']:.1f}%")
    logger.info(f"  平均收益: {stats['avg_profit']:.3f}%")
    logger.info(f"  最终资金: {stats['final_capital']:.2f}元")
    
    return stats


def run_multi_ai_backtest(codes: list, days: int = 20) -> dict:
    """多股票AI回测"""
    logger.info(f"\n{'='*60}")
    logger.info(f"📊 多股票AI回测")
    logger.info(f"{'='*60}")
    
    all_stats = []
    
    for code in codes:
        try:
            logger.info(f"\n--- {code} ---")
            stats = run_ai_backtest(code, days)
            if 'error' not in stats:
                all_stats.append(stats)
        except Exception as e:
            logger.info(f"{code}: 错误 - {e}")
    
    if not all_stats:
        return {'error': '无有效结果'}
    
    # 汇总
    total_buy = sum(s['buy'] for s in all_stats)
    total_correct = sum(s['buy_correct'] for s in all_stats)
    total_profit = sum(s['avg_profit'] * s['buy'] for s in all_stats) / total_buy if total_buy > 0 else 0
    overall_win_rate = total_correct / total_buy * 100 if total_buy > 0 else 0
    
    logger.info(f"\n{'='*60}")
    logger.info(f"📈 总体统计")
    logger.info(f"{'='*60}")
    logger.info(f"股票数: {len(all_stats)}")
    logger.info(f"总买入: {total_buy}")
    logger.info(f"总正确: {total_correct}")
    logger.info(f"总体胜率: {overall_win_rate:.1f}%")
    logger.info(f"平均收益: {total_profit:.3f}%")
    
    return {
        'stocks': len(all_stats),
        'total_buy': total_buy,
        'total_correct': total_correct,
        'win_rate': overall_win_rate,
        'avg_profit': total_profit
    }


# ============ 示例 ============
if __name__ == "__main__":
    # 单股票回测
    logger.info("=== 单股票AI回测 ===")
    run_ai_backtest('600519', 20)
    
    # 多股票回测
    logger.info("\n=== 多股票AI回测 ===")
    run_multi_ai_backtest(['600519', '300719'], 20)
