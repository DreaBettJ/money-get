"""多Agent协作系统

核心设计：
1. 并行执行：独立Agent同时运行，提升速度
2. 协作机制：Agent之间可以共享中间结果
3. 结果汇总：最后由主Agent整合决策
"""
import asyncio
import concurrent.futures
from typing import Dict, Any, List, Callable
from functools import partial
import time
from ..logger import logger as _logger


class AgentTask:
    """Agent任务"""
    
    def __init__(self, name: str, agent, method: str = "analyze", 
                 args: tuple = (), kwargs: dict = None):
        self.name = name
        self.agent = agent
        self.method = method
        self.args = args
        self.kwargs = kwargs or {}
        self.result = None
        self.error = None
        self.start_time = None
        self.end_time = None
    
    def execute(self) -> Any:
        """执行任务"""
        self.start_time = time.time()
        try:
            method = getattr(self.agent, self.method)
            self.result = method(*self.args, **self.kwargs)
        except Exception as e:
            self.error = str(e)
        finally:
            self.end_time = time.time()
        return self.result
    
    @property
    def duration(self) -> float:
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "result": self.result,
            "error": self.error,
            "duration": self.duration
        }


class AgentTeam:
    """Agent团队 - 并行协作"""
    
    def __init__(self, name: str = "DefaultTeam"):
        self.name = name
        self.tasks: List[AgentTask] = []
        self.results: Dict[str, Any] = {}
        self._shared_context: Dict[str, Any] = {}  # 共享上下文
    
    def add_task(self, name: str, agent, method: str = "analyze", 
                 args: tuple = (), kwargs: dict = None) -> 'AgentTeam':
        """添加任务"""
        task = AgentTask(name, agent, method, args, kwargs)
        self.tasks.append(task)
        return self
    
    def execute_parallel(self, max_workers: int = 4) -> Dict[str, Any]:
        """并行执行所有任务"""
        task_names = [t.name for t in self.tasks]
        _logger.info(f"📈 并行: {task_names}")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(task.execute): task for task in self.tasks}
            
            for future in concurrent.futures.as_completed(futures):
                task = futures[future]
                if task.error:
                    _logger.warning(f"  ❌ {task.name}: {task.error}")
                else:
                    _logger.info(f"  ✅ {task.name} ({task.duration:.1f}s)")
                    self.results[task.name] = task.result
        
        return self.results
    
    def execute_sequential(self) -> Dict[str, Any]:
        """串行执行（保留以备兼容）"""
        _logger.info(f"🔄 {self.name}: 串行执行 {len(self.tasks)} 个任务")
        
        for task in self.tasks:
            _logger.info(f"  ▶️  执行 {task.name}...")
            task.execute()
            if task.error:
                _logger.info(f"  ❌ {task.name} 失败: {task.error}")
            else:
                _logger.info(f"  ✅ {task.name} 完成 ({task.duration:.1f}s)")
                self.results[task.name] = task.result
        
        return self.results
    
    def share_context(self, key: str, value: Any):
        """共享上下文（Agent之间传递数据）"""
        self._shared_context[key] = value
    
    def get_shared(self, key: str, default: Any = None) -> Any:
        """获取共享上下文"""
        return self._shared_context.get(key, default)
    
    def execute_with_dependencies(self, dependency_map: Dict[str, List[str]] = None) -> Dict[str, Any]:
        """按依赖关系执行
        
        Args:
            dependency_map: {task_name: [依赖的任务名]}
        """
        if not dependency_map:
            return self.execute_parallel()
        
        _logger.info(f"🔗 {self.name}: 按依赖执行 {len(self.tasks)} 个任务")
        
        completed = set()
        pending = {task.name for task in self.tasks}
        
        while pending:
            # 找到可以执行的任务（依赖都已完成）
            ready = []
            for task in self.tasks:
                if task.name in pending:
                    deps = dependency_map.get(task.name, [])
                    if all(d in completed for d in deps):
                        ready.append(task)
            
            if not ready:
                break
            
            # 执行就绪的任务
            for task in ready:
                _logger.info(f"  ▶️  执行 {task.name} (依赖: {dependency_map.get(task.name, [])})")
                task.execute()
                pending.remove(task.name)
                
                if task.error:
                    _logger.info(f"  ❌ {task.name} 失败: {task.error}")
                    self.results[task.name] = None
                else:
                    _logger.info(f"  ✅ {task.name} 完成 ({task.duration:.1f}s)")
                    self.results[task.name] = task.result
                    # 共享给其他任务
                    self.share_context(task.name, task.result)
                
                completed.add(task.name)
        
        return self.results


