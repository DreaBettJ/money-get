"""数据爬取 - 东方财富（免费、稳定）

注意：东方财富有频率限制，需要控制请求频率
"""
from typing import List, Dict, Optional
import json
import re
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Playwright 是可选依赖
try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

# 请求间隔（秒），避免被限流
REQUEST_DELAY = 0.5
_last_request_time = 0


def _get_session():
    """获取带重试的 session"""
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.5)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('https://', adapter)
    return session


def get_stock_price(code: str) -> Optional[Dict]:
    """获取股票实时价格"""
    code = code.strip()
    
    # 判断交易所
    if code.startswith('6'):
        url = f"https://push2.eastmoney.com/api/qt/stock/get?invt=2&fltt=2&fields=f43,f44,f45,f46,f47,f48,f50,f51,f52,f57,f58,f59,f60,f116,f117,f162,f167,f168,f169,f170,f171,f173,f177&secid=1.{code}"
    elif code.startswith('0') or code.startswith('3'):
        url = f"https://push2.eastmoney.com/api/qt/stock/get?invt=2&fltt=2&fields=f43,f44,f45,f46,f47,f48,f50,f51,f52,f57,f58,f59,f60,f116,f117,f162,f167,f168,f169,f170,f171,f173,f177&secid=0.{code}"
    else:
        return None
    
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < REQUEST_DELAY:
        time.sleep(REQUEST_DELAY - elapsed)
    _last_request_time = time.time()
    
    try:
        session = _get_session()
        resp = session.get(url, timeout=10)
        data = resp.json()
        
        if data.get('data'):
            d = data['data']
            return {
                'code': code,
                'name': d.get('f58', ''),
                'price': d.get('f43', 0),
                'change': d.get('f44', 0) / 100,
                'pct': d.get('f45', 0) / 1000,
                'volume': d.get('f47', 0),
                'amount': d.get('f46', 0),
                'open': d.get('f50', 0) / 100,
                'high': d.get('f51', 0) / 100,
                'low': d.get('f52', 0) / 100,
                'close': d.get('f60', 0),
            }
    except Exception as e:
        _logger.warning(f"获取价格失败: {e}")
    
    return None


def get_fund_flow(code: str, days: int = 10) -> List[Dict]:
    """获取资金流向"""
    code = code.strip()
    
    if code.startswith('6'):
        secid = f"1.{code}"
    else:
        secid = f"0.{code}"
    
    url = f"https://push2.eastmoney.com/api/qt/stock/get?invt=2&fltt=2&fields=f62,f184,f66,f69,f72,f75,f78,f81,f84,f87,f124,f125,f126&secid={secid}"
    
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < REQUEST_DELAY:
        time.sleep(REQUEST_DELAY - elapsed)
    _last_request_time = time.time()
    
    try:
        session = _get_session()
        resp = session.get(url, timeout=10)
        data = resp.json()
        
        if data.get('data'):
            d = data['data']
            return [{
                'code': code,
                'main_net_inflow': d.get('f62', 0),
                'small_net_inflow': d.get('f66', 0),
                'retail_net_inflow': d.get('f72', 0),
                'net_inflow': d.get('f184', 0),
            }]
    
    except Exception as e:
        _logger.warning(f"获取资金流向失败: {e}")
    
    return []


def get_hot_sectors(limit: int = 10) -> List[Dict]:
    """获取热点板块"""
    url = "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=50&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m:90+t:2&fields=f1,f2,f3,f4,f12,f13,f14,f128,f140,f141"
    
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < REQUEST_DELAY:
        time.sleep(REQUEST_DELAY - elapsed)
    _last_request_time = time.time()
    
    try:
        session = _get_session()
        resp = session.get(url, timeout=10)
        data = resp.json()
        
        results = []
        if data.get('data') and data['data'].get('diff'):
            for i, item in enumerate(data['data']['diff'][:limit]):
                results.append({
                    'rank': i + 1,
                    'code': item.get('f12'),
                    'name': item.get('f14'),
                    'change': item.get('f2', 0),
                    'amount': item.get('f4', 0),
                })
        
        return results
    
    except Exception as e:
        _logger.warning(f"获取热点板块失败: {e}")
        return []


