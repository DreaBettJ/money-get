"""股票分析 CLI 入口。"""
import argparse
import json
from datetime import datetime
from pathlib import Path

from money_get.agent import StockAgent
from money_get.backtest.strategy import Strategy, quick_backtest
from money_get.logger import get_logger, log_trade

logger = get_logger("money_get.cli")


def load_trades():
    """加载交易记录"""
    path = Path(__file__).parent.parent.parent / "data" / "trades.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f).get("trades", [])
    return []


def save_trades(trades):
    """保存交易记录"""
    path = Path(__file__).parent.parent.parent / "data" / "trades.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"trades": trades}, f, ensure_ascii=False, indent=2)


def cmd_buy(args):
    """买入命令"""
    trade = {
        "code": args.code,
        "action": "买入",
        "price": args.price,
        "quantity": args.quantity,
        "reason": args.reason or "",
        "date": args.date or datetime.now().strftime("%Y-%m-%d"),
        "recorded_at": datetime.now().isoformat()
    }
    trades = load_trades()
    trades.append(trade)
    save_trades(trades)
    
    # 记录日志
    log_trade("买入", args.code, args.price, args.quantity, args.reason or "")
    logger.info(f"买入: {args.code} x {args.quantity} @ {args.price}")
    
    print(f"✅ 已记录买入: {args.code} x {args.quantity} @ {args.price}")


def cmd_sell(args):
    """卖出命令"""
    trade = {
        "code": args.code,
        "action": "卖出",
        "price": args.price,
        "quantity": args.quantity,
        "reason": args.reason or "",
        "date": args.date or datetime.now().strftime("%Y-%m-%d"),
        "recorded_at": datetime.now().isoformat()
    }
    trades = load_trades()
    trades.append(trade)
    save_trades(trades)
    
    # 记录日志
    log_trade("卖出", args.code, args.price, args.quantity, args.reason or "")
    logger.info(f"卖出: {args.code} x {args.quantity} @ {args.price}")
    
    print(f"✅ 已记录卖出: {args.code} x {args.quantity} @ {args.price}")


def cmd_portfolio(args):
    """查看持仓"""
    trades = load_trades()
    
    # 计算持仓
    holdings = {}
    for t in trades:
        code = t.get("code") or t.get("stock_code", "")
        if not code:
            continue
        action = t.get("action") or t.get("direction", "")
        qty = t.get("quantity", 0)
        price = t.get("price", 0)
        
        if action in ["买入", "buy"]:
            if code not in holdings:
                holdings[code] = {"qty": 0, "cost": 0}
            holdings[code]["qty"] += qty
            holdings[code]["cost"] += price * qty
        elif action in ["卖出", "sell"]:
            if code in holdings:
                holdings[code]["qty"] -= qty
                if holdings[code]["qty"] <= 0:
                    del holdings[code]
    
    if not holdings:
        print("📭 当前无持仓")
        return
    
    print("=" * 50)
    print("📊 当前持仓")
    print("=" * 50)
    total_value = 0
    total_cost = 0
    for code, h in holdings.items():
        qty = h["qty"]
        cost = h["cost"]
        avg_cost = cost / qty if qty > 0 else 0
        print(f"{code}: {qty}股 | 成本: {avg_cost:.2f}元 | 总成本: {cost:.2f}元")
        total_cost += cost
    print("-" * 50)
    print(f"总成本: {total_cost:.2f}元")


def cmd_stats(args):
    """交易统计"""
    trades = load_trades()
    if not trades:
        print("📭 暂无交易记录")
        return
    
    buys = [t for t in trades if t.get("action") in ["买入", "buy"]]
    sells = [t for t in trades if t.get("action") in ["卖出", "sell"]]
    
    print("=" * 50)
    print("📈 交易统计")
    print("=" * 50)
    print(f"总交易次数: {len(trades)}")
    print(f"买入次数: {len(buys)}")
    print(f"卖出次数: {len(sells)}")
    
    # 简单统计
    total_buy = sum(t.get("price", 0) * t.get("quantity", 0) for t in buys)
    total_sell = sum(t.get("price", 0) * t.get("quantity", 0) for t in sells)
    print(f"\n买入总额: {total_buy:.2f}元")
    print(f"卖出总额: {total_sell:.2f}元")
    if total_buy > 0:
        print(f"持仓成本: {total_buy - total_sell:.2f}元")


