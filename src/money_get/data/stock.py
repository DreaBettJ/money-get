"""股票数据获取 - A股数据层

基于 akshare 实现，参考 TradingAgents 数据层设计
支持本地缓存优先策略
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import pandas as pd
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False


def retry_on_error(max_retries: int = 3, delay: float = 1.0):
    """重试装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"{func.__name__} attempt {attempt+1} failed: {e}, retrying...")
                        time.sleep(delay)
                    else:
                        logger.error(f"{func.__name__} failed after {max_retries} attempts")
                        raise
        return wrapper
    return decorator


def get_from_local_cache(stock_code: str, days: int = 30) -> Optional[Dict]:
    """从本地数据库获取数据"""
    try:
        from money_get.db import get_kline, get_indicators
        
        klines = get_kline(stock_code, limit=days)
        if klines:
            # 转换格式
            data = [{
                "日期": k["date"],
                "开盘": k["open"],
                "收盘": k["close"],
                "最高": k["high"],
                "最低": k["low"],
                "成交量": k["volume"],
                "成交额": k["amount"],
            } for k in klines]
            
            return {
                "code": stock_code,
                "data": data,
                "count": len(data),
                "source": "local"
            }
    except Exception as e:
        logger.warning(f"Local cache read failed: {e}")
    return None


# ==================== 基础行情数据 ====================

def get_stock_data(stock_code: str, start_date: str = None, end_date: str = None, days: int = 30, use_local: bool = True) -> Dict[str, Any]:
    """获取股票K线数据 (OHLCV)
    
    Args:
        stock_code: 股票代码，如 "600519"
        start_date: 开始日期 "YYYYMMDD"
        end_date: 结束日期 "YYYYMMDD"
        days: 默认取最近N天
        use_local: 是否优先使用本地缓存
    
    Returns:
        dict: 包含股票数据的字典
    """
    # 优先从本地获取
    if use_local:
        local_data = get_from_local_cache(stock_code, days)
        if local_data:
            logger.info(f"Using local cache for {stock_code}")
            return local_data
    
    if not AKSHARE_AVAILABLE:
        return {"error": "akshare not installed"}
    
    try:
        # 默认取最近 N 天
        if not start_date:
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=days+30)).strftime("%Y%m%d")
        
        # 使用 stock_zh_a_hist（更稳定）
        df = ak.stock_zh_a_hist(
            symbol=stock_code,
            start_date=start_date,
            end_date=end_date,
            adjust="qfq",
            period="daily"
        )
        
        if df is None or df.empty:
            return {"error": f"股票 {stock_code} 无数据"}
        
        # 转换为字典
        data = df.to_dict(orient="records")
        return {
            "code": stock_code,
            "data": data,
            "count": len(data),
            "start_date": start_date,
            "end_date": end_date
        }
    except Exception as e:
        return {"error": str(e)}


def get_realtime_quote(stock_code: str) -> Dict[str, Any]:
    """获取股票实时行情"""
    if not AKSHARE_AVAILABLE:
        return {"error": "akshare not installed"}
    
    try:
        df = ak.stock_zh_a_spot_em()
        stock = df[df["代码"] == stock_code]
        
        if stock.empty:
            return {"error": f"股票 {stock_code} 未找到"}
        
        data = stock.iloc[0]
        return {
            "code": stock_code,
            "name": data.get("名称"),
            "price": data.get("最新价"),
            "change": data.get("涨跌幅"),
            "volume": data.get("成交量"),
            "amount": data.get("成交额"),
            "amplitude": data.get("振幅"),
            "high": data.get("最高"),
            "low": data.get("最低"),
            "open": data.get("今开"),
            "prev_close": data.get("昨收"),
        }
    except Exception as e:
        return {"error": str(e)}


# ==================== 技术指标 ====================

