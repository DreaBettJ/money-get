"""日志配置"""
import logging
import os
from pathlib import Path
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)


def get_logger(name: str = "money_get") -> logging.Logger:
    """获取日志器 - 按小时分割"""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # 按小时分割的主日志文件
        main_log = LOG_DIR / f"money_get_{datetime.now().strftime('%Y%m%d_%H')}.log"
        fh = TimedRotatingFileHandler(
            main_log,
            when='h',
            interval=1,
            backupCount=168,  # 保留7天 * 24小时
            encoding='utf-8'
        )
        fh.setLevel(logging.INFO)
        
        # 错误日志文件（按小时）
        error_log = LOG_DIR / f"error_{datetime.now().strftime('%Y%m%d_%H')}.log"
        eh = logging.FileHandler(error_log, encoding='utf-8')
        eh.setLevel(logging.ERROR)
        
        # 控制台
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # 格式：时间 - 模块 - 级别 - 消息
        fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        formatter = logging.Formatter(fmt)
        fh.setFormatter(formatter)
        eh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        logger.addHandler(fh)
        logger.addHandler(eh)
        logger.addHandler(ch)
    
    return logger


def clean_old_logs(days: int = 7):
    """清理旧日志"""
    import time
    now = time.time()
    cutoff = now - (days * 86400)
    
    for f in LOG_DIR.glob("*.log*"):
        if f.is_file():
            if os.path.getmtime(f) < cutoff:
                f.unlink()
                logger.info(f"删除旧日志: {f.name}")


def log_trade(action: str, code: str, price: float, quantity: int, reason: str = ""):
    """交易日志"""
    log_file = LOG_DIR / f"trade_{datetime.now().strftime('%Y%m%d_%H')}.log"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{timestamp} | {action} | {code} | {price} | {quantity} | {reason}\n"
    
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line)


def log_selector(stage: str, count: int, details: str = ""):
    """选股日志"""
    log_file = LOG_DIR / f"selector_{datetime.now().strftime('%Y%m%d_%H')}.log"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{timestamp} | {stage} | {count} | {details}\n"
    
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line)


def log_analysis(code: str, recommendation: str, price: float = 0, target: float = 0, reason: str = ""):
    """分析日志"""
    log_file = LOG_DIR / f"analysis_{datetime.now().strftime('%Y%m%d_%H')}.log"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{timestamp} | {code} | {recommendation} | 现价:{price} 目标:{target} | {reason}\n"
    
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line)


def log_fund(code: str, inflow: float, days: int, reason: str = ""):
    """资金流日志"""
    log_file = LOG_DIR / f"fund_{datetime.now().strftime('%Y%m%d_%H')}.log"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    inflow_str = f"+{inflow:.1f}万" if inflow > 0 else f"{inflow:.1f}万"
    line = f"{timestamp} | {code} | {inflow_str} | {days}天 | {reason}\n"
    
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line)


def log_error(module: str, error: str, detail: str = ""):
    """错误日志"""
    log_file = LOG_DIR / f"error_{datetime.now().strftime('%Y%m%d_%H')}.log"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{timestamp} | {module} | {error} | {detail}\n"
    
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line)


def log_workflow(name: str, status: str, detail: str = ""):
    """工作流日志"""
    log_file = LOG_DIR / f"workflow_{datetime.now().strftime('%Y%m%d_%H')}.log"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{timestamp} | {name} | {status} | {detail}\n"
    
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line)


# 默认日志器
logger = get_logger("money_get")
