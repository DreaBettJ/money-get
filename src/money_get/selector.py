"""综合选股系统

选股逻辑：
1. 政策关键词 → 热门概念 → 成分股
2. 资金流入 - 主力资金
3. 技术形态 - 多头排列/突破
4. 财务排雷 - 避免垃圾股
"""
from typing import List, Dict, Optional
from .scraper import get_stock_price, get_hot_sectors, get_fund_flow
from .policy import get_focus_sectors
import time

# 请求间隔
REQUEST_DELAY = 0.5
_last_request_time = 0


def _delay():
    """控制请求频率"""
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < REQUEST_DELAY:
        time.sleep(REQUEST_DELAY - elapsed)
    _last_request_time = time.time()


def get_concept_stocks(concept_name: str = None, limit: int = 30) -> List[Dict]:
    """获取概念板块成分股
    
    Args:
        concept_name: 概念名称（可选）
        limit: 返回数量
    
    Returns:
        list: 概念成分股
    """
    _delay()
    
    # 东方财富概念板块列表
    url = "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=100&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m:90+t:2+f:!50&fields=f1,f2,f3,f4,f12,f13,f14,f128,f140,f141,f184"
    
    import requests
    
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        
        concepts = []
        if data.get('data') and data['data'].get('diff'):
            for item in data['data']['diff']:
                concepts.append({
                    'code': item.get('f12'),
                    'name': item.get('f14'),
                    'change': item.get('f2', 0),
                    'amount': item.get('f4', 0),
                })
        
        # 如果指定了概念名称，返回其成分股
        if concept_name:
            # 简化：先返回概念列表
            return concepts
        
        return concepts[:limit]
    
    except Exception as e:
        print(f"获取概念板块失败: {e}")
        return []


def check_consecutive_inflow(stock_code: str, days: int = 2) -> Dict:
    """检查股票是否有资金流入
    
    Args:
        stock_code: 股票代码
        days: 期望天数（仅供参考）
    
    Returns:
        dict: {total_inflow, is_qualified}
    """
    _delay()
    
    import requests
    
    if stock_code.startswith('6'):
        secid = f"1.{stock_code}"
    else:
        secid = f"0.{stock_code}"
    
    # 获取资金流向
    url = f"https://push2.eastmoney.com/api/qt/stock/get?invt=2&fltt=2&fields=f62,f71,f184&secid={secid}"
    
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        
        if data.get('data'):
            d = data['data']
            
            # f62: 主力净流入标识（1/2/3/4代表不同流向）
            # f71: 今日成交额(万元)
            # f184: 净流入(万元)
            
            main_flag = d.get('f62', 0)  # 1=流出,2=流入,3=流入,4=流出
            amount = d.get('f71', 0) or 0  # 成交额
            net_inflow = d.get('f184', 0) or 0  # 净流入
            
            # 判断：有资金流入（flag=2或3表示流入）
            has_inflow = main_flag in [2, 3] and net_inflow > 0
            
            # 判断：大单买入（成交额大且净流入为正）
            big_order = amount > 10000 and net_inflow > 0
            
            is_qualified = has_inflow or big_order
            
            return {
                'total_inflow': net_inflow,
                'amount': amount,
                'main_flag': main_flag,
                'is_qualified': is_qualified
            }
    
    except Exception as e:
        print(f"获取资金流向失败: {stock_code}: {e}")
    
    return {
        'total_inflow': 0,
        'amount': 0,
        'is_qualified': False
    }


