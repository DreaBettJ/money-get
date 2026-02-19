#!/usr/bin/env python3
"""
每日股票分析工作流
==================
场景：
1. 每日推荐股票
2. 独立分析每只股票
3. 决策调仓
4. 收益率计算
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from money_get.selector import select_stocks
from money_get.agent import StockAgent
from money_get.llm import get_default_llm
from money_get.main import load_trades, cmd_portfolio
import json


def daily_recommend():
    """场景1: 每日推荐股票"""
    print("\n" + "="*60)
    print("📅 每日股票推荐")
    print("="*60)
    
    stocks = select_stocks(use_policy=True, use_llm=True, top_n=5)
    
    if not stocks:
        print("⚠️ 今日无推荐股票")
        return []
    
    print(f"\n推荐 {len(stocks)} 只股票:\n")
    for i, s in enumerate(stocks, 1):
        code = s.get("code", "")
        name = s.get("name", "")
        rec = s.get("llm_recommendation", "观望")
        inflow = s.get("inflow", {}).get("consecutive_days", 0)
        patterns = s.get("technique", {}).get("patterns", [])[:2]
        print(f"{i}. {code} {name}")
        print(f"   推荐: {rec} | 资金流入: {inflow}天 | 技术: {patterns}")
    
    return stocks


def analyze_stock(code):
    """场景2: 独立分析股票"""
    print("\n" + "="*60)
    print(f"🔍 分析: {code}")
    print("="*60)
    
    agent = StockAgent(verbose=False, trace=False)
    result = agent.analyze(code)
    print(result)
    return result


def decision_and_adjust(stocks):
    """场景3: 决策调仓"""
    print("\n" + "="*60)
    print("⚖️ 决策调仓")
    print("="*60)
    
    # 加载当前持仓
    trades = load_trades()
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
    
    print("\n当前持仓:", holdings)
    
    # 分析推荐股票
    recommendations = []
    for s in stocks[:3]:
        code = s.get("code", "")
        rec = s.get("llm_recommendation", "观望")
        print(f"\n分析 {code}: {rec}")
        
        # 简单决策逻辑
        if "买入" in rec or "增持" in rec:
            recommendations.append({"code": code, "action": "买入", "reason": rec})
        elif "卖出" in rec or "减持" in rec:
            recommendations.append({"code": code, "action": "卖出", "reason": rec})
    
    print("\n📋 调仓建议:")
    for r in recommendations:
        print(f"  {r['action']}: {r['code']} - {r['reason']}")
    
    return recommendations


def calculate_returns():
    """场景4: 计算收益率"""
    print("\n" + "="*60)
    print("💰 收益率计算")
    print("="*60)
    
    trades = load_trades()
    if not trades:
        print("⚠️ 无交易记录")
        return
    
    # 获取当前股价（需要实时数据，这里用最后交易价格模拟）
    holdings = {}
    history = []
    
    for t in trades:
        code = t.get("code") or t.get("stock_code", "")
        if not code:
            continue
        action = t.get("action") or t.get("direction", "")
        qty = t.get("quantity", 0)
        price = t.get("price", 0)
        date = t.get("date", "")
        
        history.append({"date": date, "code": code, "action": action, "price": price, "qty": qty})
        
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
        print("📭 当前空仓")
        return
    
    # 计算收益（简化版：假设当前价=成本价，需要接入实时行情）
    total_cost = 0
    print("\n📊 持仓明细:")
    for code, h in holdings.items():
        qty = h["qty"]
        cost = h["cost"]
        avg_cost = cost / qty if qty > 0 else 0
        print(f"  {code}: {qty}股 | 成本: {avg_cost:.2f}元")
        total_cost += cost
    
    print(f"\n总成本: {total_cost:.2f}元")
    print("⚠️ 当前收益需要接入实时行情才能计算")


def run_daily_workflow():
    """运行每日工作流"""
    print("\n" + "="*60)
    print("🚀 每日股票分析工作流")
    print("="*60)
    
    # 1. 每日推荐
    stocks = daily_recommend()
    
    # 2. 独立分析每只推荐股票
    if stocks:
        print("\n" + "="*60)
        print("📈 深度分析每只股票")
        print("="*60)
        for s in stocks[:3]:
            code = s.get("code", "")
            analyze_stock(code)
    
    # 3. 决策调仓
    if stocks:
        decision_and_adjust(stocks)
    
    # 4. 收益率计算
    calculate_returns()
    
    print("\n" + "="*60)
    print("✅ 工作流完成")
    print("="*60)


if __name__ == "__main__":
    run_daily_workflow()
