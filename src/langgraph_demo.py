"""LangGraph 可观测性演示"""
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool

# 配置
API_KEY = "sk-cp-G6lp_kvQw1s0C2RIlhI5olEW2_bWVaGS7Bm1OHXJCgepwkkQixMepNEoH0KnmxXi4ox0l1CIjCxzPBrJSHrSwrwnU663Y_cxIMiHkeL06x8gNqD_9zPAOds"

# LLM
llm = ChatOpenAI(
    model="MiniMax-M2.1",
    api_key=API_KEY,
    base_url="https://api.minimax.chat/v1",
    temperature=0.3
)

# 工具 - 使用 @tool 装饰器
@tool
def get_stock_price(symbol: str) -> str:
    """获取股票当前价格"""
    prices = {"600519": "1850元", "300719": "20.89元", "000858": "50元"}
    return f"{symbol}: {prices.get(symbol, 'N/A')}"

@tool
def get_stock_info(symbol: str) -> str:
    """获取股票基本信息(行业、概念等)"""
    info = {
        "600519": "贵州茅台 - 白酒行业龙头",
        "300719": "安达维尔 - 军工行业",
        "000858": "五粮液 - 白酒行业"
    }
    return info.get(symbol, f"{symbol}: 未知")

tools = [get_stock_price, get_stock_info]

# 创建 Agent
agent = create_agent(llm, tools, system_prompt="你是一个专业的股票分析师")

print("=" * 60)
print("🚀 LangGraph 可观测性演示")
print("=" * 60)

# 1. Agent 结构
print("\n📋 Agent 类型:")
print(f"   {type(agent).__name__}")

# 2. 工具列表
print("\n🔧 可用 Tools:")
for t in tools:
    print(f"   [{t.name}]")
    print(f"      描述: {t.description}")
    print(f"      参数: {t.args}")

# 3. 查看 Graph 结构
print("\n📊 Graph 结构:")
g = agent.get_graph()
print(f"   节点: {list(g.nodes.keys())}")

# 4. 执行
print("\n" + "=" * 60)
print("📤 执行查询...")
print("=" * 60)

messages = [HumanMessage(content="查询600519的价格和基本信息")]

response = agent.invoke({"messages": messages})

# 5. 结果
print("\n📥 Agent Response:")
print("-" * 40)
msg = response['messages'][-1]
print(f"类型: {type(msg).__name__}")
print(f"内容: {msg.content[:300]}")

# 6. 消息历史
print("\n💬 消息历史:")
for i, m in enumerate(response['messages']):
    role = type(m).__name__
    content = m.content[:50] if m.content else "tool call"
    print(f"   [{i}] {role}: {content}...")

print("\n✅ 演示完成!")
print("💡 Langfuse: https://cloud.langfuse.com")