def get_indicators(stock_code: str, indicator_type: str = "all", days: int = 60) -> Dict[str, Any]:
    """获取技术指标
    
    Args:
        stock_code: 股票代码
        indicator_type: 指标类型 ("all", "ma", "macd", "rsi", "kdj", "boll")
        days: 取最近N天
    
    Returns:
        dict: 技术指标数据
    """
    if not AKSHARE_AVAILABLE:
        return {"error": "akshare not installed"}
    
    try:
        # 先获取基础K线数据 - 使用 stock_zh_a_hist
        df = ak.stock_zh_a_hist(
            symbol=stock_code,
            start_date=(datetime.now() - timedelta(days=days+50)).strftime("%Y%m%d"),
            end_date=datetime.now().strftime("%Y%m%d"),
            adjust="qfq",
            period="daily"
        )
        
        if df is None or df.empty:
            return {"error": f"股票 {stock_code} 无数据"}
        
        result = {"code": stock_code, "indicators": {}}
        
        # 计算均线 (MA)
        if indicator_type in ("all", "ma"):
            df["ma5"] = df["收盘"].rolling(window=5).mean()
            df["ma10"] = df["收盘"].rolling(window=10).mean()
            df["ma20"] = df["收盘"].rolling(window=20).mean()
            df["ma60"] = df["收盘"].rolling(window=60).mean()
            result["indicators"]["ma"] = {
                "ma5": df["ma5"].iloc[-1] if len(df) >= 5 else None,
                "ma10": df["ma10"].iloc[-1] if len(df) >= 10 else None,
                "ma20": df["ma20"].iloc[-1] if len(df) >= 20 else None,
                "ma60": df["ma60"].iloc[-1] if len(df) >= 60 else None,
            }
        
        # 计算 MACD
        if indicator_type in ("all", "macd"):
            ema12 = df["收盘"].ewm(span=12, adjust=False).mean()
            ema26 = df["收盘"].ewm(span=26, adjust=False).mean()
            df["dif"] = ema12 - ema26
            df["dea"] = df["dif"].ewm(span=9, adjust=False).mean()
            df["macd"] = 2 * (df["dif"] - df["dea"])
            result["indicators"]["macd"] = {
                "dif": df["dif"].iloc[-1],
                "dea": df["dea"].iloc[-1],
                "macd": df["macd"].iloc[-1],
            }
        
        # 计算 RSI
        if indicator_type in ("all", "rsi"):
            delta = df["收盘"].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df["rsi"] = 100 - (100 / (1 + rs))
            result["indicators"]["rsi"] = {
                "rsi6": df["rsi"].iloc[-6] if len(df) >= 6 else None,
                "rsi12": df["rsi"].iloc[-12] if len(df) >= 12 else None,
                "rsi24": df["rsi"].iloc[-24] if len(df) >= 24 else None,
            }
        
        # 计算 KDJ
        if indicator_type in ("all", "kdj"):
            low14 = df["最低"].rolling(window=14).min()
            high14 = df["最高"].rolling(window=14).max()
            rsv = (df["收盘"] - low14) / (high14 - low14) * 100
            df["k"] = rsv.ewm(com=2, adjust=False).mean()
            df["d"] = df["k"].ewm(com=2, adjust=False).mean()
            df["j"] = 3 * df["k"] - 2 * df["d"]
            result["indicators"]["kdj"] = {
                "k": df["k"].iloc[-1],
                "d": df["d"].iloc[-1],
                "j": df["j"].iloc[-1],
            }
        
        # 计算布林带
        if indicator_type in ("all", "boll"):
            df["boll_mid"] = df["收盘"].rolling(window=20).mean()
            std = df["收盘"].rolling(window=20).std()
            df["boll_up"] = df["boll_mid"] + 2 * std
            df["boll_low"] = df["boll_mid"] - 2 * std
            result["indicators"]["boll"] = {
                "upper": df["boll_up"].iloc[-1],
                "middle": df["boll_mid"].iloc[-1],
                "lower": df["boll_low"].iloc[-1],
            }
        
        return result
        
    except Exception as e:
        return {"error": str(e)}


# ==================== 基本面数据 ====================

def get_fundamentals(stock_code: str) -> Dict[str, Any]:
    """获取基本面数据 (财务摘要)"""
    if not AKSHARE_AVAILABLE:
        return {"error": "akshare not installed"}
    
    try:
        df = ak.stock_financial_abstract_ths(symbol=stock_code)
        
        if df.empty:
            return {"error": f"股票 {stock_code} 无财务数据"}
        
        # 提取关键指标
        data = df.to_dict(orient="records")
        return {
            "code": stock_code,
            "data": data[:10],  # 最近10个季度
        }
    except Exception as e:
        return {"error": str(e)}


def get_stock_info(stock_code: str) -> Dict[str, Any]:
    """获取股票基本信息"""
    if not AKSHARE_AVAILABLE:
        return {"error": "akshare not installed"}
    
    try:
        df = ak.stock_individual_info_em(symbol=stock_code)
        info = {row["item"]: row["value"] for row in df.to_dict(orient="records")}
        return {
            "code": stock_code,
            "info": info,
        }
    except Exception as e:
        return {"error": str(e)}


# ==================== 新闻舆情 ====================

def get_news(stock_code: str = None, limit: int = 10) -> Dict[str, Any]:
    """获取股票新闻
    
    Args:
        stock_code: 股票代码 (可选)
        limit: 返回数量
    """
    if not AKSHARE_AVAILABLE:
        return {"error": "akshare not installed"}
    
    try:
        if stock_code:
            df = ak.stock_news_em(symbol=stock_code)
        else:
            # 获取全部新闻
            df = ak.stock_news_em(symbol="600519")  # 默认取茅台
        
        if df is None or df.empty:
            return {"error": "无新闻数据", "data": []}
        
        # 重命名字段（akshare 返回的字段名不同）
        rename_map = {
            "新闻标题": "title",
            "新闻内容": "content", 
            "发布时间": "pub_date",
            "文章来源": "source"
        }
        df = df.rename(columns=rename_map)
        
        # 只取需要的列
        df = df.head(limit)
        return {
            "data": df.to_dict(orient="records"),
            "count": len(df)
        }
    except Exception as e:
        return {"error": str(e)}


