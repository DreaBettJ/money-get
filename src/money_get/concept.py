"""概念板块匹配系统

从政策关键词匹配到概念板块，再获取成分股

映射表使用东方财富实际概念名称
"""
from typing import List, Dict, Optional
import time

REQUEST_DELAY = 0.5
_last_request_time = 0


def _delay():
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < REQUEST_DELAY:
        time.sleep(REQUEST_DELAY - elapsed)
    _last_request_time = time.time()


# 政策关键词 → 东方财富概念板块 映射表
CONCEPT_KEYWORD_MAP = {
    # 新能源
    "新能源": [
        "电动乘用车", "新能源汽车", "锂电池", "动力电池", "储能", 
        "锂电专用设备", "光伏", "风电", "核电", "电力", "电网"
    ],
    "新能源汽车": [
        "电动乘用车", "新能源汽车", "锂电池", "动力电池", "充电桩", 
        "汽车", "汽车零部件", "汽车电子电气系统"
    ],
    "光伏": [
        "光伏", "半导体设备", "半导体材料"
    ],
    "储能": [
        "储能", "锂电池", "动力电池", "电网", "电力"
    ],
    "风电": [
        "风电", "海洋捕捞", "航海装备"
    ],
    "电力": [
        "电力", "电网", "绿色电力", "风电", "光伏"
    ],
    "电网": [
        "电网", "电力设备", "配电", "自动化设备"
    ],
    
    # 人工智能/科技
    "人工智能": [
        "机器人", "计算机设备", "消费电子", "人工智能", "数字芯片设计",
        "模拟芯片设计", "集成电路制造", "半导体"
    ],
    "AI": [
        "人工智能", "机器人", "计算机设备", "消费电子"
    ],
    "芯片": [
        "半导体", "集成电路制造", "集成电路封测", "数字芯片设计", 
        "模拟芯片设计", "半导体设备", "半导体材料", "光刻机"
    ],
    "半导体": [
        "半导体", "集成电路制造", "数字芯片设计", "模拟芯片设计",
        "半导体设备", "半导体材料", "集成电路封测"
    ],
    "云计算": [
        "云计算", "数据中心", "数字经济", "软件"
    ],
    "大数据": [
        "大数据", "数字经济", "数据中心", "金融信息服务"
    ],
    "数字经济": [
        "数字经济", "云计算", "大数据", "数字媒体", "数字芯片设计"
    ],
    "软件": [
        "横向通用软件", "国产软件", "信创", "操作系统"
    ],
    "信息安全": [
        "信息安全", "网络安全", "安防设备", "军工电子"
    ],
    "机器人": [
        "机器人", "自动化设备", "工业机器人", "服务机器人"
    ],
    "计算机": [
        "计算机设备", "其他计算机设备", "人工智能"
    ],
    "消费电子": [
        "消费电子", "消费电子零部件及组装", "电子", "LED"
    ],
    
    # 医药医疗
    "医药医疗": [
        "医疗器械", "生物医药", "中药", "化学制药", "医药商业",
        "医疗服务", "疫苗", "创新药"
    ],
    "医药": [
        "医疗器械", "生物医药", "化学制药", "医药商业", "中药"
    ],
    "医疗器械": [
        "医疗器械", "医疗设备", "体外诊断", "耗材"
    ],
    "生物医药": [
        "生物医药", "疫苗", "创新药", "CXO"
    ],
    "中药": [
        "中药", "中医药", "中药材"
    ],
    "创新药": [
        "创新药", "生物医药", "化学制药", "CXO"
    ],
    
    # 高端制造
    "高端制造": [
        "机器人", "自动化设备", "工业母机", "数控机床", "高端装备",
        "航空航天", "军工", "军工电子", "航天装备"
    ],
    "工业母机": [
        "工业母机", "数控机床", "刀具", "机床", "仪器仪表"
    ],
    "智能制造": [
        "智能制造", "工业互联网", "工业软件", "自动化设备", "机器人"
    ],
    "军工": [
        "军工", "国防军工", "航空航天", "航天装备", "军工电子",
        "地面兵装", "船舶"
    ],
    "航空航天": [
        "航空航天", "航天装备", "军工", "航空装备"
    ],
    "航空装备": [
        "航空装备", "航空航天", "军工", "无人机"
    ],
    
    # 绿色低碳
    "绿色低碳": [
        "碳中和", "环保", "大气治理", "污水处理", "节能减排",
        "绿色电力", "垃圾发电"
    ],
    "碳中和": [
        "碳中和", "环保", "大气治理", "绿色电力"
    ],
    "环保": [
        "环保", "大气治理", "污水处理", "垃圾发电", "碳中和"
    ],
    
    # 消费
    "消费": [
        "大消费", "食品饮料", "家电", "汽车", "纺织服装",
        "餐饮", "旅游综合", "酒店", "免税", "零售"
    ],
    "食品饮料": [
        "食品饮料", "白酒", "啤酒", "乳业", "调味品", "休闲食品"
    ],
    "白酒": [
        "白酒", "酿酒", "啤酒", "食品饮料"
    ],
    "家电": [
        "白色家电", "小家电", "个护小家电", "厨房小家电", "冰洗"
    ],
    "汽车": [
        "汽车", "汽车整车", "新能源汽车", "汽车零部件", 
        "汽车电子电气系统", "电动乘用车"
    ],
    "旅游": [
        "旅游综合", "人工景区", "酒店", "航空", "免税"
    ],
    "酒店": [
        "酒店", "酒店餐饮", "旅游综合"
    ],
    "零售": [
        "零售", "免税", "消费电子"
    ],
    
    # 金融
    "金融": [
        "银行", "保险", "证券", "多元金融", "互联网金融"
    ],
    "银行": [
        "银行", "国有大行", "股份制银行", "城商行"
    ],
    "保险": [
        "保险", "寿险", "财险"
    ],
    "证券": [
        "证券", "券商"
    ],
    
    # 农业
    "农业": [
        "种植业", "养殖业", "农林牧渔", "乡村振兴",
        "种子", "农机", "猪周期", "林业"
    ],
    "乡村振兴": [
        "乡村振兴", "种植业", "养殖业", "种子", "农机"
    ],
    "种业": [
        "种子", "转基因", "种植业", "农业"
    ],
    "养殖": [
        "养殖业", "猪周期", "水产养殖", "海洋捕捞"
    ],
    
    # 基建地产
    "基建地产": [
        "房地产", "建筑", "建材", "水泥", "钢铁",
        "园林工程", "装饰", "家居", "物业管理"
    ],
    "房地产": [
        "房地产", "物业管理", "园林工程", "建材", "家电"
    ],
    "建筑": [
        "建筑", "基建", "水利", "管网", "工程咨询服务"
    ],
    "建材": [
        "建材", "水泥", "玻璃", "涂料", "防水", "塑料包装"
    ],
    "水泥": [
        "水泥", "建材", "混凝土"
    ],
    "园林": [
        "园林工程", "房地产", "旅游综合"
    ],
    "物业管理": [
        "物业管理", "房地产综合服务"
    ],
    
    # 国防军工
    "国防": [
        "国防军工", "军工", "航空航天", "航天装备", "军工电子",
        "航空装备", "地面兵装", "船舶", "无人机"
    ],
    
    # 电力
    "电力": [
        "电力", "绿色电力", "水电", "火电", "核电",
        "风电", "光伏", "电网", "虚拟电厂"
    ],
    
    # 交通运输
    "交通运输": [
        "航空", "机场", "航运", "港口", "公路", "铁路",
        "物流", "快递", "公交", "公路货运"
    ],
    "物流": [
        "物流", "快递", "供应链", "跨境物流", "端到端供应链服务"
    ],
    "航空": [
        "航空", "航空装备", "航天装备", "航空航天"
    ],
    
    # 传媒
    "传媒": [
        "传媒", "游戏", "影视院线", "影视", "院线",
        "出版", "数字媒体", "元宇宙", "文字媒体"
    ],
    "游戏": [
        "游戏", "网络游戏", "云游戏", "电竞"
    ],
    "影视": [
        "影视院线", "院线", "电影", "影视", "文字媒体"
    ],
    "元宇宙": [
        "元宇宙", "虚拟现实", "AR/VR", "数字媒体", "游戏"
    ],
    
    # 电子
    "电子": [
        "电子", "消费电子", "半导体", "光学光电子", "元器件",
        "PCB", "集成电路", "传感器", "LED"
    ],
    "消费电子": [
        "消费电子", "消费电子零部件及组装", "手机", "智能穿戴", "VR/AR"
    ],
    
    # 体育/娱乐
    "体育": [
        "体育", "体育Ⅱ", "体育Ⅲ"
    ],
    "娱乐": [
        "娱乐用品", "游戏", "影视院线", "旅游综合"
    ],
}


