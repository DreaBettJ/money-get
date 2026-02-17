"""记忆系统

简单的公共记忆 + 股票上下文
"""
from money_get.db import get_connection


def add_principle(content: str) -> int:
    """添加投资原则"""
    return add_shared_memory("principles", content)


def add_pattern(content: str) -> int:
    """添加交易规律"""
    return add_shared_memory("patterns", content)


def add_case(content: str) -> int:
    """添加案例"""
    return add_shared_memory("cases", content)


def add_shared_memory(category: str, content: str) -> int:
    """添加公共记忆"""
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


def get_principles() -> str:
    """获取投资原则"""
    return get_shared_memory("principles")


def get_patterns() -> str:
    """获取交易规律"""
    return get_shared_memory("patterns")


def get_cases() -> str:
    """获取案例"""
    return get_shared_memory("cases")


def get_shared_memory(category: str = None) -> str:
    """获取公共记忆"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if category:
        cursor.execute("""
            SELECT content FROM shared_memory 
            WHERE category = ?
            ORDER BY created_at DESC
        """, (category,))
    else:
        cursor.execute("""
            SELECT content FROM shared_memory 
            ORDER BY created_at DESC
        """)
    
    rows = cursor.fetchall()
    conn.close()
    
    return "\n".join([r[0] for r in rows])


def add_stock_context(code: str, context_type: str, content: str) -> int:
    """添加股票上下文"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO stock_context (stock_code, context_type, content)
        VALUES (?, ?, ?)
    """, (code, context_type, content))
    conn.commit()
    _id = cursor.lastrowid
    conn.close()
    return _id


def get_stock_history(code: str, limit: int = 10) -> str:
    """获取股票分析历史"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT content FROM stock_context
        WHERE stock_code = ?
        ORDER BY created_at DESC
        LIMIT ?
    """, (code, limit))
    rows = cursor.fetchall()
    conn.close()
    return "\n".join([r[0] for r in rows])


def build_agent_context(stock_code: str = None) -> str:
    """构建 Agent 上下文"""
    parts = []
    
    principles = get_principles()
    if principles:
        parts.append(f"## 用户投资原则\n{principles}")
    
    patterns = get_patterns()
    if patterns:
        parts.append(f"## 历史规律\n{patterns}")
    
    if stock_code:
        history = get_stock_history(stock_code)
        if history:
            parts.append(f"## {stock_code} 分析历史\n{history}")
    
    return "\n\n".join(parts)
