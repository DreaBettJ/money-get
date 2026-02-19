"""自动选股系统 - 每日精选"""
from money_get.enhanced_factors import batch_analyze, quick_analyze
from money_get.core.scraper import get_hot_sectors
from money_get.core.db import get_connection
from datetime import datetime


# 候选股票池（可配置）
DEFAULT_POOL = [
    '600519', '000858',  # 白酒
    '300719', '300251',  # 科技/传媒
    '600036', '601318',  # 银行/保险
    '000001', '399001',  # 指数
    '688981', '688256',  # 科创
    '300750', '300014',  # 新能源
    '002594', '300124',  # 汽车/制造
]


def get_pool_from_hot() -> list:
    """从热点板块获取候选股票"""
    try:
        # 这里应该从热点板块获取成分股
        # 简化版本返回默认池
        return DEFAULT_POOL
    except:
        return DEFAULT_POOL


def daily_selection(pool: list = None) -> list:
    """每日选股
    
    Args:
        pool: 候选股票列表
        
    Returns:
        list: 排序后的分析结果
    """
    if pool is None:
        pool = get_pool_from_hot()
    
    print(f"\n{'='*60}")
    print(f"📊 每日选股分析 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}")
    print(f"候选股票: {len(pool)} 只\n")
    
    # 批量分析
    results = batch_analyze(pool)
    
    # 输出结果
    print(f"{'排名':<4} {'代码':<8} {'名称':<10} {'现价':<8} {'涨幅':<8} {'总分':<6} {'信号'}")
    print("-" * 70)
    
    for i, r in enumerate(results, 1):
        change = r.get('change', 0)
        change_str = f"{change:+.2f}%" if change else "N/A"
        
        print(f"{i:<4} {r['code']:<8} {r['name']:<10} {r['price']:<8.2f} {change_str:<8} {r['total_score']:<6.1f} {r['signal']}")
    
    print("-" * 70)
    
    # 推荐
    top3 = results[:3]
    print(f"\n🎯 推荐关注:")
    for r in top3:
        print(f"  - {r['code']} {r['name']}: {r['signal']} (分数: {r['total_score']})")
    
    return results


def auto_buy_candidates(min_score: float = 60) -> list:
    """获取符合买入条件的股票
    
    Args:
        min_score: 最低分数
        
    Returns:
        list: 符合条件的股票列表
    """
    pool = get_pool_from_hot()
    results = batch_analyze(pool)
    
    # 筛选买入信号
    candidates = [r for r in results if r['total_score'] >= min_score]
    
    return candidates


def save_daily_report(results: list):
    """保存每日报告"""
    conn = get_connection()
    cursor = conn.cursor()
    
    date = datetime.now().strftime('%Y-%m-%d')
    
    for r in results:
        cursor.execute("""
            INSERT OR REPLACE INTO daily_selection (code, name, price, score, signal, date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (r['code'], r['name'], r['price'], r['total_score'], r['signal'], date))
    
    conn.commit()
    conn.close()
    print(f"\n✅ 报告已保存")


if __name__ == "__main__":
    # 每日选股
    results = daily_selection()
