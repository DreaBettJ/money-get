"""政策关键词提取系统 V2

从政府官网/权威媒体获取政策文件，提取关键词
- 时效性：新政策/旧政策
- 重要程度：国家级/部委级/地方级
"""
import re
import time
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from enum import Enum

# 使用统一的日志配置
from money_get.core.logger import get_logger
logger = get_logger("money_get.policy")

# Playwright 是可选依赖
try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    logger.warning("⚠️ Playwright 未安装，将使用备用数据源，政策信息可能不完整")
    logger.info("💡 安装 Playwright: pip install playwright && playwright install chromium")

# 请求间隔（秒）
REQUEST_DELAY = 2.0
_last_request_time = 0


class PolicyLevel(Enum):
    """政策重要程度"""
    NATIONAL = "国家级"      # 党中央、国务院
    MINISTRY = "部委级"      # 各部委
    LOCAL = "地方级"        # 省市


class PolicyTimeliness(Enum):
    """政策时效性"""
    NEW = "新政策"          # 7天内
    RECENT = "近期"         # 30天内
    OLD = "旧政策"          # 30天前


def _delay():
    """控制请求频率"""
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < REQUEST_DELAY:
        time.sleep(REQUEST_DELAY - elapsed)
    _last_request_time = time.time()


# 重要程度关键词映射
LEVEL_KEYWORDS = {
    PolicyLevel.NATIONAL: [
        "党中央", "国务院", "中共中央", "全国", "中央", "总书记", 
        "国务院关于", "中共中央办公厅", "国务院办公厅", "全国人大",
        "十四五", "2035", "远景目标", "规划纲要"
    ],
    PolicyLevel.MINISTRY: [
        "工信部", "发改委", "财政部", "商务部", "科技部", "教育部",
        "卫健委", "生态环境部", "住建部", "交通运输部", "农业农村部",
        "央行", "证监会", "银保监会", "自然资源部", "文旅部"
    ],
    PolicyLevel.LOCAL: [
        "省", "市", "县", "区", "镇", "乡", "自治区", "直辖市",
        "省委", "市政府", "区县", "开发区"
    ]
}


# 时间关键词
TIME_KEYWORDS = {
    PolicyTimeliness.NEW: ["今日", "昨天", "本周", "本月", "最新", "刚刚"],
    PolicyTimeliness.RECENT: ["近日", "近期", "本月", "本年", "今年"],
}


