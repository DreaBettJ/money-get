"""完整选股系统 - 扫描 + 多因子分析"""
from money_get.full_scan import full_scan, STOCK_POOL
from money_get.enhanced_factors import EnhancedFactor
from money_get.scraper import get_stock_price
from concurrent.futures import ThreadPoolExecutor, as_completed
import time


def scan_and_analyze(stock_count: int = 100, min_change: float = 0) -> list:
    """扫描并分析
    
    Args:
        stock_count: 扫描股票数量
        min_change: 最小涨幅过滤
        
    Returns:
        list: 分析结果列表
    """
    print(f"\n{'='*70}")
    print(f"🔍 全市场扫描 + 多因子分析")
    print(f"{'='*70}")
    
    # 1. 扫描市场
    print("\n📊 阶段1: 市场扫描...")
    start = time.time()
    results = full_scan(stock_count)
    print(f"扫描完成，耗时 {time.time()-start:.1f}秒")
    
    # 2. 过滤涨幅
    if min_change > 0:
        results = [r for r in results if r['change'] >= min_change]
        print(f"过滤涨幅>{min_change}%后: {len(results)}只")
    
    # 3. 多因子分析（只分析Top 50，避免太慢）
    print("\n📈 阶段2: 多因子分析 (Top 50)...")
    analyze_count = min(50, len(results))
    analyzed = []
    
    for i, r in enumerate(results[:analyze_count], 1):
        try:
            factor = EnhancedFactor(r['code'])
            factor.load_all_data()
            result = factor.calculate_all()
            analyzed.append(result)
            
            if i % 10 == 0:
                print(f"  进度: {i}/{analyze_count}")
        except Exception as e:
            print(f"  分析失败 {r['code']}: {e}")
    
    # 4. 排序
    analyzed.sort(key=lambda x: x['total_score'], reverse=True)
    
    return analyzed


def quick_scan_and_rank(top_n: int = 30) -> list:
    """快速扫描+排名（简化版，不获取K线）
    
    Args:
        top_n: 返回数量
        
    Returns:
        list: 排序后的结果
    """
    print(f"\n{'='*60}")
    print(f"⚡ 快速选股 (Top {top_n})")
    print(f"{'='*60}")
    
    # 扫描全部
    results = full_scan(500)
    
    # 按涨幅排序，取Top N
    top_stocks = results[:top_n]
    
    # 简单评分
    scored = []
    for r in top_stocks:
        change = r['change']
        
        # 基础分
        score = 50
        
        # 涨幅加分
        if change > 10:
            score += 30
        elif change > 5:
            score += 20
        elif change > 3:
            score += 15
        elif change > 0:
            score += 10
        
        # 成交额加分
        if r.get('amount', 0) > 10:
            score += 10
        elif r.get('amount', 0) > 5:
            score += 5
        
        r['score'] = score
        scored.append(r)
    
    # 按分数排序
    scored.sort(key=lambda x: x['score'], reverse=True)
    
    return scored


def format_recommend(results: list, title: str = "选股推荐"):
    """格式化推荐结果"""
    lines = []
    lines.append(f"\n{'='*60}")
    lines.append(f"🎯 {title}")
    lines.append(f"{'='*60}")
    lines.append(f"{'排名':<4} {'代码':<8} {'名称':<12} {'价格':<8} {'涨幅':<8} {'评分':<6}")
    lines.append("-" * 60)
    
    for i, r in enumerate(results, 1):
        change = r.get('change', 0)
        score = r.get('total_score') or r.get('score', 0)
        
        lines.append(f"{i:<4} {r['code']:<8} {r['name']:<12} {r['price']:<8.2f} {change:+.2f}% {score:<6.1f}")
    
    lines.append("-" * 60)
    
    # 推荐买入
    buy = [r for r in results if '买入' in r.get('signal', '') or r.get('score', 0) >= 70]
    if buy:
        lines.append(f"\n✅ 推荐买入 ({len(buy)}只):")
        for r in buy[:5]:
            signal = r.get('signal', f"评分:{r.get('score',0)}")
            lines.append(f"  {r['code']} {r['name']}: {signal}")
    
    return "\n".join(lines)


def run_full_analysis():
    """运行完整分析"""
    # 方法1: 完整多因子分析（较慢）
    results = scan_and_analyze(500, min_change=3)
    print(format_recommend(results, "多因子选股结果"))
    
    return results


def run_quick_selection():
    """快速选股"""
    results = quick_scan_and_rank(30)
    print(format_recommend(results, "快速选股结果"))
    return results


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'quick':
        run_quick_selection()
    else:
        run_full_analysis()
