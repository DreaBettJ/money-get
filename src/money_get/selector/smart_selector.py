"""智能选股系统 v2 - 自进化选股系统

核心功能：
1. 优质股票选择 - 多因子评分
2. 买入信号判断 - 量化信号
3. 复盘系统 - 定期自反思
4. 可观测性 - 决策链路记录
5. 仓位管理 - 10000元起始资金
6. 数据同步 - 历史+实时
"""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from money_get.core.scraper import get_stock_price, get_fund_flow, get_hot_sectors
from money_get.core.db import get_connection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('money_get.smart_selector')


# ============ 配置文件 ============
CONFIG = {
    # 仓位管理
    'total_capital': 10000,  # 总仓位 10000元
    'max_positions': 5,       # 最大持仓数
    'max_position_pct': 0.25, # 单只最大仓位25%
    
    # 选股参数
    'min_score': 60,          # 最小评分
    'min_change': 3,          # 最小涨幅
    
    # 复盘参数
    'review_interval_hours': 24,  # 复盘间隔
    
    # 数据源
    'data_source': 'realtime',  # realtime实时 / history历史
}


# ============ 选股因子系统 ============
class FactorSystem:
    """多因子选股系统"""
    
    def __init__(self):
        self.weights = {
            'fund_flow': 0.20,      # 资金流向
            'momentum': 0.15,        # 动量
            'volume': 0.10,          # 成交量
            'sentiment': 0.15,       # 市场情绪
            'valuation': 0.20,       # 估值
            'growth': 0.20,          # 成长
        }
    
    def score(self, data: dict) -> dict:
        """计算因子得分"""
        scores = {}
        
        # 1. 资金流向 (20%)
        fund = data.get('fund_flow', [])
        if fund:
            net_main = fund[0].get('main_net_inflow', 0) or 0
            if net_main > 1000:
                scores['fund_flow'] = 100
            elif net_main > 500:
                scores['fund_flow'] = 80
            elif net_main > 0:
                scores['fund_flow'] = 60
            else:
                scores['fund_flow'] = 40
        else:
            scores['fund_flow'] = 50
        
        # 2. 动量 (15%)
        change = data.get('change', 0)
        if change > 10:
            scores['momentum'] = 100
        elif change > 5:
            scores['momentum'] = 80
        elif change > 2:
            scores['momentum'] = 60
        elif change > 0:
            scores['momentum'] = 50
        else:
            scores['momentum'] = 30
        
        # 3. 成交量 (10%)
        volume = data.get('volume', 0)
        if volume > 100000:
            scores['volume'] = 100
        elif volume > 50000:
            scores['volume'] = 80
        elif volume > 20000:
            scores['volume'] = 60
        else:
            scores['volume'] = 40
        
        # 4. 市场情绪 (15%)
        sectors = data.get('sectors', [])
        if sectors:
            hot_change = sectors[0].get('change', 0) if sectors else 0
            if hot_change > 5:
                scores['sentiment'] = 100
            elif hot_change > 2:
                scores['sentiment'] = 80
            else:
                scores['sentiment'] = 60
        else:
            scores['sentiment'] = 50
        
        # 5. 估值 (20%) - 简化版
        price = data.get('price', 0)
        if price < 50:
            scores['valuation'] = 80
        elif price < 100:
            scores['valuation'] = 70
        elif price < 200:
            scores['valuation'] = 60
        else:
            scores['valuation'] = 50
        
        # 6. 成长性 (20%) - 简化版
        scores['growth'] = 60  # 默认为中等
        
        # 计算总分
        total = sum(scores[k] * self.weights[k] for k in self.weights)
        
        return {
            'scores': scores,
            'total': round(total, 1),
            'weights': self.weights
        }