def get_realtime_news(limit: int = 10) -> List[Dict]:
    """获取实时财经新闻
    
    Returns:
        list: 新闻列表
    """
    if not HAS_PLAYWRIGHT:
        return _get_news_simple()
    
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < REQUEST_DELAY * 2:
        time.sleep(REQUEST_DELAY * 2 - elapsed)
    _last_request_time = time.time()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            page.goto('https://finance.sina.com.cn/stock/', wait_until='networkidle', timeout=25000)
            
            # 获取页面内容，用正则提取标题
            content = page.content()
            
            # 提取新闻标题
            patterns = [
                r'<h2[^>]*>.*?<a[^>]*>([^<]{10,60})</a>.*?</h2>',
                r'<h3[^>]*>.*?<a[^>]*>([^<]{10,60})</a>.*?</h3>',
                r'class=["\']news-item["\'][^>]*>.*?href=["\']([^"\']+)["\'].*?>([^<]{10,60})</a>',
            ]
            
            results = []
            for pattern in patterns:
                matches = re.findall(pattern, content, re.DOTALL)
                for match in matches:
                    if isinstance(match, tuple):
                        title = match[-1].strip()
                    else:
                        title = match.strip()
                    
                    if title and 10 < len(title) < 70:
                        results.append({
                            'title': title,
                            'source': '新浪财经',
                            'url': ''
                        })
            
            # 去重
            seen = set()
            unique = []
            for r in results:
                if r['title'] not in seen:
                    seen.add(r['title'])
                    unique.append(r)
            
            return unique[:limit]
            
        except Exception as e:
            _logger.warning(f"获取新闻失败: {e}")
            return _get_news_simple()
        finally:
            browser.close()


def _get_news_simple() -> List[Dict]:
    """简单的新闻获取（使用东方财富API）"""
    try:
        import json
        url = 'https://newsapi.eastmoney.com/kuaixun/v1/getlist_102_ajaxResult_50_1_.html'
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        session = _get_session()
        resp = session.get(url, headers=headers, timeout=10)
        
        # 解析 JSONP 响应
        text = resp.text
        if text.startswith('var ajaxResult='):
            text = text[len('var ajaxResult='):]
        
        data = json.loads(text)
        lives = data.get('LivesList', [])
        
        results = []
        for item in lives[:10]:
            results.append({
                'title': item.get('title', ''),
                'source': '东方财富',
                'url': item.get('url_w', ''),
                'time': item.get('datetime', '')
            })
        
        return results
    except Exception as e:
        _logger.warning(f"简单新闻获取失败: {e}")
        return []


def fetch_with_playwright(url: str) -> Optional[str]:
    """用 Playwright 获取页面"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
            content = page.content()
            return content
        except Exception as e:
            _logger.warning(f"Playwright 访问失败: {e}")
            return None
        finally:
            browser.close()


def get_stock_detail_playwright(code: str) -> Optional[Dict]:
    """用 Playwright 获取股票详情"""
    if code.startswith('6'):
        url = f"https://quote.eastmoney.com/sh{code}.html"
    else:
        url = f"https://quote.eastmoney.com/sz{code}.html"
    
    content = fetch_with_playwright(url)
    
    if not content:
        return None
    
    name_match = re.search(r'"name":"([^"]+)"', content)
    name = name_match.group(1) if name_match else code
    
    price_match = re.search(r'"price":([\d.]+)', content)
    price = float(price_match.group(1)) if price_match else 0
    
    return {
        'code': code,
        'name': name,
        'price': price,
    }


if __name__ == "__main__":
    print("=== 测试数据爬取 ===")
    
    print("\n1. 股票价格:")
    price = get_stock_price("600519")
    _logger.warning(f"   {price}")
    
    print("\n2. 资金流向:")
    flow = get_fund_flow("600519", days=5)
    for f in flow[:3]:
        _logger.warning(f"   {f}")
    
    print("\n3. 热点板块:")
    sectors = get_hot_sectors(5)
    for s in sectors:
        _logger.warning(f"   {s}")
    
    print("\n=== 完成 ===")
