"""快速全市场扫描"""
from money_get.core.scraper import get_stock_price
from concurrent.futures import ThreadPoolExecutor, as_completed
import time


# 股票池
STOCKS = [
    # 沪深300
    '600519', '000858', '600036', '601318', '600900', '600276', '601166', '601398',
    '600028', '601988', '601857', '600050', '601288', '600016', '601088', '600030',
    '601012', '600585', '600690', '600309', '600887', '600018', '600009', '601328',
    '600000', '601229', '601319', '601688', '600837', '600104', '600606', '601668',
    '600745', '600031', '600348', '600547', '601866', '601618', '601390', '601336',
    '601899', '600518', '600867', '601877', '600507', '600170', '600487', '600588',
    '600850', '600703', '600809', '600660', '601601', '600612', '600760', '600645',
    '600522', '600176', '600496', '600183', '600261', '600409', '600059', '600733',
    '600316', '600811', '600795', '600100', '600570', '600816', '600745', '600031',
    # 热门概念
    '300750', '300014', '002594', '002466', '002475', '002371', '300012', '300033',
    '300059', '300122', '300124', '300146', '300166', '300182', '300212', '300223',
    '300251', '300274', '300308', '300347', '300408', '300433', '300459', '300496',
    '300527', '300581', '300598', '300618', '300663', '300672', '300696', '300719',
    '300751', '300763', '300770', '300782', '300896', '300001', '300002', '300003',
    '300004', '300006', '300007', '300008', '300009', '300010', '300015', '300016',
    '300017', '300018', '300019', '300020',
]


def scan_one(code: str) -> dict:
    """扫描单只"""
    try:
        p = get_stock_price(code)
        if p:
            return {
                'code': code,
                'name': p.get('name', ''),
                'price': p.get('price', 0),
                'change': (p.get('pct', 0) or 0) * 100,
            }
    except:
        pass
    return None


def fast_scan(max_stocks: int = 50) -> list:
    """快速扫描
    
    Args:
        max_stocks: 最大扫描数量
    """
    stocks = list(set(STOCKS))[:max_stocks]
    results = []
    
    print(f"🔍 扫描 {len(stocks)} 只股票...")
    start = time.time()
    
    # 并发扫描
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(scan_one, c): c for c in stocks}
        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            if result:
                results.append(result)
            if i % 10 == 0:
                print(f"  进度: {i}/{len(stocks)}")
    
    elapsed = time.time() - start
    print(f"完成，耗时 {elapsed:.1f}秒")
    
    # 排序
    results.sort(key=lambda x: x['change'], reverse=True)
    return results


def show_results(results: list, top_n: int = 20):
    """显示结果"""
    print(f"\n{'排名':<4} {'代码':<8} {'名称':<12} {'价格':<10} {'涨幅'}")
    print("-" * 55)
    
    for i, r in enumerate(results[:top_n], 1):
        print(f"{i:<4} {r['code']:<8} {r['name']:<12} {r['price']:<10.2f} {r['change']:+.2f}%")
    
    # Top 5
    print(f"\n🔥 涨幅前5:")
    for r in results[:5]:
        print(f"  {r['code']} {r['name']}: {r['change']:+.2f}%")
    
    # Down 5
    print(f"\n📉 跌幅前5:")
    for r in results[-5:]:
        print(f"  {r['code']} {r['name']}: {r['change']:+.2f}%")


if __name__ == "__main__":
    results = fast_scan(50)
    show_results(results)