def _extract_date_from_text(text: str) -> Optional[datetime]:
    """从文本中提取日期"""
    # 常见日期格式
    patterns = [
        r'(\d{4})年(\d{1,2})月(\d{1,2})日',
        r'(\d{4})-(\d{1,2})-(\d{1,2})',
        r'(\d{4})/(\d{1,2})/(\d{1,2})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
            except:
                pass
    
    return None


def _judge_level(title: str) -> PolicyLevel:
    """判断政策重要程度"""
    title = title.lower()
    
    # 国家级优先匹配
    for keyword in LEVEL_KEYWORDS[PolicyLevel.NATIONAL]:
        if keyword in title:
            return PolicyLevel.NATIONAL
    
    # 部委级
    for keyword in LEVEL_KEYWORDS[PolicyLevel.MINISTRY]:
        if keyword in title:
            return PolicyLevel.MINISTRY
    
    # 地方级
    for keyword in LEVEL_KEYWORDS[PolicyLevel.LOCAL]:
        if keyword in title:
            return PolicyLevel.LOCAL
    
    return PolicyLevel.MINISTRY  # 默认部委级


def _judge_timeliness(title: str, text: str = "") -> PolicyTimeliness:
    """判断政策时效性"""
    now = datetime.now()
    
    # 1. 尝试从文本提取日期
    date = _extract_date_from_text(title + text)
    if date:
        days = (now - date).days
        if days <= 7:
            return PolicyTimeliness.NEW
        elif days <= 30:
            return PolicyTimeliness.RECENT
        else:
            return PolicyTimeliness.OLD
    
    # 2. 从标题关键词判断
    for keyword in TIME_KEYWORDS[PolicyTimeliness.NEW]:
        if keyword in title:
            return PolicyTimeliness.NEW
    
    for keyword in TIME_KEYWORDS[PolicyTimeliness.RECENT]:
        if keyword in title:
            return PolicyTimeliness.RECENT
    
    # 3. 默认返回近期
    return PolicyTimeliness.RECENT


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
            logger.info(f"获取页面失败: {url}, {e}")
            return None
        finally:
            browser.close()


def get_gov_policy_keywords() -> List[Dict]:
    """获取政府政策关键词（带时效性和重要程度）
    
    从中国政府网、新华网等获取政策文件
    """
    if not HAS_PLAYWRIGHT:
        return _get_policy_fallback()
    
    keywords = []
    
    # 1. 中国政府网 - 政策文件
    logger.info("获取中国政府网政策...")
    content = fetch_with_playwright("https://www.gov.cn/zhengce/zuixin.htm")
    if content:
        policies = _extract_policy_info(content, "中国政府网")
        keywords.extend(policies)
    
    # 2. 央广网 - 政策解读
    logger.info("获取央广网政策...")
    content = fetch_with_playwright("https://news.cnr.cn/")
    if content:
        policies = _extract_policy_info(content, "央广网")
        keywords.extend(policies)
    
    # 去重
    unique = _dedup_keywords(keywords)
    
    return unique[:30]


def _extract_policy_info(html: str, source: str) -> List[Dict]:
    """从HTML中提取政策信息"""
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
        if any(x in title for x in ['登录', '注册', '更多', '>>', '图片', '视频', '滚动', '返回']):
            continue
        
        # 判断重要程度
        level = _judge_level(title)
        
        # 判断时效性
        timeliness = _judge_timeliness(title)
        
        # 提取行业领域
        sectors = _extract_sectors(title)
        
        keywords.append({
            'title': title,
            'source': source,
            'sectors': sectors,
            'level': level.value,
            'timeliness': timeliness.value,
        })
    
    return keywords


def _extract_sectors(text: str) -> List[str]:
    """从文本中提取行业/领域"""
    text = text.lower()
    
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
        key = kw['title'][:15]
        if key not in seen:
            seen.add(key)
            unique.append(kw)
    
    return unique


def _get_policy_fallback() -> List[Dict]:
    """备用方案：无数据时返回空"""
    logger.warning("⚠️ 无可用政策数据源，请安装 Playwright 获取真实数据")
    return []


def get_focus_sectors(policy_level: str = None, timeliness: str = None) -> List[str]:
    """获取当前政策关注领域
    
    Args:
        policy_level: 筛选重要程度 (国家级/部委级/地方级)
        timeliness: 筛选时效性 (新政策/近期/旧政策)
    
    Returns:
        list: 热门行业列表
    """
    policies = get_gov_policy_keywords()
    
    # 过滤
    if policy_level:
        policies = [p for p in policies if p.get('level') == policy_level]
    if timeliness:
        policies = [p for p in policies if p.get('timeliness') == timeliness]
    
    # 统计行业出现频次
    sector_count = {}
    for p in policies:
        for sector in p.get('sectors', []):
            sector_count[sector] = sector_count.get(sector, 0) + 1
    
    # 按频次排序
    sorted_sectors = sorted(sector_count.items(), key=lambda x: x[1], reverse=True)
    
    return [s[0] for s in sorted_sectors[:10]]


def get_priority_policies(limit: int = 5) -> List[Dict]:
    """获取优先政策（新政策 + 国家级）
    
    Args:
        limit: 返回数量
    
    Returns:
        list: 高优先级政策列表
    """
    policies = get_gov_policy_keywords()
    
    # 优先级排序
    def priority(p):
        score = 0
        # 国家级 +3，部委级 +2，地方级 +1
        if p.get('level') == '国家级':
            score += 3
        elif p.get('level') == '部委级':
            score += 2
        
        # 新政策 +2，近期 +1
        if p.get('timeliness') == '新政策':
            score += 2
        elif p.get('timeliness') == '近期':
            score += 1
        
        return -score  # 降序
    
    policies.sort(key=priority)
    
    return policies[:limit]


# 测试
if __name__ == "__main__":
    logger.info("=== 政策关键词提取 V2 ===\n")
    
    policies = get_gov_policy_keywords()
    
    logger.info(f"获取到 {len(policies)} 条政策\n")
    
    # 打印高优先级政策
    logger.info("=== 高优先级政策（新政策+国家级）===\n")
    priority = get_priority_policies(5)
    for i, p in enumerate(priority, 1):
        sectors = p.get('sectors', [])
        s = f" [{', '.join(sectors)}]" if sectors else ""
        logger.info(f"{i}. [{p['level']}][{p['timeliness']}] {p['title'][:40]}{s}")
    
    # 按级别统计
    logger.info("\n=== 政策级别统计 ===")
    levels = {}
    for p in policies:
        l = p.get('level', '未知')
        levels[l] = levels.get(l, 0) + 1
    for l, count in levels.items():
        logger.info(f"  {l}: {count}条")
    
    # 按时效统计
    logger.info("\n=== 政策时效统计 ===")
    times = {}
    for p in policies:
        t = p.get('timeliness', '未知')
        times[t] = times.get(t, 0) + 1
    for t, count in times.items():
        logger.info(f"  {t}: {count}条")
    
    # 提取领域
    logger.info("\n=== 政策关注领域 ===")
    sectors = get_focus_sectors()
    logger.info(f"  {', '.join(sectors)}")
