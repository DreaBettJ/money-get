"""上下文隔离系统

核心设计：
1. ContextScope - 上下文作用域，确保某段时间内只处理一只股票
2. 记忆隔离 - 只有当前股票的上下文会被加载
3. 全局记忆 - 投资原则、交易规律全局共享
"""
from contextlib import contextmanager
from typing import Optional
from money_get.db import get_connection
import threading

# 线程局部存储，确保线程安全
_local = threading.local()


class ContextScope:
    """上下文作用域管理器
    
    用法:
        with ContextScope("600519"):
            # 这里只能看到600519的上下文
            context = get_isolated_context()
    """
    
    def __init__(self, stock_code: str):
        self.stock_code = stock_code
        self._previous = None
    
    def __enter__(self):
        # 保存之前的上下文
        self._previous = getattr(_local, 'current_stock', None)
        _local.current_stock = self.stock_code
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # 恢复之前的上下文
        if self._previous is None:
            delattr(_local, 'current_stock')
        else:
            _local.current_stock = self._previous
        return False
    
    @staticmethod
    def get_current() -> Optional[str]:
        """获取当前上下文股票代码"""
        return getattr(_local, 'current_stock', None)


def get_current_stock() -> Optional[str]:
    """获取当前分析的股票"""
    return ContextScope.get_current()


# ============== 记忆读取 ==============

def get_isolated_context(stock_code: str = None) -> dict:
    """获取隔离的上下文
    
    Args:
        stock_code: 股票代码，如果为None则使用当前上下文
    
    Returns:
        dict: 包含全局记忆和股票特定记忆
    """
    # 确定股票代码
    code = stock_code or get_current_stock()
    if not code:
        return {
            "principles": [],
            "patterns": [],
            "cases": [],
            "stock_history": [],
            "recent_decisions": []
        }
    
    conn = get_connection()
    cursor = conn.cursor()
    
    result = {
        "principles": [],
        "patterns": [],
        "cases": [],
        "stock_history": [],
        "recent_decisions": []
    }
    
    # 1. 全局记忆（共享）
    for category in ["principles", "patterns", "cases"]:
        cursor.execute("""
            SELECT content FROM shared_memory 
            WHERE category = ?
            ORDER BY created_at DESC
            LIMIT 10
        """, (category,))
        result[category] = [r[0] for r in cursor.fetchall()]
    
    # 2. 股票特定记忆（隔离）
    cursor.execute("""
        SELECT context_type, content, created_at FROM stock_context
        WHERE stock_code = ?
        ORDER BY created_at DESC
        LIMIT 20
    """, (code,))
    
    for row in cursor.fetchall():
        ctx_type, content, created_at = row
        if ctx_type == "summary":
            result["stock_history"].append({
                "type": "summary",
                "content": content,
                "date": created_at
            })
        elif ctx_type == "decision":
            result["recent_decisions"].append({
                "type": "decision", 
                "content": content,
                "date": created_at
            })
    
    conn.close()
    return result


def format_context_for_agent(context: dict, stock_code: str) -> str:
    """为Agent格式化上下文"""
    parts = []
    
    # 标题
    parts.append(f"# {stock_code} 分析上下文")
    parts.append("")
    
    # 1. 投资原则（全局）
    principles = context.get("principles", [])
    if principles:
        parts.append("## 📜 投资原则")
        for i, p in enumerate(principles[:5], 1):
            parts.append(f"{i}. {p}")
        parts.append("")
    
    # 2. 交易规律（全局）
    patterns = context.get("patterns", [])
    if patterns:
        parts.append("## 📊 历史规律")
        for i, p in enumerate(patterns[:5], 1):
            parts.append(f"{i}. {p}")
        parts.append("")
    
    # 3. 该股票的分析历史（隔离）
    history = context.get("stock_history", [])
    if history:
        parts.append(f"## 📈 {stock_code} 历史分析")
        for h in history[:3]:  # 只取最近3条
            # 去除思考标签
            content = h["content"]
            if content.startswith("<think>"):
                content = content.split("</think>")[0][:200] + "..."
            parts.append(f"- {h['date']}: {content[:100]}...")
        parts.append("")
    
    # 4. 近期决策（隔离）
    decisions = context.get("recent_decisions", [])
    if decisions:
        parts.append(f"## ⚖️ {stock_code} 近期决策")
        for d in decisions[:3]:
            content = d["content"]
            if content.startswith("<think>"):
                content = content.split("</think>")[0][:100] + "..."
            parts.append(f"- {d['date']}: {content[:80]}...")
        parts.append("")
    
    return "\n".join(parts)


def get_stock_history(stock_code: str, limit: int = 10) -> str:
    """获取股票分析历史（隔离版本）"""
    context = get_isolated_context(stock_code)
    history = context.get("stock_history", [])
    
    if not history:
        return f"暂无 {stock_code} 的分析历史"
    
    lines = [f"## {stock_code} 历史分析"]
    for h in history[:limit]:
        content = h["content"]
        if content.startswith("<think>"):
            content = content.split("</think>")[0][:150]
        lines.append(f"\n### {h['date']}")
        lines.append(content)
    
    return "\n".join(lines)


# ============== 记忆写入 ==============

def add_stock_summary(stock_code: str, content: str) -> int:
    """添加股票分析总结"""
    return _add_stock_context(stock_code, "summary", content)


def add_stock_decision(stock_code: str, content: str) -> int:
    """添加股票决策"""
    return _add_stock_context(stock_code, "decision", content)


def _add_stock_context(stock_code: str, context_type: str, content: str) -> int:
    """内部方法：添加股票上下文"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO stock_context (stock_code, context_type, content)
        VALUES (?, ?, ?)
    """, (stock_code, context_type, content))
    conn.commit()
    _id = cursor.lastrowid
    conn.close()
    return _id


def add_principle(content: str) -> int:
    """添加投资原则（全局）"""
    return _add_shared_memory("principles", content)


def add_pattern(content: str) -> int:
    """添加交易规律（全局）"""
    return _add_shared_memory("patterns", content)


def _add_shared_memory(category: str, content: str) -> int:
    """内部方法：添加共享记忆"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO shared_memory (category, content, source)
        VALUES (?, ?, 'user')
    """, (category, content))
    conn.commit()
    _id = cursor.lastrowid
    conn.close()
    return _id


# ============== 便捷函数 ==============

@contextmanager
def isolated_analysis(stock_code: str):
    """上下文隔离的分析上下文管理器
    
    用法:
        with isolated_analysis("600519"):
            # 分析600519，只能看到600519的上下文
            context = get_isolated_context()
            result = llm.analyze(context + prompt)
            add_stock_summary("600519", result)
    """
    with ContextScope(stock_code):
        yield


def get_principles() -> list:
    """获取投资原则"""
    context = get_isolated_context()
    return context.get("principles", [])


def get_patterns() -> list:
    """获取交易规律"""
    context = get_isolated_context()
    return context.get("patterns", [])
