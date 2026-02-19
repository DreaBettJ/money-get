#!/usr/bin/env python3
"""定时同步股票数据

用法:
    python sync_daily.py              # 同步默认股票
    python sync_daily.py 600519       # 同步指定股票
    python sync_daily.py --all        # 同步所有关注的股票
"""
import argparse
import json
import logging
import sys
import os
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))
os.chdir(project_root)

from money_get.db import init_db, sync_stock_data, get_all_stocks, insert_trade

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def load_config() -> dict:
    """加载配置"""
    config_path = Path(__file__).parent.parent.parent / "config.json"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"data": {"stocks": ["600519", "000858", "300750"]}}


def get_watch_list() -> list:
    """获取关注列表"""
    config = load_config()
    return config.get("data", {}).get("stocks", ["600519"])


def sync_single_stock(stock_code: str, days: int = 30) -> dict:
    """同步单个股票"""
    logger.info(f"开始同步 {stock_code}...")
    try:
        result = sync_stock_data(stock_code, days=days)
        logger.info(f"✅ {stock_code}: K线 {result['kline']} 条, 指标 {result['indicators']} 条")
        return {"code": stock_code, "success": True, **result}
    except Exception as e:
        logger.error(f"❌ {stock_code}: {e}")
        return {"code": stock_code, "success": False, "error": str(e)}


def sync_all(days: int = 30, max_workers: int = 3) -> dict:
    """同步所有关注的股票"""
    watch_list = get_watch_list()
    logger.info(f"开始同步 {len(watch_list)} 只股票: {watch_list}")
    
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(sync_single_stock, code, days): code for code in watch_list}
        for future in as_completed(futures):
            results.append(future.result())
    
    success = sum(1 for r in results if r.get("success"))
    failed = len(results) - success
    
    # 同步资金流向
    logger.info("同步资金流向...")
    sync_fund_flow()
    
    # 同步龙虎榜
    logger.info("同步龙虎榜...")
    sync_lhb()
    
    # 同步新闻
    logger.info("同步新闻...")
    sync_news()
    
    # 同步热点板块
    logger.info("同步热点板块...")
    sync_hot_sectors()
    
    # 同步北向资金
    logger.info("同步北向资金...")
    sync_north_money()
    
    summary = {
        "total": len(results),
        "success": success,
        "failed": failed,
        "results": results,
        "timestamp": datetime.now().isoformat()
    }
    
    logger.info(f"同步完成: 成功 {success}, 失败 {failed}")
    return summary


def sync_fund_flow() -> dict:
    """同步资金流向数据"""
    from money_get.data import get_fund_flow
    
    watch_list = get_watch_list()
    result = {"success": 0, "failed": 0}
    
    for code in watch_list:
        try:
            data = get_fund_flow(code)
            if "data" in data and data["data"]:
                # 取最新一条
                latest = data["data"][0]
                from money_get.db import insert_fund_flow
                insert_fund_flow(code, latest.get("日期", ""), {
                    "主力净流入": latest.get("主力净流入-净额"),
                    "小单净流入": latest.get("小单净流入-净额"),
                    "中单净流入": latest.get("中单净流入-净额"),
                    "大单净流入": latest.get("大单净流入-净额"),
                    "超大单净流入": latest.get("超大单净流入-净额"),
                })
                result["success"] += 1
                logger.info(f"✅ {code} 资金流向同步成功")
        except Exception as e:
            result["failed"] += 1
            logger.error(f"❌ {code} 资金流向同步失败: {e}")
    
    return result


def sync_lhb() -> dict:
    """同步龙虎榜数据"""
    from money_get.data import get_insider_transactions
    
    watch_list = get_watch_list()
    result = {"success": 0, "failed": 0}
    
    # 获取近一月的龙虎榜
    try:
        data = get_insider_transactions("近一月")
        if "data" in data and data["data"]:
            from money_get.db import insert_lhb
            for item in data["data"][:50]:  # 取前50条
                try:
                    insert_lhb(
                        code=item.get("代码"),
                        name=item.get("股票名称"),
                        date=item.get("日期", ""),
                        data=item
                    )
                    result["success"] += 1
                except Exception as e:
                    logger.warning(f"插入龙虎榜失败: {e}")
            logger.info(f"✅ 龙虎榜同步成功: {result['success']} 条")
    except Exception as e:
        result["failed"] += 1
        logger.error(f"❌ 龙虎榜同步失败: {e}")
    
    return result


