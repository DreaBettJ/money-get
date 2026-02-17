"""CLI 入口"""
import click

from money_get.agent.graph import build_graph
from money_get.data.trade import Trade, save_trade, get_trades
from money_get.services.analyzer import analyze_stock, review_trades
from money_get.services.reporter import generate_report


@click.group()
def cli():
    """money-get: A股投资辅助 Agent"""
    pass


@cli.command()
@click.argument("stock_code")
@click.option("--days", default=30, help="分析天数")
def analyze(stock_code: str, days: int):
    """分析指定股票"""
    click.echo(f"分析股票: {stock_code}, 近 {days} 天")
    result = analyze_stock(stock_code, days)
    click.echo(result)


@cli.command()
def review():
    """复盘历史操作"""
    click.echo("执行历史操作复盘...")
    trades = get_trades()
    result = review_trades(trades)
    click.echo(result)


@cli.command()
def market():
    """市场热点分析"""
    click.echo("执行市场热点分析...")
    from money_get.data.stock import fetch_sector_flow

    result = fetch_sector_flow()
    click.echo(result)


@cli.group()
def trades():
    """交易记录管理"""
    pass


@trades.command(name="add")
@click.option("--code", required=True, help="股票代码")
@click.option("--name", required=True, help="股票名称")
@click.option("--direction", type=click.Choice(["buy", "sell"]), required=True, help="买卖方向")
@click.option("--price", required=True, type=float, help="价格")
@click.option("--quantity", required=True, type=int, help="数量")
@click.option("--date", required=True, help="日期 YYYY-MM-DD")
@click.option("--reason", default="", help="买入理由")
@click.option("--notes", default="", help="备注")
def trade_add(code, name, direction, price, quantity, date, reason, notes):
    """记录交易"""
    trade = Trade(
        stock_code=code,
        stock_name=name,
        direction=direction,
        price=price,
        quantity=quantity,
        date=date,
        reason=reason,
        notes=notes,
    )
    save_trade(trade)
    click.echo(f"已记录: {direction} {code} {name} @ {price} x {quantity}")


@trades.command(name="list")
@click.option("--code", help="股票代码过滤")
def trade_list(code):
    """查看交易记录"""
    trades = get_trades(code)
    if not trades:
        click.echo("暂无交易记录")
        return

    for t in trades:
        click.echo(
            f"{t['date']} | {t['direction']} | {t['stock_code']} {t['stock_name']} | "
            f"@{t['price']} x {t['quantity']}"
        )


@cli.command()
@click.argument("prompt")
def chat(prompt: str):
    """与 Agent 对话"""
    click.echo(f"用户: {prompt}")
    graph = build_graph()
    result = graph.invoke({"task": prompt})
    click.echo(f"Agent: {result.get('result', '处理完成')}")


if __name__ == "__main__":
    cli()