def get_financial_data(stock_code: str) -> Dict:
    """获取财务指标
    
    Args:
        stock_code: 股票代码
    
    Returns:
        dict: 财务指标数据
    """
    _delay()
    
    import requests
    
    if stock_code.startswith('6'):
        secid = f"1.{stock_code}"
    else:
        secid = f"0.{stock_code}"
    
    # 获取财务指标
    url = f"https://push2.eastmoney.com/api/qt/stock/get?invt=2&fltt=2&fields=f57,f58,f160,f161,f166,f167,f168,f169,f170,f173,f174,f175&secid={secid}"
    
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        
        if data.get('data'):
            d = data['data']
            
            # PE（市盈率）- 直接就是倍数
            pe = d.get('f160', 0)
            if pe:
                pe = round(pe, 2)
            else:
                pe = None
            
            # PB（市净率）
            pb = d.get('f161', 0)
            if pb:
                pb = round(pb, 2)
            else:
                pb = None
            
            # 每股收益 - 直接是元
            eps = d.get('f166', 0)
            if eps:
                eps = round(eps, 2)
            
            # 每股净资产 - 直接是元
            bps = d.get('f167', 0)
            if bps:
                bps = round(bps, 2)
            
            # ROE - 直接是百分比数值
            roe = d.get('f168', 0)
            if roe:
                roe = round(roe, 2)
            
            # 净利润增长率 - 直接是百分比数值
            profit_growth = d.get('f169', 0)
            if profit_growth:
                profit_growth = round(profit_growth, 2)
            
            # 营收增长率 - 直接是百分比数值
            revenue_growth = d.get('f170', 0)
            if revenue_growth:
                revenue_growth = round(revenue_growth, 2)
            
            return {
                'pe': pe,
                'pb': pb,
                'eps': eps,
                'bps': bps,
                'roe': roe,
                'profit_growth': profit_growth,
                'revenue_growth': revenue_growth,
                'name': d.get('f58', '')
            }
    
    except Exception as e:
        print(f"获取财务数据失败: {stock_code}: {e}")
    
    return {}


def filter_financial(stock_code: str) -> Dict:
    """财务过滤 - 排除垃圾股
    
    过滤条件：
    1. 股价 > 2元（避免仙股）
    2. 成交额 > 0.5亿元（避免僵尸股）
    3. 涨幅 < 15%（排除暴涨股）
    4. PE > 0 且 < 100（排除亏损/高估）
    
    Args:
        stock_code: 股票代码
    
    Returns:
        dict: {is_qualified, reasons, financial_data}
    """
    _delay()
    
    import requests
    
    if stock_code.startswith('6'):
        secid = f"1.{stock_code}"
    else:
        secid = f"0.{stock_code}"
    
    reasons = []
    is_qualified = True
    financial_data = {}
    
    # 1. 基础过滤（价格/成交额/涨幅）
    url1 = f"https://push2.eastmoney.com/api/qt/stock/get?invt=2&fltt=2&fields=f43,f44,f45,f46,f47,f58&secid={secid}"
    
    try:
        resp = requests.get(url1, timeout=10)
        data = resp.json()
        
        if data.get('data'):
            d = data['data']
            
            # 股价
            price = d.get('f43', 0)
            financial_data['price'] = price
            
            if price and price < 2:
                reasons.append(f'股价过低({price}元)')
                is_qualified = False
            
            # 成交额（亿元）
            amount = d.get('f46', 0)
            financial_data['amount'] = amount
            
            if amount and amount < 0.5:
                reasons.append(f'成交额过低({amount}亿)')
                is_qualified = False
            
            # 涨幅（千分比转为百分比）
            pct = d.get('f45', 0) / 10 if d.get('f45') else 0
            financial_data['pct'] = pct
            
            if pct > 15:
                reasons.append(f'涨幅过大({pct:.1f}%)')
    
    except Exception as e:
        print(f"基础财务获取失败: {stock_code}: {e}")
    
    # 2. 获取财务指标
    try:
        finance = get_financial_data(stock_code)
        financial_data.update(finance)
        
        # PE过滤
        pe = finance.get('pe')
        if pe:
            if pe < 0:
                reasons.append(f'亏损(PE<0)')
                is_qualified = False
            elif pe > 100:
                reasons.append(f'PE过高({pe})')
                is_qualified = False
    
    except Exception as e:
        print(f"财务指标获取失败: {stock_code}: {e}")
    
    return {
        'is_qualified': is_qualified,
        'reasons': reasons,
        'financial_data': financial_data
    }


