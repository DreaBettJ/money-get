"""配置管理"""
import os
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent

# 数据目录
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

# MiniMax API
MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY", "")
MINIMAX_BASE_URL = "https://api.minimax.chat/v1"

# 推送配置
DINGTALK_WEBHOOK = os.getenv("DINGTALK_WEBHOOK", "")
FEISHU_WEBHOOK = os.getenv("FEISHU_WEBHOOK", "")

# 数据文件路径
TRADES_FILE = DATA_DIR / "trades.json"
MEMORY_DIR = DATA_DIR / "memory"
CACHE_DIR = DATA_DIR / "cache"
