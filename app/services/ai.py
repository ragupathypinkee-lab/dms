import logging

from openai import APIConnectionError, APIStatusError, AuthenticationError, OpenAI

from app.core.config import settings
from app.models import Demand
from app.services.prompts import PRIORITY_LABELS, build_analysis_messages
from app.utils.status import get_status_label

logger = logging.getLogger(__name__)


class AnalysisResult:
    __slots__ = ("text", "message", "is_mock")

    def __init__(self, text: str, message: str, is_mock: bool = False):
        self.text = text
        self.message = message
        self.is_mock = is_mock


def _mock_analysis(demand: Demand, reason: str | None = None) -> str:
    priority = PRIORITY_LABELS.get(demand.priority, demand.priority)
    status = get_status_label(demand.status)
    desc = demand.description[:100] + ("..." if len(demand.description) > 100 else "")
    reason_line = f"（{reason}）\n" if reason else ""

    return f"""【模拟分析结果】
{reason_line}
一、需求理解
- 「{demand.title}」由 {demand.department}（{demand.creator}）提出，当前状态为 {status}，优先级 {priority}。
- 核心目标：{desc}
- 功能边界：围绕上述描述完成 MVP 闭环；具体验收标准、异常流程需进一步澄清。

二、风险
1. 需求边界不清晰（影响：中）— 建议召开 30 分钟需求澄清会，确认 MVP 范围
2. 跨部门协作成本（影响：中）— 提前明确接口人与评审节点
3. AI/数据依赖不确定（影响：高）— 确认是否依赖外部模型、数据源及权限
4. 排期与优先级冲突（影响：{ "高" if demand.priority == "high" else "中" }）— 与现有迭代计划对齐资源

三、开发工作量
- 预估：5～8 人天（含澄清、开发、联调、测试）
- 组成：后端 2～3 人天、前端 1～2 人天、联调测试 2～3 人天
- 若涉及 AI 接口对接或第三方集成，额外增加 3～5 人天
- 前提：需求范围不再大幅变更，且无复杂权限/合规要求

四、建议
1. 【高】补充验收标准与成功指标（如效率提升百分比、覆盖场景）
2. 【高】确认 MVP 最小功能集，避免首版范围过大
3. 【中】安排需求评审，产品、研发、业务方共同参与
4. 【中】如涉及 AI，提前验证模型效果与 API 稳定性
5. 【低】上线后设定 2 周观察期，收集使用反馈再迭代"""


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
            messages=build_analysis_messages(demand),
            temperature=0.5,
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