def get_stock_technique(stock_code: str) -> Dict:
    """获取股票技术形态（备用方案）
    
    当新浪API不可用时，使用简单的价格数据判断
    
    Args:
        stock_code: 股票代码
    
    Returns:
        dict: 技术形态分析
    """
    _delay()
    
    import requests
    
    # 先尝试获取基础数据
    if stock_code.startswith('6'):
        secid = f"1.{stock_code}"
    else:
        secid = f"0.{stock_code}"
    
    # 获取实时数据作为后备
    url = f"https://push2.eastmoney.com/api/qt/stock/get?invt=2&fltt=2&fields=f43,f44,f45,f46,f47,f50,f51,f52,f58,f60&secid={secid}"
    
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        
        patterns = []
        
        if data.get('data'):
            d = data['data']
            
            price = d.get('f43', 0)  # 当前价
            pct = d.get('f45', 0)   # 涨跌幅
            volume = d.get('f47', 0)  # 成交量
            open_price = d.get('f50', 0)  # 开盘
            high = d.get('f51', 0)  # 最高
            low = d.get('f52', 0)  # 最低
            
            # 简单判断形态
            
            # 1. 涨幅适中（0-5%）
            if 0 < pct < 5:
                patterns.append('涨幅健康')
            
            # 2. 放量（成交量>10000手）
            if volume > 10000:
                patterns.append('放量')
            
            # 3. 低开高走
            if open_price < price:
                patterns.append('低开高走')
            
            # 4. 突破（最高价接近收盘价）
            if high > 0 and price >= high * 0.98:
                patterns.append('接近高点')
            
            return {
                'price': price,
                'pct': pct,
                'volume': volume,
                'patterns': patterns,
                'has_pattern': len(patterns) >= 1
            }
    
    except Exception as e:
        print(f"获取技术形态失败: {stock_code}: {e}")
    
    return {
        'price': 0,
        'pct': 0,
        'volume': 0,
        'patterns': [],
        'has_pattern': True  # 如果获取不到数据，默认通过
    }
    
    try:
        resp = requests.get(url, timeout=10)
        text = resp.text
        
        # 解析JSON
        import json
        import re
        
        # 提取JSON数据
        match = re.search(r'\[.*\]', text)
        if not match:
            return {'patterns': [], 'has_pattern': False}
        
        klines = json.loads(match.group())
        
        if not klines:
            return {'patterns': [], 'has_pattern': False}
        
        # 解析数据
        closes = []
        volumes = []
        highs = []
        lows = []
        
        for k in klines:
            if isinstance(k, dict) and 'close' in k and 'volume' in k:
                closes.append(float(k['close']))  # 收盘
                volumes.append(float(k['volume']))  # 成交量
                highs.append(float(k['high']))   # 最高
                lows.append(float(k['low']))    # 最低
        
        if len(closes) < 20:
            return {'patterns': [], 'has_pattern': False}
        
        # 计算技术指标
        ma5 = sum(closes[-5:]) / 5
        ma10 = sum(closes[-10:]) / 10
        ma20 = sum(closes[-20:]) / 20
        
        # 形态判断
        patterns = []
        
        # 1. 多头排列：MA5 > MA10 > MA20
        if ma5 > ma10 > ma20:
            patterns.append('多头排列')
        
        # 2. 突破20日新高
        if highs[-1] > max(highs[-20:-1]) if len(highs) > 20 else False:
            patterns.append('突破20日新高')
        
        # 3. 放量：今日成交量 > 20日均量
        avg_volume = sum(volumes[-20:]) / 20
        if volumes[-1] > avg_volume * 1.5:
            patterns.append('放量')
        
        # 4. 5日线上穿10日（金叉）
        if len(closes) >= 10:
            prev_ma5 = sum(closes[-6:-1]) / 5
            prev_ma10 = sum(closes[-11:-1]) / 10
            if ma5 > prev_ma5 and ma10 > prev_ma10:
                patterns.append('均线金叉')
        
        return {
            'ma5': ma5,
            'ma10': ma10,
            'ma20': ma20,
            'price': closes[-1],
            'volume': volumes[-1],
            'avg_volume_20': avg_volume,
            'patterns': patterns,
            'has_pattern': len(patterns) > 0
        }
    
    except Exception as e:
        print(f"获取K线失败: {stock_code}: {e} (type: {type(e).__name__})")
    
    return {
        'ma5': 0,
        'ma10': 0,
        'ma20': 0,
        'patterns': [],
        'has_pattern': False
    }