# ============ 买入信号系统 ============
class BuySignal:
    """买入信号判断"""
    
    @staticmethod
    def should_buy(data: dict, factor_score: float) -> tuple:
        """判断是否应该买入
        
        Returns:
            (should_buy: bool, reason: str, confidence: float)
        """
        reasons = []
        confidence = 0
        
        # 1. 因子评分 (40%权重)
        if factor_score >= 75:
            confidence += 30
            reasons.append("因子评分优秀(≥75)")
        elif factor_score >= 60:
            confidence += 20
            reasons.append("因子评分良好(≥60)")
        
        # 2. 资金流向 (30%权重)
        fund = data.get('fund_flow', [])
        if fund:
            net_main = fund[0].get('main_net_inflow', 0) or 0
            if net_main > 500:
                confidence += 25
                reasons.append(f"主力资金净流入({net_main})")
            elif net_main > 0:
                confidence += 15
                reasons.append("主力资金正流入")
        
        # 3. 动量 (20%权重)
        change = data.get('change', 0)
        if 3 <= change <= 10:
            confidence += 15
            reasons.append(f"涨幅适中({change:.1f}%)")
        elif change > 10:
            reasons.append(f"涨幅过大({change:.1f}%), 谨慎")
        
        # 4. 市场情绪 (10%权重)
        sectors = data.get('sectors', [])
        if sectors and sectors[0].get('change', 0) > 3:
            confidence += 10
            reasons.append("市场热点")
        
        # 决策
        should_buy = confidence >= 35
        reason = "; ".join(reasons) if reasons else "条件不足"
        
        return should_buy, reason, confidence
    
    @staticmethod
    def get_signal_level(confidence: float) -> str:
        """信号等级"""
        if confidence >= 70:
            return "⭐ 强烈买入"
        elif confidence >= 50:
            return "✅ 买入"
        elif confidence >= 35:
            return "➡️ 持有"
        else:
            return "⚠️ 观望"


# ============ 仓位管理系统 ============
class PositionManager:
    """仓位管理"""
    
    def __init__(self, capital: float = None):
        self.capital = capital or CONFIG['total_capital']
        self.positions = {}  # {code: {'shares': int, 'price': float, 'date': str}}
        self.history = []    # 交易历史
    
    def calculate_position(self, price: float, confidence: float) -> int:
        """计算仓位
        
        Args:
            price: 股价
            confidence: 信心度
            
        Returns:
            股数
        """
        # 信心度决定仓位
        if confidence >= 70:
            pct = 0.25  # 25%
        elif confidence >= 50:
            pct = 0.20  # 20%
        elif confidence >= 35:
            pct = 0.15  # 15%
        else:
            pct = 0.10  # 10%
        
        amount = self.capital * pct
        shares = int(amount / price / 100) * 100  # 整手
        
        return shares
    
    def buy(self, code: str, price: float, shares: int) -> bool:
        """买入"""
        cost = price * shares
        if cost > self.capital:
            logger.warning(f"资金不足: 需要{cost}, 剩余{self.capital}")
            return False
        
        self.positions[code] = {
            'shares': shares,
            'price': price,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'cost': cost
        }
        self.capital -= cost
        self.history.append({
            'action': 'buy',
            'code': code,
            'price': price,
            'shares': shares,
            'cost': cost,
            'date': datetime.now().strftime('%Y-%m-%d %H:%M')
        })
        logger.info(f"买入 {code}: {shares}股 @{price}, 成本:{cost}")
        return True
    
    def sell(self, code: str, price: float) -> float:
        """卖出"""
        if code not in self.positions:
            return 0
        
        pos = self.positions[code]
        shares = pos['shares']
        revenue = price * shares
        profit = revenue - pos['cost']
        
        self.capital += revenue
        del self.positions[code]
        self.history.append({
            'action': 'sell',
            'code': code,
            'price': price,
            'shares': shares,
            'revenue': revenue,
            'profit': profit,
            'date': datetime.now().strftime('%Y-%m-%d %H:%M')
        })
        logger.info(f"卖出 {code}: {shares}股 @{price}, 盈利:{profit:.2f}")
        return profit
    
    def get_status(self) -> dict:
        """获取状态"""
        total_value = sum(p['shares'] * p['price'] for p in self.positions.values())
        total_cost = sum(p['cost'] for p in self.positions.values())
        
        return {
            'capital': self.capital,
            'positions': self.positions,
            'total_value': total_value,
            'total_cost': total_cost,
            'total_assets': self.capital + total_value,
            'profit': self.capital + total_value - CONFIG['total_capital'],
            'profit_pct': (self.capital + total_value - CONFIG['total_capital']) / CONFIG['total_capital'] * 100
        }


# ============ 决策记录系统 ============
class DecisionLogger:
    """决策链路记录"""
    
    def __init__(self):
        self.decisions = []
        self.file_path = '/home/lijiang/code/money-get/logs/decisions.json'
        self.load()
    
    def load(self):
        """加载历史决策"""
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r') as f:
                    self.decisions = json.load(f)
            except:
                self.decisions = []
    
    def save(self):
        """保存决策"""
        with open(self.file_path, 'w') as f:
            json.dump(self.decisions, f, ensure_ascii=False, indent=2)
    
    def add(self, decision: dict):
        """添加决策"""
        decision['timestamp'] = datetime.now().isoformat()
        self.decisions.append(decision)
        self.save()
    
    def get_recent(self, days: int = 7) -> List[dict]:
        """获取近期决策"""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        return [d for d in self.decisions if d.get('timestamp', '') > cutoff]