def cmd_list(args):
    """列出交易记录"""
    trades = load_trades()
    if not trades:
        print("📭 暂无交易记录")
        return
    
    print("=" * 50)
    print("📋 交易记录")
    print("=" * 50)
    for i, t in enumerate(trades[-10:], 1):
        code = t.get("code") or t.get("stock_code", "")
        action = t.get("action") or t.get("direction", "")
        price = t.get("price", 0)
        qty = t.get("quantity", 0)
        date = t.get("date", "")
        reason = t.get("reason", "")
        print(f"{i}. {date} | {code} | {action} {qty}股 @{price} | {reason}")


def cli() -> None:
    # 主 parser
    parser = argparse.ArgumentParser(description="股票分析 CLI")
    parser.add_argument("--stock", "-s", help="股票代码")
    parser.add_argument("--hot", action="store_true", help="查看热点板块")
    parser.add_argument("--backtest", "-b", action="store_true", help="回测模式")
    parser.add_argument("--reco", "-r", action="store_true", help="推荐股票")
    parser.add_argument("--eval", "-e", action="store_true", help="策略回测评估")
    parser.add_argument("--weeks", "-w", type=int, default=52, help="回测周数")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    parser.add_argument("--no-trace", action="store_true", help="不追踪")
    
    # 子命令
    subparsers = parser.add_subparsers(title="子命令", dest="cmd")
    
    # buy 子命令
    buy_parser = subparsers.add_parser("buy", help="记录买入")
    buy_parser.add_argument("code", help="股票代码")
    buy_parser.add_argument("price", type=float, help="买入价格")
    buy_parser.add_argument("quantity", type=int, help="数量")
    buy_parser.add_argument("--reason", help="买入理由")
    buy_parser.add_argument("--date", help="日期 YYYY-MM-DD")
    
    # sell 子命令
    sell_parser = subparsers.add_parser("sell", help="记录卖出")
    sell_parser.add_argument("code", help="股票代码")
    sell_parser.add_argument("price", type=float, help="卖出价格")
    sell_parser.add_argument("quantity", type=int, help="数量")
    sell_parser.add_argument("--reason", help="卖出理由")
    sell_parser.add_argument("--date", help="日期 YYYY-MM-DD")
    
    # portfolio 子命令
    subparsers.add_parser("portfolio", help="查看持仓")
    
    # stats 子命令
    subparsers.add_parser("stats", help="交易统计")
    
    # list 子命令
    subparsers.add_parser("list", help="列出交易记录")
    
    args = parser.parse_args()
    
    # 处理子命令
    if args.cmd == "buy":
        cmd_buy(args)
        return
    if args.cmd == "sell":
        cmd_sell(args)
        return
    if args.cmd == "portfolio":
        cmd_portfolio(args)
        return
    if args.cmd == "stats":
        cmd_stats(args)
        return
    if args.cmd == "list":
        cmd_list(args)
        return

    verbose = args.verbose
    trace = not args.no_trace

    if args.eval:
        print("=" * 50)
        print("📊 策略回测评估")
        print("=" * 50)
        strategies = [
            Strategy("默认策略", tiers=[(10, 0.20), (15, 0.20), (20, 0.20), (30, 0.40)], stop_loss=-5),
            Strategy("激进策略", tiers=[(8, 0.25), (15, 0.25), (25, 0.50)], stop_loss=-7),
            Strategy("保守策略", tiers=[(5, 0.20), (10, 0.30), (15, 0.50)], stop_loss=-3),
        ]
        stocks = ["600519", "000858", "300750"]
        results = []
        for strat in strategies:
            print(f"\n🔄 测试策略: {strat.name}")
            result = quick_backtest(
                stocks=stocks,
                strategy=strat,
                start_date="2025-01-01",
                end_date="2025-12-31",
                initial_capital=10000,
                verbose=False,
            )
            results.append((strat.name, result))

        print("\n" + "=" * 50)
        print("📈 策略对比")
        print("=" * 50)
        for name, res in results:
            print(f"\n【{name}】")
            if "error" in res:
                print(f"  ❌ {res['error']}")
            else:
                print(f"  收益: {res.get('total_return', 'N/A')}")
                print(f"  胜率: {res.get('win_rate', 'N/A')}")
                print(f"  盈亏比: {res.get('profit_ratio', 'N/A')}")
                print(f"  最大回撤: {res.get('max_drawdown', 'N/A')}")
        return

    if args.hot:
        print("=" * 50)
        print("🔥 热点板块")
        print("=" * 50)
        agent = StockAgent(verbose=verbose, trace=trace)
        print(agent.analyze("大盘", "有哪些热点板块？"))
        return

    if args.reco:
        print("=" * 50)
        print("🎯 智能选股（4层过滤 + LLM分析）")
        print("=" * 50)
        
        # 使用新的selector选股
        from money_get.selector import select_stocks
        
        # 先规则过滤
        print("\n📋 规则过滤选股...")
        stocks = select_stocks(
            use_policy=True,
            use_llm=False,
            top_n=10
        )
        
        if not stocks:
            print("无符合条件股票")
            return
        
        print(f"\n规则筛选出 {len(stocks)} 只候选股")
        
        # 如果开启LLM分析
        use_llm = True
        if use_llm:
            print("\n🤖 LLM深度分析...")
            stocks = select_stocks(
                use_policy=True,
                use_llm=True,
                top_n=5
            )
        
        # 打印结果
        print("\n" + "=" * 50)
        print("📊 推荐结果")
        print("=" * 50)
        
        for idx, s in enumerate(stocks, 1):
            code = s.get('code', '')
            name = s.get('name', '')
            llm_rec = s.get('llm_recommendation', '未知')
            inflow = s.get('inflow', {}).get('consecutive_days', 0)
            patterns = s.get('technique', {}).get('patterns', [])[:2]
            
            print(f"\n{idx}. {code} {name}")
            print(f"   推荐: {llm_rec} | 资金流入: {inflow}天 | 技术: {patterns}")
        
        return

    if args.backtest:
        if not args.stock:
            print("❌ 回测需要指定股票代码")
            print("   money-get 600519 --backtest")
            return
        print("=" * 50)
        print(f"📈 回测: {args.stock}")
        print(f"📅 周数: {args.weeks}")
        print("=" * 50)
        agent = StockAgent(backtest_date="2025-01-01", initial_capital=10000, verbose=verbose, trace=trace)
        result = agent.run_backtest([args.stock], weeks=args.weeks)
        print("\n" + "=" * 50)
        print("📊 回测结果")
        print("=" * 50)
        print(f"初始资金: {result['initial_capital']}元")
        print(f"当前资金: {result['current_capital']:.2f}元")
        print(f"总收益: {result['total_return']:.2f}%")
        ev = result.get("evaluation", {})
        if ev and "error" not in ev:
            print(f"交易次数: {ev.get('total_trades', 0)}")
            print(f"胜率: {ev.get('win_rate', 'N/A')}")
            print(f"盈利: {ev.get('wins', 0)}次")
            print(f"亏损: {ev.get('losses', 0)}次")
        return

    if args.stock:
        print("=" * 50)
        print(f"📊 分析: {args.stock}")
        print("=" * 50)
        
        # 使用多 Agent 协作系统
        from .agents import TradingAgents
        from .logger import logger as _logger
        
        _logger.info(f"开始多Agent分析: {args.stock}")
        
        agents = TradingAgents(mode='hybrid')
        result = agents.analyze(args.stock)
        
        # 打印最终决策
        decision = result.get('decision', '无决策')
        print("\n" + "="*50)
        print("📋 分析结果")
        print("="*50)
        print(decision)
        
        _logger.info(f"多Agent分析完成: {args.stock}")
        return

    print(
        """
📈 股票分析 CLI
================

命令:
  money-get 600519             # 分析股票
  money-get --hot              # 热点板块
  money-get --reco             # 推荐股票
  money-get --eval             # 策略回测对比
  money-get 600519 --backtest  # 回测
  money-get --help             # 帮助

输入股票代码开始分析:
"""
    )
    stock = input("> ").strip()
    if stock:
        agent = StockAgent(verbose=verbose, trace=trace)
        print("\n" + "=" * 50)
        print(agent.analyze(stock))