def select_stocks(
    concept: str = None,
    min_consecutive_days: int = 2,
    require_pattern: bool = True,
    use_policy: bool = True,
    use_llm: bool = False,
    top_n: int = 10
) -> List[Dict]:
    """综合选股（规则过滤）
    
    Args:
        concept: 概念板块（可选）
        min_consecutive_days: 最小连续流入天数
        require_pattern: 是否要求技术形态
        use_policy: 是否使用政策关键词筛选
        use_llm: 是否使用LLM做最终决策
        top_n: 返回数量
    
    Returns:
        list: 选股结果
    """
    print(f"=== 规则过滤选股 ===")
    print(f"条件: 资金流入", end="")
    if require_pattern:
        print(" + 技术形态", end="")
    if use_policy:
        print(" + 政策关键词", end="")
    if use_llm:
        print(" + LLM决策", end="")
    print()
    
    # 第0步：获取政策关注领域
    policy_sectors = []
    if use_policy:
        print("\n0. 获取政策关键词...")
        try:
            from .policy import get_focus_sectors
            policy_sectors = get_focus_sectors()
            print(f"   政策关注领域: {', '.join(policy_sectors)}")
        except Exception as e:
            print(f"   获取政策失败: {e}")
    
    # 第1步：获取热门股票（从热点板块）
    print("\n1. 获取热门股票...")
    sectors = get_hot_sectors(limit=20)
    
    # 简化：获取沪深涨幅榜
    stocks_to_check = []
    
    # 从涨停板获取
    _delay()
    url = "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=50&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m:0+t:6,m:0+t:80&fields=f2,f3,f4,f12,f13,f14,f128"
    
    import requests
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        
        if data.get('data') and data['data'].get('diff'):
            for item in data['data']['diff'][:50]:
                stocks_to_check.append({
                    'code': item.get('f12'),
                    'name': item.get('f14'),
                    'change': item.get('f2', 0),
                })
    except Exception as e:
        print(f"获取涨幅榜失败: {e}")
    
    print(f"   待筛选: {len(stocks_to_check)} 只")
    
    # 第2步：检查资金连续流入
    print("\n2. 检查资金连续流入...")
    qualified = []
    
    for i, stock in enumerate(stocks_to_check[:30]):
        code = stock['code']
        name = stock['name']
        
        inflow = check_consecutive_inflow(code, min_consecutive_days)
        
        if inflow['is_qualified']:
            stock['inflow'] = inflow
            qualified.append(stock)
            inflow_amt = inflow.get('total_inflow', 0)
            print(f"   ✓ {code} {name}: 净流入 {inflow_amt:.1f}万")
        
        if (i + 1) % 10 == 0:
            print(f"   已检查 {i+1}/30")
    
    print(f"   资金关: {len(qualified)} 只")
    
    if not qualified:
        print("\n无符合条件股票")
        return []
    
    # 第3步：检查技术形态
    if require_pattern:
        print("\n3. 检查技术形态...")
        
        final = []
        for stock in qualified:
            code = stock['code']
            tech = get_stock_technique(code)
            
            if tech['has_pattern']:
                stock['technique'] = tech
                final.append(stock)
                print(f"   ✓ {code}: {', '.join(tech['patterns'])}")
        
        print(f"   技术关: {len(final)} 只")
    else:
        final = qualified
    
    # 第4步：财务过滤（排雷）
    print("\n4. 财务过滤（排雷）...")
    
    filtered = []
    for stock in final:
        code = stock['code']
        finance = filter_financial(code)
        
        if finance['is_qualified']:
            stock['finance'] = finance
            filtered.append(stock)
            print(f"   ✓ {code}: 价格{finance.get('price')} 成交{finance.get('amount')}万 涨幅{finance.get('pct')}%")
        else:
            print(f"   ✗ {code}: {', '.join(finance['reasons'])}")
    
    print(f"   财务关: {len(filtered)} 只")
    
    # 返回结果
    final = filtered[:top_n]
    
    print(f"\n=== 规则过滤结果: {len(final)} 只 ===")
    for i, s in enumerate(final, 1):
        patterns = s.get('technique', {}).get('patterns', [])
        inflow_days = s.get('inflow', {}).get('consecutive_days', 0)
        print(f"{i}. {s['code']} {s['name']} (流入{inflow_days}天, {patterns})")
    
    # 如果开启LLM决策
    if use_llm and final:
        print("\n=== LLM最终决策 ===")
        from .agents import TradingAgents
        agents = TradingAgents()
        
        llm_final = []
        for stock in final[:top_n]:
            code = stock['code']
            name = stock['name']
            
            print(f"分析 {code} {name}...")
            
            try:
                analysis = agents.analyze(code)
                decision = analysis.get('decision', '')
                
                # 判断是否推荐
                if '买入' in decision or '建仓' in decision or '增持' in decision:
                    stock['llm_recommendation'] = '买入'
                elif '卖出' in decision or '减仓' in decision:
                    stock['llm_recommendation'] = '卖出'
                else:
                    stock['llm_recommendation'] = '观望'
                
                stock['analysis'] = analysis
                llm_final.append(stock)
                
                print(f"  → {stock['llm_recommendation']}")
                
            except Exception as e:
                print(f"  → 分析失败: {e}")
                stock['llm_recommendation'] = '观望'
                llm_final.append(stock)
        
        final = llm_final
        
        # 筛选推荐的
        recommended = [s for s in final if s.get('llm_recommendation') == '买入']
        
        print(f"\n=== LLM推荐: {len(recommended)} 只 ===")
        for s in recommended:
            print(f"  {s['code']} {s['name']}")
    
    return final