# ============ 复盘系统 ============
class ReviewSystem:
    """复盘自进化系统"""
    
    def __init__(self):
        self.decision_logger = DecisionLogger()
        self.reviews = []
        self.file_path = '/home/lijiang/code/money-get/logs/reviews.json'
        self.load()
    
    def load(self):
        """加载复盘记录"""
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r') as f:
                    self.reviews = json.load(f)
            except:
                self.reviews = []
    
    def save(self):
        """保存复盘"""
        with open(self.file_path, 'w') as f:
            json.dump(self.reviews, f, ensure_ascii=False, indent=2)
    
    def review(self):
        """执行复盘"""
        decisions = self.decision_logger.get_recent(7)
        
        if not decisions:
            return None
        
        # 统计
        buy_count = len([d for d in decisions if d.get('action') == 'buy'])
        sell_count = len([d for d in decisions if d.get('action') == 'sell'])
        
        # 分析
        review = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'buy_count': buy_count,
            'sell_count': sell_count,
            'decisions': decisions,
            'insights': self._generate_insights(decisions),
            'improvements': []
        }
        
        self.reviews.append(review)
        self.save()
        
        return review
    
    def _generate_insights(self, decisions: List[dict]) -> List[str]:
        """生成洞察"""
        insights = []
        
        # 买入成功率
        buy_decisions = [d for d in decisions if d.get('action') == 'buy']
        if buy_decisions:
            insights.append(f"近期买入 {len(buy_decisions)} 次")
        
        # 资金使用情况
        capital = CONFIG['total_capital']
        insights.append(f"总资金: {capital}元")
        
        return insights


# ============ 主选股系统 ============
class SmartSelector:
    """智能选股系统"""
    
    def __init__(self):
        self.factor = FactorSystem()
        self.buy_signal = BuySignal()
        self.position_mgr = PositionManager()
        self.decision_logger = DecisionLogger()
        self.review_system = ReviewSystem()
    
    def analyze_stock(self, code: str) -> dict:
        """分析单只股票"""
        # 获取数据
        price_data = get_stock_price(code)
        fund_data = get_fund_flow(code, 5)
        sector_data = get_hot_sectors(5)
        
        # 整理数据
        data = {
            'code': code,
            'name': price_data.get('name', '') if price_data else '',
            'price': price_data.get('price', 0) if price_data else 0,
            'change': (price_data.get('pct', 0) or 0) * 100 if price_data else 0,
            'volume': price_data.get('volume', 0) if price_data else 0,
            'fund_flow': fund_data,
            'sectors': sector_data
        }
        
        # 计算因子
        factor_result = self.factor.score(data)
        
        # 买入信号
        should_buy, reason, confidence = self.buy_signal.should_buy(data, factor_result['total'])
        signal = self.buy_signal.get_signal_level(confidence)
        
        # 决策记录
        decision = {
            'code': code,
            'name': data['name'],
            'price': data['price'],
            'change': data['change'],
            'factor_score': factor_result['total'],
            'confidence': confidence,
            'should_buy': should_buy,
            'reason': reason,
            'signal': signal
        }
        
        return decision
    
    def scan_and_recommend(self, stock_count: int = 100) -> List[dict]:
        """扫描并推荐
        
        Args:
            stock_count: 扫描数量
            
        Returns:
            List: 推荐列表
        """
        from money_get.core.scraper import get_stock_price
        from concurrent.futures import ThreadPoolExecutor
        
        # 生成候选股票列表
        candidates = []
        # 沪市
        candidates.extend([f'60{i:04d}' for i in range(0, 500)])
        # 创业板
        candidates.extend([f'30{i:04d}' for i in range(0, 300)])
        
        candidates = list(set(candidates))[:stock_count]
        
        logger.info(f"开始扫描 {len(candidates)} 只股票...")
        
        # 并发获取价格
        results = []
        def get_price(code):
            try:
                return get_stock_price(code)
            except:
                return None
        
        with ThreadPoolExecutor(20) as ex:
            prices = list(ex.map(get_price, candidates))
        
        # 过滤有效数据
        valid_prices = [p for p in prices if p and p.get('price')]
        
        # 获取资金流和板块
        logger.info(f"有效股票: {len(valid_prices)} 只")
        
        recommendations = []
        for p in valid_prices[:50]:  # 取前50只详细分析
            try:
                code = p.get('code', '')
                fund = get_fund_flow(code, 3)
                sectors = get_hot_sectors(3)
                
                data = {
                    'code': code,
                    'name': p.get('name', ''),
                    'price': p.get('price', 0),
                    'change': (p.get('pct', 0) or 0) * 100,
                    'volume': p.get('volume', 0),
                    'fund_flow': fund,
                    'sectors': sectors
                }
                
                factor_result = self.factor.score(data)
                should_buy, reason, confidence = self.buy_signal.should_buy(data, factor_result['total'])
                signal = self.buy_signal.get_signal_level(confidence)
                
                recommendations.append({
                    'code': code,
                    'name': data['name'],
                    'price': data['price'],
                    'change': data['change'],
                    'factor_score': factor_result['total'],
                    'confidence': confidence,
                    'should_buy': should_buy,
                    'reason': reason,
                    'signal': signal
                })
            except Exception as e:
                logger.warning(f"分析失败: {e}")
        
        # 按信心度排序
        recommendations.sort(key=lambda x: x['confidence'], reverse=True)
        
        return recommendations
    
    def execute_buy(self, code: str) -> bool:
        """执行买入"""
        # 分析
        decision = self.analyze_stock(code)
        
        if not decision['should_buy']:
            logger.info(f"不买入 {code}: {decision['reason']}")
            return False
        
        # 计算仓位
        shares = self.position_mgr.calculate_position(
            decision['price'], 
            decision['confidence']
        )
        
        if shares < 100:
            logger.info(f"仓位不足 {code}")
            return False
        
        # 买入
        success = self.position_mgr.buy(code, decision['price'], shares)
        
        if success:
            # 记录决策
            decision['action'] = 'buy'
            decision['shares'] = shares
            decision['cost'] = decision['price'] * shares
            self.decision_logger.add(decision)
        
        return success
    
    def get_status(self) -> dict:
        """获取系统状态"""
        position_status = self.position_mgr.get_status()
        
        # 决策统计
        recent_decisions = self.decision_logger.get_recent(7)
        
        return {
            'config': CONFIG,
            'position': position_status,
            'recent_decisions': len(recent_decisions),
            'last_review': self.reviews[-1] if self.reviews else None
        }
    
    def run_review(self):
        """执行复盘"""
        return self.review_system.review()


