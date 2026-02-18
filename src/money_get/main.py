"""股票分析 CLI 入口。"""
import argparse

from money_get.agent import StockAgent
from money_get.backtest.strategy import Strategy, quick_backtest


def cli() -> None:
    parser = argparse.ArgumentParser(description="股票分析 CLI")
    parser.add_argument("stock", nargs="?", help="股票代码")
    parser.add_argument("--hot", action="store_true", help="查看热点板块")
    parser.add_argument("--backtest", "-b", action="store_true", help="回测模式")
    parser.add_argument("--reco", "-r", action="store_true", help="推荐股票")
    parser.add_argument("--eval", "-e", action="store_true", help="策略回测评估")
    parser.add_argument("--weeks", "-w", type=int, default=52, help="回测周数")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    parser.add_argument("--no-trace", action="store_true", help="不追踪")
    args = parser.parse_args()

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
        agent = StockAgent(backtest_date="2025-01-01", verbose=verbose, trace=trace) if args.backtest else StockAgent(
            verbose=verbose, trace=trace
        )
        print(agent.analyze(args.stock))
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
