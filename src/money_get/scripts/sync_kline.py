"""K线数据爬取脚本"""
import requests
import json
from money_get.db import get_connection


def fetch_kline(code: str, days: int = 320) -> list:
    """获取K线数据（从腾讯财经API）
    
    Args:
        code: 股票代码，如 300719
        days: 获取天数，默认320天
    
    Returns:
        list: K线数据列表
    """
    # 转换为腾讯财经格式
    if code.startswith('6'):
        qq_code = 'sh' + code
    else:
        qq_code = 'sz' + code
    
    url = f'https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={qq_code},day,,,{days},qfq'
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    r = requests.get(url, headers=headers, timeout=10)
    data = r.json()
    
    if 'data' not in data:
        return []
    
    stock_data = data['data'].get(qq_code, {})
    qfq_data = stock_data.get('qfqday', [])
    
    return qfq_data


def save_kline(code: str, klines: list) -> int:
    """保存K线数据到数据库
    
    Args:
        code: 股票代码
        klines: K线数据列表
    
    Returns:
        int: 保存的记录数
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    count = 0
    for k in klines:
        if len(k) < 6:
            continue
            
        date = k[0]
        open_price = k[1]
        close = k[2]
        high = k[3]
        low = k[4]
        volume = k[5]
        
        # 转换日期格式
        if '-' not in date:
            # 格式可能是 YYYYMMDD
            date = f"{date[:4]}-{date[4:6]}-{date[6:]}"
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO daily_kline 
                (code, date, open, close, high, low, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (code, date, float(open_price), float(close), float(high), float(low), float(volume)))
            count += 1
        except Exception as e:
            print(f"插入失败: {date}, {e}")
    
    conn.commit()
    conn.close()
    return count


def sync_kline(code: str) -> int:
    """同步K线数据
    
    Args:
        code: 股票代码
    
    Returns:
        int: 保存的记录数
    """
    print(f"获取 {code} K线数据...")
    klines = fetch_kline(code)
    print(f"获取到 {len(klines)} 条数据")
    
    if klines:
        count = save_kline(code, klines)
        print(f"保存 {count} 条数据")
        return count
    
    return 0


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        code = sys.argv[1]
    else:
        code = "300719"
    
    sync_kline(code)
