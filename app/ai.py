import logging

from openai import APIConnectionError, APIStatusError, AuthenticationError, OpenAI

from app.config import settings
from app.models import Demand

logger = logging.getLogger(__name__)

PRIORITY_LABELS = {"high": "高", "medium": "中", "low": "低"}

ANALYSIS_INSTRUCTION = """请根据下面需求输出：

一、需求理解

二、风险

三、开发工作量

四、建议"""


class AnalysisResult:
    __slots__ = ("text", "message", "is_mock")

    def __init__(self, text: str, message: str, is_mock: bool = False):
        self.text = text
        self.message = message
        self.is_mock = is_mock


def _format_demand(demand: Demand) -> str:
    priority = PRIORITY_LABELS.get(demand.priority, demand.priority)
    return (
        f"标题：{demand.title}\n"
        f"描述：{demand.description}\n"
        f"部门：{demand.department}\n"
        f"优先级：{priority}"
    )


def _mock_analysis(demand: Demand, reason: str | None = None) -> str:
    priority = PRIORITY_LABELS.get(demand.priority, demand.priority)
    reason_line = f"（{reason}）\n\n" if reason else ""
    return f"""【模拟分析结果】
{reason_line}一、需求理解
该需求「{demand.title}」由 {demand.department} 提出，优先级为 {priority}。核心目标是通过 {demand.description[:80]}{"..." if len(demand.description) > 80 else ""} 解决业务痛点，提升相关流程效率。

二、风险
1. 需求描述可能不够完整，需进一步澄清边界条件
2. 跨部门协作可能带来沟通成本
3. 优先级为 {priority}，需关注资源排期冲突

三、开发工作量
预估 3–5 人天（含需求澄清、开发、联调与测试）。若涉及外部系统集成，工作量可能增加至 1–2 周。

四、建议
1. 补充验收标准与成功指标
2. 安排需求评审，确认 MVP 范围
3. 建议先完成原型验证，再进入正式开发"""


def _fallback_reason(exc: Exception) -> str:
    if isinstance(exc, AuthenticationError):
        return "API Key 无效或已过期，已使用模拟分析"
    if isinstance(exc, APIStatusError):
        if exc.status_code == 401:
            return "API Key 无效或已过期，已使用模拟分析"
        if exc.status_code == 404:
            return "模型或接口地址不可用，已使用模拟分析"
        return f"AI 服务异常（{exc.status_code}），已使用模拟分析"
    if isinstance(exc, APIConnectionError):
        return "无法连接 AI 服务，已使用模拟分析"
    return "AI 服务调用失败，已使用模拟分析"


def analyze_demand(demand: Demand) -> AnalysisResult:
    if not settings.openai_api_key:
        return AnalysisResult(
            text=_mock_analysis(demand),
            message="未配置 API Key，已使用模拟分析",
            is_mock=True,
        )

    client = OpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url or None,
    )

    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": "你是资深产品与技术顾问，请用中文简洁专业地分析需求。",
                },
                {
                    "role": "user",
                    "content": f"{ANALYSIS_INSTRUCTION}\n\n{_format_demand(demand)}",
                },
            ],
            temperature=0.7,
        )
    except (AuthenticationError, APIStatusError, APIConnectionError) as exc:
        logger.warning("AI analysis failed, using mock: %s", exc)
        reason = _fallback_reason(exc)
        return AnalysisResult(
            text=_mock_analysis(demand, reason=reason),
            message=reason,
            is_mock=True,
        )
    except Exception as exc:
        logger.exception("Unexpected AI analysis error")
        reason = _fallback_reason(exc)
        return AnalysisResult(
            text=_mock_analysis(demand, reason=reason),
            message=reason,
            is_mock=True,
        )

    content = response.choices[0].message.content
    if not content:
        return AnalysisResult(
            text=_mock_analysis(demand, reason="AI 返回内容为空，已使用模拟分析"),
            message="AI 返回内容为空，已使用模拟分析",
            is_mock=True,
        )

    return AnalysisResult(
        text=content.strip(),
        message="AI 分析完成",
        is_mock=False,
    )