def create_stock_analysis_team(agents: dict) -> AgentTeam:
    """创建股票分析团队
    
    Args:
        agents: dict of {name: agent_instance}
    
    Returns:
        AgentTeam: 配置好的团队
    """
    team = AgentTeam("股票分析团队")
    
    # 阶段1: 并行执行独立分析
    team.add_task("资金分析", agents["fund"], "analyze", ("600519",))
    team.add_task("新闻分析", agents["news"], "analyze", ("600519",))
    team.add_task("情绪分析", agents["sentiment"], "analyze", ("600519",))
    
    # 阶段2: 依赖结果的研究（等第一阶段完成）
    # 这个在 execute_with_dependencies 中配置
    
    return team


# 协作模式示例
COLLABORATION_MODES = {
    "parallel": "所有Agent并行执行，最快",
    "sequential": "串行执行，最稳定",
    "hybrid": "先并行分析，再串行决策",
    "dependency": "按依赖关系自动调度"
}


class MultiAgentOrchestrator:
    """多Agent编排器 - 智能调度"""
    
    def __init__(self, mode: str = "hybrid"):
        self.mode = mode
        self.team = None
    
    def analyze(self, stock_code: str, agents: dict) -> dict:
        """执行多Agent分析
        
        Args:
            stock_code: 股票代码
            agents: Agent字典 {"fund": agent, "news": agent, ...}
        
        Returns:
            dict: 汇总结果
        """
        _logger.info(f"\n{'='*60}")
        _logger.info(f"🚀 开始分析股票: {stock_code} | 模式: {self.mode}")
        _logger.info(f"{'='*60}")
        
        start = time.time()
        
        if self.mode == "parallel":
            result = self._analyze_parallel(stock_code, agents)
        elif self.mode == "sequential":
            result = self._analyze_sequential(stock_code, agents)
        elif self.mode == "hybrid":
            result = self._analyze_hybrid(stock_code, agents)
        elif self.mode == "dependency":
            result = self._analyze_dependency(stock_code, agents)
        else:
            result = self._analyze_hybrid(stock_code, agents)
        
        elapsed = time.time() - start
        _logger.info(f"\n{'='*60}")
        _logger.info(f"✅ 分析完成: {stock_code} | 耗时: {elapsed:.1f}s")
        _logger.info(f"{'='*60}")
        
        return result
    
    def _analyze_parallel(self, stock_code: str, agents: dict) -> dict:
        """纯并行模式"""
        team = AgentTeam("并行分析")
        
        team.add_task("资金", agents["fund"], "analyze", (stock_code,))
        team.add_task("新闻", agents["news"], "analyze", (stock_code,))
        team.add_task("情绪", agents["sentiment"], "analyze", (stock_code,))
        
        results = team.execute_parallel()
        
        # 汇总
        return {
            "fund": results.get("资金"),
            "news": results.get("新闻"),
            "sentiment": results.get("情绪"),
            "research": agents["research"].analyze(stock_code,
                fund_analysis=results.get("资金", ""),
                news_analysis=results.get("新闻", ""),
                sentiment_analysis=results.get("情绪", "")),
            "decision": agents["decision"].analyze(stock_code,
                fund_analysis=results.get("资金", ""),
                news_analysis=results.get("新闻", ""),
                sentiment_analysis=results.get("情绪", ""))
        }
    
    def _analyze_sequential(self, stock_code: str, agents: dict) -> dict:
        """串行模式"""
        # 资金分析
        fund = agents["fund"].analyze(stock_code)
        
        # 新闻分析
        news = agents["news"].analyze(stock_code)
        
        # 情绪分析
        sentiment = agents["sentiment"].analyze(stock_code)
        
        # 研究辩论
        research = agents["research"].analyze(stock_code,
            fund_analysis=fund,
            news_analysis=news,
            sentiment_analysis=sentiment)
        
        # 最终决策
        decision = agents["decision"].analyze(stock_code,
            fund_analysis=fund,
            news_analysis=news,
            sentiment_analysis=sentiment,
            research_result=research)
        
        return {
            "fund": fund,
            "news": news,
            "sentiment": sentiment,
            "research": research,
            "decision": decision
        }
    
    def _analyze_hybrid(self, stock_code: str, agents: dict) -> dict:
        """混合模式：先并行分析，再串行决策"""
        _logger.info("\n--- 📈 阶段1: 并行分析 ---")
        
        team = AgentTeam("混合分析-并行阶段")
        team.add_task("fund", agents["fund"], "analyze", (stock_code,))
        team.add_task("news", agents["news"], "analyze", (stock_code,))
        team.add_task("sentiment", agents["sentiment"], "analyze", (stock_code,))
        
        parallel_results = team.execute_parallel()
        
        fund = parallel_results.get("fund", "")
        news = parallel_results.get("news", "")
        sentiment = parallel_results.get("sentiment", "")
        
        _logger.info("\n--- 📝 阶段2: 串行决策 ---")
        
        # 研究辩论
        research = agents["research"].analyze(stock_code,
            fund_analysis=fund,
            news_analysis=news,
            sentiment_analysis=sentiment)
        
        # 最终决策
        decision = agents["decision"].analyze(stock_code,
            fund_analysis=fund,
            news_analysis=news,
            sentiment_analysis=sentiment,
            research_result=research)
        
        return {
            "fund": fund,
            "news": news,
            "sentiment": sentiment,
            "research": research,
            "decision": decision
        }
    
    def _analyze_dependency(self, stock_code: str, agents: dict) -> dict:
        """依赖模式"""
        team = AgentTeam("依赖分析")
        
        # 第一波: 独立分析
        team.add_task("fund", agents["fund"], "analyze", (stock_code,))
        team.add_task("news", agents["news"], "analyze", (stock_code,))
        team.add_task("sentiment", agents["sentiment"], "analyze", (stock_code,))
        
        # 第二波: 依赖第一波
        # 注意: 这里简化了，实际可以用更复杂的依赖
        
        results = team.execute_with_dependencies({
            "fund": [],
            "news": [],
            "sentiment": []
        })
        
        # 研究和决策（手动串行）
        research = agents["research"].analyze(stock_code,
            fund_analysis=results.get("fund", ""),
            news_analysis=results.get("news", ""),
            sentiment_analysis=results.get("sentiment", ""))
        
        decision = agents["decision"].analyze(stock_code,
            fund_analysis=results.get("fund", ""),
            news_analysis=results.get("news", ""),
            sentiment_analysis=results.get("sentiment", ""),
            research_result=research)
        
        return {
            "fund": results.get("fund"),
            "news": results.get("news"),
            "sentiment": results.get("sentiment"),
            "research": research,
            "decision": decision
        }


# 便捷函数
def parallel_analyze(stock_code: str, agents: dict) -> dict:
    """并行分析"""
    orchestrator = MultiAgentOrchestrator(mode="parallel")
    return orchestrator.analyze(stock_code, agents)


def hybrid_analyze(stock_code: str, agents: dict) -> dict:
    """混合分析（默认）"""
    orchestrator = MultiAgentOrchestrator(mode="hybrid")
    return orchestrator.analyze(stock_code, agents)
