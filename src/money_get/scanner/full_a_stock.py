"""全A股扫描系统 - 5000只"""
from money_get.core.scraper import get_stock_price
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('money_get.full_a_stock')


def get_all_a_stocks() -> list:
    """获取全部A股股票代码
    
    Returns:
        list: 股票代码列表 (沪深A股)
    """
    # 沪市A股 (600000-603999)
    sh = [f'60{i:04d}' for i in range(0, 4000)]
    # 深市A股 (000001-003999)
    sz = [f'00{i:04d}' for i in range(0, 1000)]
    # 创业板 (300001-300999)
    cyb = [f'30{i:04d}' for i in range(0, 1000)]
    
    all_stocks = sh + sz + cyb
    return all_stocks


def scan_stock(code: str) -> dict:
    """扫描单只股票"""
    try:
        p = get_stock_price(code)
        if p and p.get('price'):
            return {
                'code': code,
                'name': p.get('name', ''),
                'price': p.get('price', 0),
                'change': (p.get('pct', 0) or 0) * 100,
                'volume': p.get('volume', 0),
                'amount': p.get('amount', 0),
            }
    except:
        pass
    return None


def full_a_stock_scan(
    stock_count: int = 5000,
    workers: int = 30,
    batch_size: int = 500,
    delay: float = 0.05
) -> list:
    """全A股扫描
    
    Args:
        stock_count: 扫描数量
        workers: 并发数
        batch_size: 每批数量
        delay: 请求间隔(秒)
        
    Returns:
        list: 扫描结果
    """
    all_stocks = get_all_a_stocks()[:stock_count]
    total = len(all_stocks)
    
    logger.info(f"🚀 开始全A股扫描: {total}只")
    logger.info(f"   并发: {workers}, 批次: {batch_size}, 延迟: {delay}s")
    
    results = []
    fail_count = 0
    batch_num = (total + batch_size - 1) // batch_size
    
    start_time = time.time()
    
    for batch_idx in range(batch_num):
        start_idx = batch_idx * batch_size
        end_idx = min(start_idx + batch_size, total)
        batch_stocks = all_stocks[start_idx:end_idx]
        
        logger.info(f"📦 批次 {batch_idx+1}/{batch_num}: {start_idx}-{end_idx}")
        
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(scan_stock, c): c for c in batch_stocks}
            
            for future in as_completed(futures):
                result = future.result()
                if result:
                    results.append(result)
                else:
                    fail_count += 1
                
                # 进度
                done = len(results) + fail_count
                if done % 100 == 0:
                    logger.info(f"   进度: {done}/{total} ({len(results)}成功, {fail_count}失败)")
        
        # 批次间隔
        if batch_idx < batch_num - 1:
            time.sleep(0.5)
    
    elapsed = time.time() - start_time
    
    # 排序
    results.sort(key=lambda x: x['change'], reverse=True)
    
    logger.info(f"✅ 扫描完成: {len(results)}只成功, {fail_count}只失败, 耗时 {elapsed:.1f}秒")
    logger.info(f"   平均速度: {len(results)/elapsed:.1f}只/秒")
    
    return results


def format_full_report(results: list, top_n: int = 30) -> str:
    """生成完整报告"""
    lines = []
    lines.append(f"\n{'='*70}")
    lines.append(f"📊 全A股扫描报告 (共{len(results)}只)")
    lines.append(f"{'='*70}")
    
    # 涨幅分布
    up = len([r for r in results if r['change'] > 0])
    down = len([r for r in results if r['change'] < 0])
    flat = len(results) - up - down
    
    lines.append(f"\n📈 涨跌分布:")
    lines.append(f"  上涨: {up}只 ({up/len(results)*100:.1f}%)")
    lines.append(f"  下跌: {down}只 ({down/len(results)*100:.1f}%)")
    lines.append(f"  平盘: {flat}只 ({flat/len(results)*100:.1f}%)")
    
    # Top 30
    lines.append(f"\n{'='*70}")
    lines.append(f"🔥 涨幅前{top_n}:")
    lines.append(f"{'排名':<4} {'代码':<8} {'名称':<12} {'价格':<10} {'涨幅'}")
    lines.append("-" * 55)
    
    for i, r in enumerate(results[:top_n], 1):
        lines.append(f"{i:<4} {r['code']:<8} {r['name']:<12} {r['price']:<10.2f} {r['change']:+.2f}%")
    
    # 跌幅前20
    lines.append(f"\n{'='*70}")
    lines.append(f"📉 跌幅前20:")
    lines.append("-" * 55)
    
    for i, r in enumerate(results[-20:], 1):
        lines.append(f"{i:<4} {r['code']:<8} {r['name']:<12} {r['price']:<10.2f} {r['change']:+.2f}%")
    
    return "\n".join(lines)


def run_full_scan(count: int = 5000):
    """运行全A股扫描"""
    logger.info("="*60)
    logger.info(f"开始全A股扫描: {count}只")
    logger.info("="*60)
    
    results = full_a_stock_scan(stock_count=count)
    
    # 输出报告
    report = format_full_report(results)
    print(report)
    
    # 记录结果
    top5 = [(r['code'], r['name'], f"{r['change']:+.2f}%") for r in results[:5]]
    down5 = [(r['code'], r['name'], f"{r['change']:+.2f}%") for r in results[-5:]]
    logger.info(f"涨幅前5: {top5}")
    logger.info(f"跌幅前5: {down5}")
    
    return results


if __name__ == "__main__":
    import sys
    
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    run_full_scan(count)
