"""数据爬取脚本 - 完整版"""
import logging
import requests
import json
import time
from money_get.db import get_connection

logger = logging.getLogger(__name__)


# ============ 北向资金 ============
def get_north_money() -> list:
    """获取北向资金持股数据
    
    Returns:
        list: 北向资金持股列表
    """
    results = []
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        # 沪股通持股
        url1 = 'https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=50&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:1+t:23&fields=f2,f3,f4,f12,f14,f62,f140'
        r1 = requests.get(url1, headers=headers, timeout=10)
        data1 = r1.json()
        
        if data1.get('data') and data1['data'].get('diff'):
            for item in data1['data']['diff']:
                results.append({
                    'code': str(item.get('f12')),
                    'name': item.get('f14', ''),
                    'price': item.get('f2'),
                    'change': item.get('f3'),
                    'north_money': item.get('f62'),
                    'type': '沪股通'
                })
        
        # 深股通持股
        url2 = 'https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=50&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:0+t:6&fields=f2,f3,f4,f12,f14,f62,f140'
        r2 = requests.get(url2, headers=headers, timeout=10)
        data2 = r2.json()
        
        if data2.get('data') and data2['data'].get('diff'):
            for item in data2['data']['diff']:
                results.append({
                    'code': str(item.get('f12')),
                    'name': item.get('f14', ''),
                    'price': item.get('f2'),
                    'change': item.get('f3'),
                    'north_money': item.get('f62'),
                    'type': '深股通'
                })
        
    except Exception as e:
        logger.info(f"获取北向资金失败: {e}")
    
    return results


def save_north_money(data_list: list):
    """保存北向资金数据"""
    if not data_list:
        return
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # 创建表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS north_stock (
            code TEXT PRIMARY KEY,
            name TEXT,
            price REAL,
            change_pct REAL,
            north_money REAL,
            type TEXT,
            updated_at TEXT
        )
    """)
    
    for data in data_list:
        cursor.execute("""
            INSERT OR REPLACE INTO north_stock 
            (code, name, price, change_pct, north_money, type, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
        """, (
            data.get('code'),
            data.get('name'),
            data.get('price'),
            data.get('change'),
            data.get('north_money'),
            data.get('type')
        ))
    
    conn.commit()
    conn.close()
    logger.info(f"北向资金持股: {len(data_list)}条")


# ============ 股票行情 ============
def get_stock_quote(code: str) -> dict:
    """获取股票行情"""
    try:
        if code.startswith('6'):
            secid = f'1.{code}'
        else:
            secid = f'0.{code}'
        
        url = f'https://push2.eastmoney.com/api/qt/stock/get?secid={secid}&fields=f2,f3,f4,f5,f14,f15,f16,f17,f18,f20,f38,f162,f167'
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        r = requests.get(url, headers=headers, timeout=5)
        data = r.json()
        
        if data.get('data'):
            d = data['data']
            return {
                'code': code,
                'name': d.get('f14', ''),
                'price': d.get('f2'),
                'change': d.get('f3'),
                'volume': d.get('f5'),
                'high': d.get('f15'),
                'low': d.get('f16'),
                'open': d.get('f17'),
                'close': d.get('f18'),
                'pe': d.get('f162'),
                'pb': d.get('f167'),
                'market': d.get('f20'),
                'turnover': d.get('f38'),
            }
    except:
        pass
    return None


def save_stock_quote(data: dict):
    """保存行情到数据库"""
    if not data:
        return
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # 创建表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_quote (
            code TEXT PRIMARY KEY,
            name TEXT,
            price REAL,
            change_pct REAL,
            volume REAL,
            high REAL,
            low REAL,
            open REAL,
            close REAL,
            pe REAL,
            pb REAL,
            market REAL,
            turnover REAL,
            updated_at TEXT
        )
    """)
    
    cursor.execute("""
        INSERT OR REPLACE INTO stock_quote 
        (code, name, price, change_pct, volume, high, low, open, close, pe, pb, market, turnover, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
    """, (
        data.get('code'),
        data.get('name'),
        data.get('price'),
        data.get('change'),
        data.get('volume'),
        data.get('high'),
        data.get('low'),
        data.get('open'),
        data.get('close'),
        data.get('pe'),
        data.get('pb'),
        data.get('market'),
        data.get('turnover')
    ))
    
    conn.commit()
    conn.close()


# ============ 主程序 ============
def crawl_market():
    """爬取市场数据"""
    logger.info("="*50)
    logger.info("开始爬取市场数据")
    logger.info("="*50)
    
    # 1. 北向资金
    logger.info("\n[1/2] 北向资金持股...")
    north_data = get_north_money()
    save_north_money(north_data)
    
    # 2. 热门股票
    logger.info("\n[2/2] 热门股票...")
    hot_codes = [
        '600519', '000858', '600036', '601318', '600900', '600276', '601166', '601398',
        '600028', '601988', '601857', '600050', '601288', '600016', '601088', '600030',
        '601012', '600585', '600690', '600309', '600887', '600018', '600009', '601328',
        '600000', '601229', '601319', '601688', '600837', '600104', '600606', '601668',
        '600745', '600031', '600348', '600547', '601866', '601618', '601390', '601336',
        '601899', '600518', '600867', '601877', '600507', '600170', '600487', '600588',
        '600850', '600703', '600809', '600660', '601601', '600612', '600760', '600645',
    ]
    
    success = 0
    for i, code in enumerate(hot_codes, 1):
        data = get_stock_quote(code)
        if data:
            save_stock_quote(data)
            success += 1
        
        if i % 20 == 0:
            logger.info(f"  进度: {i}/{len(hot_codes)}")
        time.sleep(0.03)
    
    logger.info(f"行情数据: {success}条")
    logger.info("\n爬取完成!")


if __name__ == "__main__":
    crawl_market()