# ==================== 龙虎榜/内部交易 ====================

def get_insider_transactions(stock_code: str = "近一月") -> Dict[str, Any]:
    """获取龙虎榜数据
    
    Args:
        stock_code: "近一月" 或股票代码
    """
    if not AKSHARE_AVAILABLE:
        return {"error": "akshare not installed"}
    
    try:
        df = ak.stock_lhb_stock_statistic_em(symbol=stock_code)
        
        if df.empty:
            return {"error": "无龙虎榜数据", "data": []}
        
        return {
            "data": df.to_dict(orient="records"),
            "count": len(df)
        }
    except Exception as e:
        return {"error": str(e)}


def get_lhb_detail(stock_code: str, date: str = None) -> Dict[str, Any]:
    """获取个股龙虎榜详情
    
    Args:
        stock_code: 股票代码
        date: 日期 (可选)
    """
    if not AKSHARE_AVAILABLE:
        return {"error": "akshare not installed"}
    
    try:
        df = ak.stock_lhb_detail_em(symbol=stock_code)
        
        if df.empty:
            return {"error": "无龙虎榜详情", "data": []}
        
        return {
            "code": stock_code,
            "data": df.to_dict(orient="records"),
            "count": len(df)
        }
    except Exception as e:
        return {"error": str(e)}


# ==================== 资金流向 ====================

def get_fund_flow(stock_code: str) -> Dict[str, Any]:
    """获取个股资金流向"""
    if not AKSHARE_AVAILABLE:
        return {"error": "akshare not installed"}
    
    try:
        # 判断市场
        market = "sh" if stock_code.startswith("6") else "sz"
        
        df = ak.stock_individual_fund_flow(stock=stock_code, market=market)
        
        if df.empty:
            return {"error": "无资金流向数据", "data": []}
        
        return {
            "code": stock_code,
            "data": df.to_dict(orient="records"),
            "count": len(df)
        }
    except Exception as e:
        return {"error": str(e)}


def get_market_fund_flow() -> Dict[str, Any]:
    """获取市场资金流向 (北向资金)"""
    if not AKSHARE_AVAILABLE:
        return {"error": "akshare not installed"}
    
    try:
        df = ak.fund_flow_hsgt()
        
        if df.empty:
            return {"error": "无资金流向数据", "data": []}
        
        return {
            "data": df.head(20).to_dict(orient="records"),
            "count": len(df)
        }
    except Exception as e:
        return {"error": str(e)}


# ==================== 板块数据 ====================

def get_hot_sectors(limit: int = 20) -> Dict[str, Any]:
    """获取热点板块"""
    if not AKSHARE_AVAILABLE:
        return {"error": "akshare not installed"}
    
    try:
        df = ak.stock_board_industry_name_em()
        
        if df.empty:
            return {"error": "无板块数据", "data": []}
        
        return {
            "data": df.head(limit).to_dict(orient="records"),
            "count": len(df)
        }
    except Exception as e:
        return {"error": str(e)}


def get_sector_stocks(sector_name: str) -> Dict[str, Any]:
    """获取板块成分股"""
    if not AKSHARE_AVAILABLE:
        return {"error": "akshare not installed"}
    
    try:
        df = ak.board_industry_cons_em(symbol=sector_name)
        
        if df.empty:
            return {"error": f"板块 {sector_name} 无数据", "data": []}
        
        return {
            "sector": sector_name,
            "data": df.to_dict(orient="records"),
            "count": len(df)
        }
    except Exception as e:
        return {"error": str(e)}


# ==================== 工具函数 ====================

def format_stock_data(stock_code: str) -> str:
    """格式化股票数据为可读字符串"""
    # 获取实时行情
    quote = get_realtime_quote(stock_code)
    if "error" in quote:
        return f"获取失败: {quote['error']}"
    
    # 获取技术指标
    indicators = get_indicators(stock_code)
    
    # 获取资金流向
    fund_flow = get_fund_flow(stock_code)
    
    report = f"""## {quote.get('name')} ({stock_code}) 行情

### 实时行情
- 最新价: {quote.get('price')}
- 涨跌幅: {quote.get('change')}%
- 涨跌额: {quote.get('price', 0) - quote.get('prev_close', 0):.2f}
- 成交额: {quote.get('amount', 0):,.0f}万

### 技术指标
"""
    if "indicators" in indicators:
        ind = indicators["indicators"]
        if "ma" in ind:
            ma = ind["ma"]
            report += f"- MA5: {ma.get('ma5'):.2f}\n"
            report += f"- MA10: {ma.get('ma10'):.2f}\n"
            report += f"- MA20: {ma.get('ma20'):.2f}\n"
        if "macd" in ind:
            macd = ind["macd"]
            report += f"- MACD: {macd.get('macd'):.2f}\n"
        if "rsi" in ind:
            rsi = ind["rsi"]
            report += f"- RSI: {rsi.get('rsi24'):.2f}\n"
    
    return report
