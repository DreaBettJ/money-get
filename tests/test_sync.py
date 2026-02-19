"""同步和数据测试脚本

用法:
    python test_sync.py              # 运行同步并测试
    python test_sync.py --sync      # 仅同步
    python test_sync.py --analyze   # 仅分析
"""
import argparse
import sys
import os
from pathlib import Path

# 项目根目录 - 动态计算
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# 切换到项目目录
os.chdir(PROJECT_ROOT)


def test_sync():
    """测试数据同步"""
    print("=" * 50)
    print("📊 数据同步测试")
    print("=" * 50)
    
    from money_get.scripts.sync_daily import sync_all
    from money_get.db import init_db
    
    # 初始化数据库
    print("\n1️⃣ 初始化数据库...")
    init_db()
    print("   ✅ 完成")
    
    # 同步数据
    print("\n2️⃣ 同步数据...")
    result = sync_all(days=30)
    print(f"   ✅ 同步完成: 成功 {result['success']}/{result['total']}")
    
    # 检查数据
    print("\n3️⃣ 检查数据...")
    import sqlite3
    db_path = PROJECT_ROOT / "data" / "db" / "money_get.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    tables = [
        ("daily_kline", "K线"),
        ("indicators", "技术指标"),
        ("fund_flow", "资金流向"),
        ("lhb_data", "龙虎榜"),
        ("stock_news", "新闻"),
        ("hot_sectors", "热点板块"),
    ]
    
    for table, name in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"   {name}: {count} 条")
    
    conn.close()
    print("\n✅ 数据同步测试完成!")


def test_analyze():
    """测试分析功能"""
    print("=" * 50)
    print("🤖 LLM 分析测试")
    print("=" * 50)
    
    from money_get.services.llm_analyzer import analyze_stock
    
    # 分析个股
    print("\n1️⃣ 分析贵州茅台 (600519)...")
    result = analyze_stock("600519")
    
    print("\n" + "=" * 50)
    print(result)
    print("=" * 50)


def test_query():
    """测试数据查询"""
    print("=" * 50)
    print("🔍 数据查询测试")
    print("=" * 50)
    
    from money_get.db import (
        get_kline, get_indicators, get_fund_flow_data,
        get_news, get_lhb_data, get_hot_sectors
    )
    
    # K线
    print("\n1️⃣ K线数据 (茅台):")
    klines = get_kline("600519", limit=3)
    for k in klines:
        print(f"   {k['date']}: 收盘 {k['close']}")
    
    # 指标
    print("\n2️⃣ 技术指标:")
    ind = get_indicators("600519")
    if ind:
        print(f"   MA5: {ind.get('ma5', 0):.2f}")
        print(f"   MA20: {ind.get('ma20', 0):.2f}")
        print(f"   MACD: {ind.get('macd', 0):.2f}")
    
    # 资金流向
    print("\n3️⃣ 资金流向:")
    ff = get_fund_flow_data("600519", limit=1)
    if ff:
        print(f"   主力净流入: {ff[0].get('main_net_inflow', 0)}")
    
    # 新闻
    print("\n4️⃣ 最新新闻:")
    news = get_news("600519", limit=3)
    for n in news:
        print(f"   - {n.get('title', '')[:30]}...")
    
    # 龙虎榜
    print("\n5️⃣ 龙虎榜:")
    lhb = get_lhb_data(limit=5)
    for l in lhb:
        print(f"   - {l.get('name')}: 净买入 {l.get('net_amount')}")
    
    # 热点板块
    print("\n6️⃣ 热点板块:")
    sectors = get_hot_sectors(limit=5)
    for s in sectors:
        print(f"   - {s.get('sector_name')}: {s.get('change_percent')}%")
    
    print("\n✅ 查询测试完成!")


def main():
    parser = argparse.ArgumentParser(description="测试同步和分析功能")
    parser.add_argument("--sync", action="store_true", help="仅同步数据")
    parser.add_argument("--analyze", action="store_true", help="仅分析")
    parser.add_argument("--query", action="store_true", help="仅查询数据")
    
    args = parser.parse_args()
    
    if args.sync:
        test_sync()
    elif args.analyze:
        test_analyze()
    elif args.query:
        test_query()
    else:
        # 全部测试
        test_sync()
        test_query()
        test_analyze()


if __name__ == "__main__":
    main()