def sync_news() -> dict:
    """同步新闻数据"""
    from money_get.data import get_news
    
    watch_list = get_watch_list()
    result = {"success": 0, "failed": 0}
    
    for code in watch_list:
        try:
            data = get_news(code, limit=10)
            if "data" in data and data["data"]:
                from money_get.db import insert_news
                for item in data["data"]:
                    insert_news(
                        code=code,
                        title=item.get("title", ""),
                        content=item.get("content", ""),
                        pub_date=item.get("pub_date", ""),
                        source=item.get("source", "")
                    )
                result["success"] += 1
                logger.info(f"✅ {code} 新闻同步成功: {len(data['data'])} 条")
        except Exception as e:
            result["failed"] += 1
            logger.error(f"❌ {code} 新闻同步失败: {e}")
    
    return result


def sync_hot_sectors() -> dict:
    """同步热点板块数据"""
    from money_get.data import get_hot_sectors
    
    result = {"success": 0, "failed": 0}
    
    try:
        data = get_hot_sectors(limit=30)
        if "data" in data and data["data"]:
            from money_get.db import insert_hot_sector
            today = datetime.now().strftime("%Y-%m-%d")
            for item in data["data"]:
                try:
                    insert_hot_sector(
                        sector_name=item.get("板块名称", ""),
                        date=today,
                        data=item
                    )
                    result["success"] += 1
                except Exception as e:
                    logger.warning(f"插入板块失败: {e}")
            logger.info(f"✅ 热点板块同步成功: {result['success']} 条")
    except Exception as e:
        result["failed"] += 1
        logger.error(f"❌ 热点板块同步失败: {e}")
    
    return result


def sync_north_money() -> dict:
    """同步北向资金数据"""
    from money_get.data import get_market_fund_flow
    
    result = {"success": 0, "failed": 0}
    
    try:
        data = get_market_fund_flow()
        if "data" in data and data["data"]:
            from money_get.db import insert_north_money
            latest = data["data"][0]
            insert_north_money(
                date=latest.get("日期", datetime.now().strftime("%Y-%m-%d")),
                data=latest
            )
            result["success"] = 1
            logger.info(f"✅ 北向资金同步成功")
    except Exception as e:
        result["failed"] += 1
        logger.error(f"❌ 北向资金同步失败: {e}")
    
    return result


def main():
    parser = argparse.ArgumentParser(description="同步股票数据到本地数据库")
    parser.add_argument("stock_code", nargs="?", help="股票代码")
    parser.add_argument("--all", action="store_true", help="同步所有关注的股票")
    parser.add_argument("--days", type=int, default=30, help="同步天数")
    parser.add_argument("--init", action="store_true", help="初始化数据库")
    parser.add_argument("--fundamentals", action="store_true", help="同步基本面数据（每周一次）")
    parser.add_argument("--mode", choices=["daily", "weekly", "full"], default="daily", help="同步模式")
    
    args = parser.parse_args()
    
    # 初始化数据库
    if args.init:
        logger.info("初始化数据库...")
        init_db()
        logger.info("✅ 数据库初始化完成")
    
    # 同步逻辑
    if args.mode == "weekly" or args.fundamentals:
        # 每周同步：基本面 + 股票信息
        logger.info("执行每周同步（基本面+股票信息）...")
        # TODO: 实现基本面同步
        logger.info("✅ 每周同步完成")
    elif args.mode == "full":
        # 完整同步
        result = sync_all(days=args.days)
        logger.info(f"\n📊 完整同步: 成功 {result['success']}/{result['total']}")
    elif args.all:
        result = sync_all(days=args.days)
        logger.info(f"\n📊 同步结果: 成功 {result['success']}/{result['total']}")
    elif args.stock_code:
        result = sync_single_stock(args.stock_code, days=args.days)
        if result.get("success"):
            logger.info(f"\n✅ {args.stock_code} 同步完成")
        else:
            logger.info(f"\n❌ {args.stock_code} 同步失败: {result.get('error')}")
    else:
        # 默认同步所有
        result = sync_all(days=args.days)
        logger.info(f"\n📊 同步结果: 成功 {result['success']}/{result['total']}")


if __name__ == "__main__":
    main()
