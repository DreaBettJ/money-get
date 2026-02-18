"""政策关键词提取系统

从政府官网/权威媒体获取政策文件，提取关键词
"""
import re
import time
from typing import List, Dict, Optional
from datetime import datetime

# Playwright 是可选依赖
try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

# 请求间隔（秒）
REQUEST_DELAY = 2.0
_last_request_time = 0


def _delay():
    """控制请求频率"""
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < REQUEST_DELAY:
        time.sleep(REQUEST_DELAY - elapsed)
    _last_request_time = time.time()


def fetch_with_playwright(url: str, timeout: int = 30000) -> Optional[str]:
    """用 Playwright 获取页面"""
    if not HAS_PLAYWRIGHT:
        return None
    
    _delay()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            page.goto(url, wait_until="networkidle", timeout=timeout)
            content = page.content()
            return content
        except Exception as e:
            print(f"获取页面失败: {url}, {e}")
            return None
        finally:
            browser.close()


def get_gov_policy_keywords() -> List[Dict]:
    """获取政府政策关键词
    
    从中国政府网、新华网等获取政策文件
    """
    if not HAS_PLAYWRIGHT:
        return _get_policy_fallback()
    
    keywords = []
    
    # 1. 中国政府网 - 政策文件
    print("获取中国政府网政策...")
    content = fetch_with_playwright("https://www.gov.cn/zhengce/zuixin.htm")
    if content:
        gov_keywords = _extract_from_html(content, "中国政府网")
        keywords.extend(gov_keywords)
    
    # 2. 央广网 - 政策解读
    print("获取央广网政策...")
    content = fetch_with_playwright("https://news.cnr.cn/")
    if content:
        cnr_keywords = _extract_from_html(content, "央广网")
        keywords.extend(cnr_keywords)
    
    # 去重
    unique = _dedup_keywords(keywords)
    
    return unique[:30]


def _extract_from_html(html: str, source: str) -> List[Dict]:
    """从HTML中提取政策关键词"""
    keywords = []
    
    # 提取标题
    titles = re.findall(r'<a[^>]*>([^<]{6,50})</a>', html)
    
    for title in titles[:20]:
        title = title.strip()
        title = re.sub(r'&[a-z]+;', '', title)  # 去除HTML实体
        title = title.strip()
        
        # 过滤噪音
        if len(title) < 6:
            continue
        if any(x in title for x in ['登录', '注册', '更多', '>>', '图片', '视频', '滚动']):
            continue
        
        # 提取领域关键词
        sectors = _extract_sectors(title)
        
        keywords.append({
            'title': title,
            'source': source,
            'sectors': sectors,
        })
    
    return keywords


def _extract_sectors(text: str) -> List[str]:
    """从文本中提取行业/领域"""
    text = text.lower()
    
    # 定义关键词映射
    sector_map = {
        '新能源': ['新能源', '光伏', '风电', '储能', '锂电池', '电动车', '电动汽车', '汽车', '电池'],
        '人工智能': ['人工智能', 'AI', '大模型', '算力', '芯片', '智能', '数字经济', '科技'],
        '半导体': ['半导体', '集成电路', '光刻机', '芯片'],
        '医药医疗': ['医药', '医疗', '生物', '中药', '疫苗', '医疗器械', '健康', '卫生'],
        '高端制造': ['高端制造', '工业', '机器人', '数控', '自动化', '制造', '装备'],
        '数字经济': ['数字', '数据', '云计算', '大数据', '互联网', '网络'],
        '绿色低碳': ['绿色', '低碳', '碳中和', '碳达峰', '环保', '节能', '生态'],
        '基建地产': ['基建', '建筑', '房地产', '城市', '管网', '水泥', '工程'],
        '消费': ['消费', '家电', '纺织', '食品', '餐饮', '旅游', '零售'],
        '金融': ['金融', '银行', '保险', '证券', '投资', '资本'],
        '农业': ['农业', '农村', '乡村振兴', '粮食', '农产品', '农机'],
        '国防': ['国防', '军工', '航天', '航空', '船舶', '军事'],
    }
    
    found = []
    for sector, keywords in sector_map.items():
        if any(k in text for k in keywords):
            if sector not in found:
                found.append(sector)
    
    return found


def _dedup_keywords(keywords: List[Dict]) -> List[Dict]:
    """去重"""
    seen = set()
    unique = []
    
    for kw in keywords:
        # 用标题去重
        key = kw['title'][:15]
        if key not in seen:
            seen.add(key)
            unique.append(kw)
    
    return unique


def _get_policy_fallback() -> List[Dict]:
    """备用方案：无Playwright时使用预设关键词"""
    return [
        {'title': '新能源汽车产业发展规划', 'source': '预设', 'sectors': ['新能源']},
        {'title': '人工智能创新发展行动计划', 'source': '预设', 'sectors': ['人工智能']},
        {'title': '半导体产业扶持政策', 'source': '预设', 'sectors': ['半导体']},
        {'title': '医药创新支持政策', 'source': '预设', 'sectors': ['医药医疗']},
        {'title': '高端装备制造业发展意见', 'source': '预设', 'sectors': ['高端制造']},
    ]


def get_focus_sectors() -> List[str]:
    """获取当前政策关注领域
    
    Returns:
        list: 热门行业列表
    """
    policies = get_gov_policy_keywords()
    
    # 统计行业出现频次
    sector_count = {}
    for p in policies:
        for sector in p.get('sectors', []):
            sector_count[sector] = sector_count.get(sector, 0) + 1
    
    # 按频次排序
    sorted_sectors = sorted(sector_count.items(), key=lambda x: x[1], reverse=True)
    
    return [s[0] for s in sorted_sectors[:10]]


# 测试
if __name__ == "__main__":
    print("=== 政策关键词提取 ===\n")
    
    policies = get_gov_policy_keywords()
    
    print(f"获取到 {len(policies)} 条政策\n")
    
    # 打印所有政策
    print("=== 政策列表 ===\n")
    for i, p in enumerate(policies[:15], 1):
        sectors = p.get('sectors', [])
        sector_str = f" [{', '.join(sectors)}]" if sectors else ""
        print(f"{i}. {p['title'][:40]}{sector_str}")
    
    # 提取领域
    print("\n=== 政策关注领域 ===")
    sectors = get_focus_sectors()
    for i, s in enumerate(sectors, 1):
        print(f"{i}. {s}")