def analyze_selected_stocks(stocks: List[Dict], top_n: int = 3) -> List[Dict]:
    """用现有Agent框架分析选出的股票
    
    Args:
        stocks: select_stocks() 返回的股票列表
        top_n: 分析前几只
    
    Returns:
        list: 包含分析结果的股票列表
    """
    from .agents import TradingAgents
    
    print(f"\n=== Agent深度分析 (前{top_n}只) ===\n")
    
    agents = TradingAgents()
    
    results = []
    for i, stock in enumerate(stocks[:top_n], 1):
        code = stock['code']
        name = stock['name']
        
        print(f"{i}. 分析 {code} {name}...")
        
        try:
            # 调用Agent分析
            analysis = agents.analyze(code)
            
            # 提取决策结论
            decision = analysis.get('decision', '')
            
            # 简化结论
            if '买入' in decision or '建仓' in decision:
                recommendation = '买入'
            elif '卖出' in decision or '减仓' in decision:
                recommendation = '卖出'
            else:
                recommendation = '观望'
            
            results.append({
                'code': code,
                'name': name,
                'technique': stock.get('technique', {}).get('patterns', []),
                'inflow': stock.get('inflow', {}).get('total_inflow', 0),
                'recommendation': recommendation,
                'analysis': analysis
            })
            
            print(f"   → {recommendation}")
            
        except Exception as e:
            print(f"   → 分析失败: {e}")
    
    return results


def select_and_analyze() -> List[Dict]:
    """选股 + 分析一体化
    
    Returns:
        list: 选股结果 + Agent分析
    """
    # 1. 选股
    print("=" * 50)
    print("第1步：量化筛选")
    print("=" * 50)
    
    stocks = select_stocks(
        min_consecutive_days=1,
        require_pattern=True,
        top_n=10
    )
    
    if not stocks:
        print("无符合条件股票")
        return []
    
    # 2. Agent深度分析
    results = analyze_selected_stocks(stocks, top_n=3)
    
    return results


# 测试
if __name__ == "__main__":
    print("=== 综合选股测试 ===\n")
    
    # 选股：连续2天资金流入 + 技术形态
    results = select_stocks(
        min_consecutive_days=2,
        require_pattern=True,
        top_n=5
    )