def get_concept_list() -> List[Dict]:
    """获取东方财富概念板块列表"""
    import requests
    
    _delay()
    
    url = "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=200&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m:90+t:2+f:!50&fields=f2,f3,f4,f12,f13,f14,f128"
    
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        
        concepts = []
        if data.get('data') and data['data'].get('diff'):
            for item in data['data']['diff']:
                concepts.append({
                    'name': item.get('f14'),  # 概念名称
                    'code': item.get('f12'),   # 概念代码
                    'change': item.get('f2', 0),
                    'stock_count': item.get('f4', 0),
                })
        
        return concepts
    
    except Exception as e:
        _logger.info(f"获取概念板块失败: {e}")
        return []


def match_concepts(keywords: List[str]) -> List[str]:
    """根据政策关键词匹配概念板块
    
    Args:
        keywords: 政策关键词列表
    
    Returns:
        list: 匹配到的概念板块列表
    """
    matched = set()
    
    for keyword in keywords:
        keyword = keyword.lower()
        
        # 精确匹配
        for key, concepts in CONCEPT_KEYWORD_MAP.items():
            if keyword in key.lower() or key in keyword:
                matched.update(concepts)
    
    return list(matched)


def get_concept_stocks(concept_name: str, limit: int = 30) -> List[Dict]:
    """获取概念板块成分股
    
    Args:
        concept_name: 概念名称
        limit: 返回数量
    
    Returns:
        list: 成分股列表
    """
    import requests
    
    _delay()
    
    # 获取概念板块列表
    url = "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=200&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m:90+t:2+f:!50&fields=f2,f3,f4,f12,f13,f14,f128"
    
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        
        # 找到匹配的概念
        concept_code = None
        if data.get('data') and data['data'].get('diff'):
            for item in data['data']['diff']:
                if concept_name in item.get('f14', ''):
                    concept_code = item.get('f12')
                    break
        
        if not concept_code:
            return []
        
        # 获取成分股
        url2 = f"https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz={limit}&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=b:{concept_code}&fields=f2,f3,f4,f12,f13,f14,f128"
        
        resp2 = requests.get(url2, timeout=10)
        data2 = resp2.json()
        
        stocks = []
        if data2.get('data') and data2['data'].get('diff'):
            for item in data2['data']['diff']:
                stocks.append({
                    'code': item.get('f12'),
                    'name': item.get('f14'),
                    'change': item.get('f2', 0),
                    'concept': concept_name
                })
        
        return stocks
    
    except Exception as e:
        _logger.info(f"获取概念成分股失败: {e}")
        return []


