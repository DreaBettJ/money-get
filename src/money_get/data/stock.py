"""股票数据获取"""
from typing import Optional

try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False


def fetch_price(stock_code: str) -> dict:
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
        }
    except Exception as e:
        return {"error": str(e)}


def fetch_kline(stock_code: str, days: int = 30) -> dict:
    """获取股票K线数据"""
    if not AKSHARE_AVAILABLE:
        return {"error": "akshare not installed"}

    try:
        df = ak.stock_zh_a_hist(
            symbol=stock_code,
            period="daily",
            start_date="20240101",
            adjust="qfq",
        )
        df = df.tail(days)
        return {
            "code": stock_code,
            "data": df.to_dict(orient="records"),
        }
    except Exception as e:
        return {"error": str(e)}


def fetch_info(stock_code: str) -> dict:
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


def fetch_sector_flow() -> dict:
    """获取板块资金流向"""
    if not AKSHARE_AVAILABLE:
        return {"error": "akshare not installed"}

    try:
        df = ak.fund_flow_hsgt()
        return {
            "data": df.head(20).to_dict(orient="records"),
        }
    except Exception as e:
        return {"error": str(e)}


def fetch_hot_sectors() -> dict:
    """获取热点板块"""
    if not AKSHARE_AVAILABLE:
        return {"error": "akshare not installed"}

    try:
        df = ak.board_industry_name_em()
        return {
            "data": df.head(20).to_dict(orient="records"),
        }
    except Exception as e:
        return {"error": str(e)}