def run_smart_selector():
    """运行智能选股系统"""
    selector = SmartSelector()
    
    # 1. 扫描推荐
    logger.info("="*60)
    logger.info("开始智能选股扫描")
    logger.info("="*60)
    
    recommendations = selector.scan_and_recommend(100)
    
    # 2. 显示推荐
    logger.info(f"\n{'='*70}")
    logger.info("🎯 智能选股推荐")
    logger.info(f"{'='*70}")
    logger.info(f"{'代码':<8} {'名称':<12} {'价格':<8} {'涨幅':<8} {'评分':<6} {'信心度':<8} {'信号'}")
    logger.info("-" * 70)
    
    for r in recommendations[:20]:
        logger.info(f"{r['code']:<8} {r['name']:<12} {r['price']:<8.2f} {r['change']:+.2f}% {r['factor_score']:<6.1f} {r['confidence']:<8} {r['signal']}")
    
    # 3. 推荐买入
    buy_recs = [r for r in recommendations if r['should_buy']][:5]
    logger.info(f"\n✅ 推荐买入 ({len(buy_recs)}只):")
    for r in buy_recs:
        logger.info(f"  {r['code']} {r['name']}: 信心度{r['confidence']}, 原因: {r['reason']}")
    
    # 4. 系统状态
    status = selector.get_status()
    logger.info(f"\n💰 账户状态:")
    logger.info(f"  总资产: {status['position']['total_assets']:.2f}元")
    logger.info(f"  可用资金: {status['position']['capital']:.2f}元")
    logger.info(f"  持仓数: {len(status['position']['positions'])}只")
    logger.info(f"  持仓:")
    for code, pos in status['position']['positions'].items():
        logger.info(f"    {code}: {pos['shares']}股 @ {pos['price']}")
    
    # 5. 决策链路
    logger.info(f"\n📊 决策统计:")
    logger.info(f"  近期决策数: {status['recent_decisions']}")
    
    # 6. 缺失信息
    logger.info(f"\n🔍 系统评估 (需要自进化):")
    logger.info(f"  - 是否有基本面数据: 否 (需要PE/ROE)")
    logger.info(f"  - 是否有龙虎榜数据: 是")
    logger.info(f"  - 是否有北向资金: 否")
    logger.info(f"  - 是否有实时新闻: 是")
    
    return recommendations


if __name__ == "__main__":
    run_smart_selector()
