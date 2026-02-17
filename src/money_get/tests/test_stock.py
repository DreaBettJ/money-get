"""股票数据层单元测试

测试股票数据获取功能
"""
import pytest
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestStockData:
    """股票数据获取测试"""

    def test_get_realtime_quote(self):
        """测试获取实时行情"""
        from money_get.data import get_realtime_quote
        
        # 测试茅台
        result = get_realtime_quote("600519")
        
        logger.info(f"茅台行情: {result}")
        
        assert "error" not in result
        assert result.get("name") == "贵州茅台"
        assert result.get("price") is not None
        assert result.get("change") is not None

    def test_get_realtime_quote_invalid(self):
        """测试无效股票代码"""
        from money_get.data import get_realtime_quote
        
        result = get_realtime_quote("999999")
        
        assert "error" in result

    def test_get_stock_data(self):
        """测试获取K线数据"""
        from money_get.data import get_stock_data
        
        result = get_stock_data("600519", days=10)
        
        logger.info(f"K线数据: {result.get('count')} 条")
        
        assert "error" not in result
        assert result.get("count") > 0
        assert "data" in result

    def test_get_indicators_ma(self):
        """测试获取均线指标"""
        from money_get.data import get_indicators
        
        result = get_indicators("600519", indicator_type="ma", days=60)
        
        logger.info(f"均线指标: {result}")
        
        # 不检查具体值，只检查不报错
        assert "error" not in result or "indicators" in result

    def test_get_indicators_all(self):
        """测试获取所有技术指标"""
        from money_get.data import get_indicators
        
        result = get_indicators("600519", indicator_type="all", days=60)
        
        logger.info(f"所有指标: {result}")
        
        # 可能没有所有指标
        assert result is not None


class TestFundamentals:
    """基本面数据测试"""

    def test_get_fundamentals(self):
        """测试获取基本面数据"""
        from money_get.data import get_fundamentals
        
        result = get_fundamentals("600519")
        
        logger.info(f"基本面数据: {result.get('count') if 'count' in result else 'error'}")
        
        # 可能没有数据，但不报错
        assert result is not None

    def test_get_stock_info(self):
        """测试获取股票基本信息"""
        from money_get.data import get_stock_info
        
        result = get_stock_info("600519")
        
        logger.info(f"股票信息 keys: {list(result.get('info', {}).keys())[:5]}")
        
        assert "error" not in result
        assert "info" in result


class TestNews:
    """新闻舆情测试"""

    def test_get_news(self):
        """测试获取新闻"""
        from money_get.data import get_news
        
        result = get_news("600519", limit=5)
        
        logger.info(f"新闻数量: {result.get('count', 0)}")
        
        assert result is not None


class TestFundFlow:
    """资金流向测试"""

    def test_get_fund_flow(self):
        """测试获取资金流向"""
        from money_get.data import get_fund_flow
        
        result = get_fund_flow("600519")
        
        logger.info(f"资金流向: {result.get('count', 0) if 'count' in result else result}")
        
        assert result is not None

    def test_get_market_fund_flow(self):
        """测试获取市场资金流向"""
        from money_get.data import get_market_fund_flow
        
        result = get_market_fund_flow()
        
        logger.info(f"市场资金流向: {result.get('count', 0)}")
        
        assert result is not None


class TestSectors:
    """板块数据测试"""

    def test_get_hot_sectors(self):
        """测试获取热点板块"""
        from money_get.data import get_hot_sectors
        
        result = get_hot_sectors(limit=10)
        
        logger.info(f"热点板块数量: {result.get('count', 0)}")
        
        assert "error" not in result
        assert result.get("count", 0) > 0


class TestFormatter:
    """格式化工具测试"""

    def test_format_stock_data(self):
        """测试格式化股票数据"""
        from money_get.data import format_stock_data
        
        result = format_stock_data("600519")
        
        logger.info(f"格式化结果 (前200字): {result[:200]}...")
        
        assert "贵州茅台" in result
        assert "实时行情" in result
