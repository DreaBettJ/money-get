"""同步历史数据

用法:
    python sync_history.py              # 同步 2025 全年
    python sync_history.py --year 2024 # 同步 2024 年
"""
import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import os
os.chdir(PROJECT_ROOT)


def sync_kline_history(stock_code: str, year: int = 2025) -> dict:
    """同步单只股票的历史 K 线
    
    Args:
        stock_code: 股票代码
        year: 年份
    """
    import akshare as ak
    from datetime import datetime, timedelta
    from money_get.db import insert_kline, init_db
    
    print(f"📥 同步 {stock_code} {year} 年 K 线...")
    
    # 注意：akshare 需要无横杠的日期格式
    start_date = f"{year}0101"
    end_date = f"{year}1231"
    
    try:
        # 获取历史 K 线
        df = ak.stock_zh_a_hist(
            symbol=stock_code,
            start_date=start_date,
            end_date=end_date,
            adjust="qfq"  # 前复权
        )
        
        if df is None or df.empty:
            print(f"  ⚠️ 无数据")
            return {"success": 0, "failed": 1}
        
        print(f"  📊 获取 {len(df)} 条数据")
        
        # 插入数据库
        count = 0
        for _, row in df.iterrows():
            try:
                # 处理日期格式（可能是 datetime.date 或字符串）
                date = row['日期']
                if hasattr(date, 'strftime'):
                    date = date.strftime('%Y-%m-%d')
                else:
                    date = str(date)[:10]
                
                insert_kline(
                    code=stock_code,
                    date=date,
                    open=float(row['开盘']),
                    close=float(row['收盘']),
                    high=float(row['最高']),
                    low=float(row['最低']),
                    volume=int(row['成交量']),
                    amount=float(row.get('成交额', 0) or 0)
                )
                count += 1
            except Exception as e:
                print(f"  ❌ 插入错误: {e}")
                break
        
        print(f"  ✅ 成功 {count} 条")
        return {"success": count, "failed": 0}
        
    except Exception as e:
        print(f"  ❌ 错误: {e}")
        return {"success": 0, "failed": 1}


def sync_fund_flow_history(stock_code: str, year: int = 2025) -> dict:
    """同步历史资金流向"""
    import akshare as ak
    from money_get.db import insert_fund_flow
    
    print(f"📥 同步 {stock_code} {year} 年资金流向...")
    
    try:
        # 东方财富资金流向
        df = ak.stock_individual_fund_flow(stock=stock_code, market="sh")
        
        if df is None or df.empty:
            print(f"  ⚠️ 无数据")
            return {"success": 0, "failed": 1}
        
        count = 0
        for _, row in df.iterrows():
            try:
                date = str(row['日期'])[:10]
                if year not in date:
                    continue
                    
                insert_fund_flow(
                    code=stock_code,
                    date=date,
                    main_net_inflow=float(row.get('主力净流入', 0) or 0) * 10000,
                    super_net_inflow=float(row.get('超大单净流入', 0) or 0) * 10000,
                    large_net_inflow=float(row.get('大单净流入', 0) or 0) * 10000,
                    medium_net_inflow=float(row.get('中单净流入', 0) or 0) * 10000,
                    small_net_inflow=float(row.get('小单净流入', 0) or 0) * 10000,
                )
                count += 1
            except:
                pass
        
        print(f"  ✅ 成功 {count} 条")
        return {"success": count, "failed": 0}
        
    except Exception as e:
        print(f"  ❌ 错误: {e}")
        return {"success": 0, "failed": 1}


def main():
    parser = argparse.ArgumentParser(description="同步历史数据")
    parser.add_argument("--year", type=int, default=2025, help="年份")
    parser.add_argument("--stock", type=str, help="指定股票代码")
    args = parser.parse_args()
    
    year = args.year
    stocks = [args.stock] if args.stock else ["600519", "000858", "300750"]
    
    print(f"📅 同步 {year} 年数据")
    print(f"📋 股票: {stocks}")
    print("=" * 50)
    
    # 初始化数据库
    from money_get.db import init_db
    init_db()
    
    total = {"kline": 0, "fund": 0}
    
    for stock in stocks:
        # K线
        result = sync_kline_history(stock, year)
        total["kline"] += result["success"]
        
        # 资金流向
        result = sync_fund_flow_history(stock, year)
        total["fund"] += result["success"]
    
    print("=" * 50)
    print(f"✅ 完成: K线 {total['kline']} 条, 资金 {total['fund']} 条")


if __name__ == "__main__":
    main()
