"""缓存层 - 避免重复调用LLM"""
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

CACHE_DIR = Path(__file__).parent.parent / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def get_cache_key(data: dict, prompt: str) -> str:
    """生成缓存Key: MD5(数据+提示词)"""
    content = json.dumps(data, sort_keys=True) + prompt
    return hashlib.md5(content.encode()).hexdigest()


def get_cached_result(key: str, max_age_days: int = 7) -> Optional[str]:
    """获取缓存结果"""
    cache_file = CACHE_DIR / f"{key}.json"
    if not cache_file.exists():
        return None
    
    try:
        with open(cache_file) as f:
            cached = json.load(f)
        
        # 检查过期
        cache_time = datetime.fromisoformat(cached['time'])
        if datetime.now() - cache_time > timedelta(days=max_age_days):
            return None
        
        return cached['result']
    except Exception:
        return None


def save_cache(key: str, result: str):
    """保存缓存 - 暂时禁用"""
    pass
    # cache_file = CACHE_DIR / f"{key}.json"
    # with open(cache_file, 'w') as f:
    #     json.dump({
    #         'result': result,
    #         'time': datetime.now().isoformat()
    #     }, f, ensure_ascii=False)


def clear_cache(pattern: str = "*"):
    """清理缓存"""
    import glob
    for f in CACHE_DIR.glob(pattern):
        f.unlink()


# 缓存配置
CACHE_CONFIG = {
    'fund_agent': 7,      # 财报数据，7天
    'news_agent': 0.5,    # 新闻，12小时
    'sentiment_agent': 1,  # 情绪，1天
}