def select_by_policy_concepts(policy_keywords: List[str], top_n: int = 30) -> List[Dict]:
    """根据政策关键词选股
    
    Args:
        policy_keywords: 政策关键词
        top_n: 返回数量
    
    Returns:
        list: 候选股票列表
    """
    # 1. 匹配概念
    concepts = match_concepts(policy_keywords)
    
    if not concepts:
        print("未匹配到概念板块")
        return []
    
    _logger.info(f"匹配到 {len(concepts)} 个概念: {concepts[:5]}...")
    
    # 2. 获取成分股
    all_stocks = []
    for concept in concepts[:5]:  # 最多取5个概念
        stocks = get_concept_stocks(concept, limit=20)
        all_stocks.extend(stocks)
    
    # 3. 去重
    seen = set()
    unique = []
    for s in all_stocks:
        if s['code'] not in seen:
            seen.add(s['code'])
            unique.append(s)
    
    return unique[:top_n]


# 测试
if __name__ == "__main__":
    print("=== 概念板块匹配测试 ===\n")
    
    keywords = ["新能源", "人工智能", "医药"]
    
    concepts = match_concepts(keywords)
    _logger.info(f"关键词: {keywords}")
    _logger.info(f"匹配概念: {len(concepts)} 个")
    for c in concepts[:10]:
        _logger.info(f"  - {c}")
    print()
    
    # 获取第一个概念的成分股
    if concepts:
        _logger.info(f"获取概念成分股: {concepts[0]}")
        stocks = get_concept_stocks(concepts[0], limit=5)
        for s in stocks:
            _logger.info(f"  {s['code']} {s['name']}")
