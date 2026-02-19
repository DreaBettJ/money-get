"""增强因子系统 - 包含基本面因子"""
from typing import Dict, List
from money_get.db import get_connection, get_stock, get_kline
from money_get.scraper import get_stock_price, get_fund_flow, get_hot_sectors


class EnhancedFactor:
    """增强因子分析"""
    
    def __init__(self, code: str):
        self.code = code
        self.data = {}
        self.scores = {}
    
    def load_all_data(self):
        """加载所有数据"""
        # 股票基本信息
        self.data['stock'] = get_stock(self.code)
        
        # 实时价格
        self.data['price'] = get_stock_price(self.code)
        
        # 资金流向
        self.data['fund'] = get_fund_flow(self.code, 10)
        
        # K线
        self.data['kline'] = get_kline(self.code, 30)
        
        # 热点板块
        self.data['sectors'] = get_hot_sectors(10)
        
        # 从数据库获取更多数据
        conn = get_connection()
        cursor = conn.cursor()
        
        # 指标数据
        try:
            cursor.execute('SELECT * FROM indicators WHERE code = ?', (self.code,))
            row = cursor.fetchone()
            self.data['indicators'] = dict(row) if row else {}
        except:
            self.data['indicators'] = {}
        
        conn.close()
        
        return self
    
    # ========== 资金因子 (30%) ==========
    def score_fund_flow(self) -> float:
        """资金流向因子"""
        fund = self.data.get('fund', [])
        if not fund:
            return 50
        
        # 取最新主力净流入
        latest = fund[0]
        net_main = latest.get('main_net_inflow', 0) or 0
        
        if net_main > 1000:
            return 100
        elif net_main > 500:
            return 85
        elif net_main > 100:
            return 70
        elif net_main > 0:
            return 55
        elif net_main > -100:
            return 45
        elif net_main > -500:
            return 30
        else:
            return 15
    
    def score_money_flow(self) -> float:
        """资金活跃度"""
        fund = self.data.get('fund', [])
        if not fund or len(fund) < 3:
            return 50
        
        # 连续流入天数
        inflow_days = 0
        for f in fund[:5]:
            net = f.get('main_net_inflow', 0) or 0
            if net > 0:
                inflow_days += 1
            else:
                break
        
        if inflow_days >= 3:
            return 100
        elif inflow_days == 2:
            return 80
        elif inflow_days == 1:
            return 60
        else:
            return 40
    
    # ========== 动量因子 (20%) ==========
    def score_momentum(self) -> float:
        """动量因子"""
        kline = self.data.get('kline', [])
        if not kline or len(kline) < 5:
            return 50
        
        # 近5日涨幅
        recent = kline[:5]
        first = recent[-1].get('close', 0)
        last = recent[0].get('close', 0)
        
        if first > 0:
            pct = (last - first) / first * 100
            
            if pct > 10:
                return 100
            elif pct > 5:
                return 85
            elif pct > 2:
                return 70
            elif pct > 0:
                return 55
            elif pct > -2:
                return 45
            elif pct > -5:
                return 30
            else:
                return 15
        
        return 50
    
    def score_price_strength(self) -> float:
        """价格强度"""
        kline = self.data.get('kline', [])
        if not kline or len(kline) < 5:
            return 50
        
        closes = [k.get('close', 0) for k in kline[:5]]
        
        # 连续上涨
        up_days = 0
        for i in range(len(closes) - 1):
            if closes[i] > closes[i + 1]:
                up_days += 1
            else:
                break
        
        if up_days >= 4:
            return 100
        elif up_days >= 3:
            return 85
        elif up_days >= 2:
            return 70
        elif up_days >= 1:
            return 55
        else:
            return 40
    
    # ========== 成交量因子 (15%) ==========
    def score_volume(self) -> float:
        """成交量因子"""
        kline = self.data.get('kline', [])
        if not kline:
            return 50
        
        # 近期平均成交量
        recent = kline[:5]
        avg_vol = sum(k.get('volume', 0) for k in recent) / len(recent)
        
        if avg_vol > 100000:
            return 100
        elif avg_vol > 50000:
            return 80
        elif avg_vol > 20000:
            return 60
        elif avg_vol > 10000:
            return 45
        else:
            return 30
    
    # ========== 市场情绪因子 (15%) ==========
    def score_market_sentiment(self) -> float:
        """市场情绪"""
        sectors = self.data.get('sectors', [])
        if not sectors:
            return 50
        
        # 热点板块涨幅
        hot_change = sectors[0].get('change', 0) if sectors else 0
        
        if hot_change > 10:
            return 100
        elif hot_change > 5:
            return 85
        elif hot_change > 2:
            return 70
        elif hot_change > 0:
            return 55
        else:
            return 40
    
    # ========== 基本面因子 (20%) ==========
    def score_fundamental(self) -> float:
        """基本面因子（模拟）"""
        # 由于缺少真实基本面数据，这里用价格位置模拟
        kline = self.data.get('kline', [])
        if not kline or len(kline) < 20:
            return 50
        
        # 20日均价位置
        recent_20 = kline[:20]
        current = recent_20[0].get('close', 0)
        avg_20 = sum(k.get('close', 0) for k in recent_20) / len(recent_20)
        
        if avg_20 > 0:
            position = (current - avg_20) / avg_20 * 100
            
            # 在20日均线上方且涨幅不大 = 低估
            if position > 5:
                return 60
            elif position > 0:
                return 80  # 最佳位置
            elif position > -5:
                return 60
            else:
                return 45
        
        return 50
    
    def calculate_all(self) -> Dict:
        """计算所有因子"""
        # 资金因子 (30%)
        self.scores['fund_flow'] = self.score_fund_flow()
        self.scores['money_flow'] = self.score_money_flow()
        
        # 动量因子 (20%)
        self.scores['momentum'] = self.score_momentum()
        self.scores['price_strength'] = self.score_price_strength()
        
        # 成交量 (15%)
        self.scores['volume'] = self.score_volume()
        
        # 市场情绪 (15%)
        self.scores['market_sentiment'] = self.score_market_sentiment()
        
        # 基本面 (20%)
        self.scores['fundamental'] = self.score_fundamental()
        
        # 计算总分
        self.total_score = (
            self.scores['fund_flow'] * 0.15 +
            self.scores['money_flow'] * 0.15 +
            self.scores['momentum'] * 0.10 +
            self.scores['price_strength'] * 0.10 +
            self.scores['volume'] * 0.15 +
            self.scores['market_sentiment'] * 0.15 +
            self.scores['fundamental'] * 0.20
        )
        
        return self.get_result()
    
    def get_signal(self) -> str:
        """交易信号"""
        if self.total_score >= 75:
            return "⭐ 强烈买入"
        elif self.total_score >= 60:
            return "✅ 买入"
        elif self.total_score >= 45:
            return "➡️ 持有"
        elif self.total_score >= 30:
            return "⚠️ 卖出"
        else:
            return "❌ 强烈卖出"
    
    def get_result(self) -> Dict:
        """结果"""
        price = self.data.get('price') or {}
        stock = self.data.get('stock') or {}
        
        return {
            'code': self.code,
            'name': price.get('name') or stock.get('name', ''),
            'price': price.get('price', 0),
            'change': (price.get('pct', 0) or 0) * 100,
            'scores': self.scores,
            'total_score': round(self.total_score, 1),
            'signal': self.get_signal()
        }


def quick_analyze(code: str) -> Dict:
    """快速分析"""
    factor = EnhancedFactor(code)
    factor.load_all_data()
    return factor.calculate_all()


def batch_analyze(codes: List[str]) -> List[Dict]:
    """批量分析"""
    results = []
    for code in codes:
        try:
            result = quick_analyze(code)
            results.append(result)
        except Exception as e:
            print(f"分析 {code} 失败: {e}")
    
    # 按总分排序
    results.sort(key=lambda x: x['total_score'], reverse=True)
    return results


if __name__ == "__main__":
    # 测试
    result = quick_analyze("300719")
    print(f"\n{'='*50}")
    print(f"股票: {result['name']} ({result['code']})")
    print(f"价格: {result['price']} ({result['change']:.2f}%)")
    print(f"{'='*50}")
    print("\n因子得分:")
    for k, v in result['scores'].items():
        bar = "█" * int(v/10)
        print(f"  {k:20s}: {v:5.1f} {bar}")
    print(f"\n总分: {result['total_score']}")
    print(f"信号: {result['signal']}")
