"""多因子选股系统

核心因子：
1. 资金因子 - 主力资金流入/流出
2. 技术因子 - 涨跌幅、换手率、波动率
3. 基本面因子 - PE、ROE、营收增长
4. 市场情绪 - 龙虎榜、热点板块
"""
from typing import Dict, List, Optional
from money_get.db import get_connection, get_stock, get_kline
from money_get.scraper import get_stock_price, get_fund_flow, get_hot_sectors


class FactorScore:
    """因子评分"""
    
    def __init__(self, code: str):
        self.code = code
        self.data = {}
        self.scores = {}
        self.total_score = 0
    
    def load_data(self):
        """加载数据"""
        # 股票信息
        self.data['stock'] = get_stock(self.code)
        
        # 实时价格
        self.data['price'] = get_stock_price(self.code)
        
        # 资金流向
        self.data['fund'] = get_fund_flow(self.code, 5)
        
        # K线数据
        self.data['kline'] = get_kline(self.code, 30)
        
        # 热点板块
        self.data['sectors'] = get_hot_sectors(5)
        
        return self
    
    def score_momentum(self) -> float:
        """动量因子：近期涨幅"""
        kline = self.data.get('kline', [])
        if not kline or len(kline) < 5:
            return 50  # 中性
        
        # 计算近5日涨幅
        recent = kline[:5]
        if len(recent) >= 2:
            first = recent[-1].get('close', 0)
            last = recent[0].get('close', 0)
            if first > 0:
                pct = (last - first) / first * 100
                
                # 评分：-10% ~ +10% 为好
                if pct > 10:
                    return 100
                elif pct > 5:
                    return 80
                elif pct > 0:
                    return 60
                elif pct > -5:
                    return 40
                else:
                    return 20
        
        return 50
    
    def score_volume(self) -> float:
        """成交量因子：换手率"""
        kline = self.data.get('kline', [])
        if not kline:
            return 50
        
        # 计算平均换手率（简化版：用成交量替代）
        volumes = [k.get('volume', 0) for k in kline[:5]]
        avg_vol = sum(volumes) / len(volumes) if volumes else 0
        
        # 评分：适中最好
        if avg_vol > 100000:  # 10万手以上
            return 90
        elif avg_vol > 50000:
            return 70
        elif avg_vol > 20000:
            return 50
        else:
            return 30
    
    def score_fund_flow(self) -> float:
        """资金因子：主力资金流向"""
        fund = self.data.get('fund', [])
        if not fund:
            return 50
        
        # 取最新一条数据
        latest = fund[0]
        net_main = latest.get('main_net_inflow', 0) or 0
        
        if net_main > 1000:
            return 100
        elif net_main > 500:
            return 80
        elif net_main > 0:
            return 60
        elif net_main > -500:
            return 40
        else:
            return 20
    
    def score_market_sentiment(self) -> float:
        """市场情绪因子"""
        # 检查是否在热点板块
        sectors = self.data.get('sectors', [])
        if not sectors:
            return 50
        
        # 简化：热点板块涨幅
        hot_change = sectors[0].get('change', 0) if sectors else 0
        
        if hot_change > 5:
            return 100
        elif hot_change > 2:
            return 75
        elif hot_change > 0:
            return 50
        else:
            return 25
    
    def score_price_strength(self) -> float:
        """价格强度：近期走势"""
        kline = self.data.get('kline', [])
        if not kline or len(kline) < 5:
            return 50
        
        # 计算收盘价趋势
        closes = [k.get('close', 0) for k in kline[:5]]
        if len(closes) < 2:
            return 50
        
        # 连续上涨天数
        up_days = 0
        for i in range(len(closes) - 1):
            if closes[i] > closes[i + 1]:
                up_days += 1
            else:
                break
        
        if up_days >= 4:
            return 100
        elif up_days >= 3:
            return 80
        elif up_days >= 2:
            return 60
        elif up_days >= 1:
            return 40
        else:
            return 20
    
    def calculate(self) -> Dict:
        """计算所有因子得分"""
        # 1. 动量因子 (20%)
        self.scores['momentum'] = self.score_momentum()
        
        # 2. 成交量因子 (15%)
        self.scores['volume'] = self.score_volume()
        
        # 3. 资金因子 (30%)
        self.scores['fund_flow'] = self.score_fund_flow()
        
        # 4. 市场情绪 (15%)
        self.scores['sentiment'] = self.score_market_sentiment()
        
        # 5. 价格强度 (20%)
        self.scores['price_strength'] = self.score_price_strength()
        
        # 计算总分
        self.total_score = (
            self.scores['momentum'] * 0.20 +
            self.scores['volume'] * 0.15 +
            self.scores['fund_flow'] * 0.30 +
            self.scores['sentiment'] * 0.15 +
            self.scores['price_strength'] * 0.20
        )
        
        return self.get_result()
    
    def get_signal(self) -> str:
        """获取选股信号"""
        if self.total_score >= 75:
            return "强烈买入"
        elif self.total_score >= 60:
            return "买入"
        elif self.total_score >= 45:
            return "持有"
        elif self.total_score >= 30:
            return "卖出"
        else:
            return "强烈卖出"
    
    def get_result(self) -> Dict:
        """获取完整结果"""
        stock = self.data.get('stock', {})
        price = self.data.get('price', {})
        
        return {
            'code': self.code,
            'name': stock.get('name', price.get('name', '')),
            'price': price.get('price', 0),
            'scores': self.scores,
            'total_score': round(self.total_score, 1),
            'signal': self.get_signal(),
            'data': {
                'momentum': self.scores.get('momentum', 0),
                'volume': self.scores.get('volume', 0),
                'fund_flow': self.scores.get('fund_flow', 0),
                'sentiment': self.scores.get('sentiment', 0),
                'price_strength': self.scores.get('price_strength', 0),
            }
        }


def analyze_stock(code: str) -> Dict:
    """分析单只股票"""
    factor = FactorScore(code)
    factor.load_data()
    return factor.calculate()


def rank_stocks(codes: List[str]) -> List[Dict]:
    """批量分析并排序"""
    results = []
    for code in codes:
        try:
            result = analyze_stock(code)
            results.append(result)
        except Exception as e:
            print(f"分析 {code} 失败: {e}")
    
    # 按总分排序
    results.sort(key=lambda x: x['total_score'], reverse=True)
    
    return results


if __name__ == "__main__":
    # 测试
    result = analyze_stock("300719")
    print("=== 多因子分析结果 ===")
    print(f"股票: {result['name']} ({result['code']})")
    print(f"现价: {result['price']}")
    print(f"\n因子得分:")
    for factor, score in result['scores'].items():
        print(f"  {factor}: {score}")
    print(f"\n总分: {result['total_score']}")
    print(f"信号: {result['signal']}")
