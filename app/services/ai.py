import logging

from openai import APIConnectionError, APIStatusError, APITimeoutError, AuthenticationError, OpenAI

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

    return f"""【模拟评估报告】
{reason_line}
一、需求理解
- 「{demand.title}」由 {demand.department.name if demand.department else "未知单位"}（{demand.creator}）提出，当前孵化状态为 {status}，优先级 {priority}。
- 核心目标：{desc}
- 智能体边界：围绕上述校园场景完成 MVP 闭环；具体验收标准、数据权限与异常流程需进一步澄清。

二、风险
1. 场景边界与数据范围不清晰（影响：中）— 建议召开校内需求澄清会，明确服务对象与数据来源
2. 跨部门协同与系统对接（影响：中）— 提前明确信息化中心与各业务单位接口人
3. 师生隐私与数据安全合规（影响：高）— 确认是否涉及个人敏感信息及脱敏方案
4. 算力与模型服务稳定性（影响：{ "高" if demand.priority == "high" else "中" }）— 评估校内算力或云服务资源

三、开发工作量
- 预估：8～15 人天（含 Agent 设计、开发、联调、测试、试点上线）
- 组成：知识库准备 2～3 人天、智能体开发 3～5 人天、业务系统对接 2～4 人天、测试验收 2～3 人天
- 若涉及校园统一身份认证或数据中台对接，额外增加 3～5 人天
- 前提：场景范围稳定，且无复杂多级审批流程

四、建议
1. 【高】明确 MVP 智能体能力与首批试点用户范围
2. 【高】补充验收指标（如响应准确率、办事时长缩短比例）
3. 【中】安排信息化中心与申请单位联合评审
4. 【中】提前验证模型效果与校园网络环境适配性
5. 【低】上线后设定 2 周观察期，收集师生反馈再迭代"""


def _fallback_reason(exc: Exception) -> str:
    if isinstance(exc, AuthenticationError):
        return "API Key 无效或已过期，已使用模拟评估"
    if isinstance(exc, APIStatusError):
        if exc.status_code == 401:
            return "API Key 无效或已过期，已使用模拟评估"
        if exc.status_code == 404:
            return "模型或接口地址不可用，已使用模拟评估"
        return f"AI 服务异常（{exc.status_code}），已使用模拟评估"
    if isinstance(exc, APITimeoutError):
        return "AI 服务响应超时，已使用模拟评估"
    if isinstance(exc, APIConnectionError):
        return "无法连接 AI 服务，已使用模拟评估"
    return "AI 服务调用失败，已使用模拟评估"


def analyze_demand(demand: Demand) -> AnalysisResult:
    if not settings.openai_api_key:
        return AnalysisResult(
            text=_mock_analysis(demand),
            message="未配置 API Key，已使用模拟评估",
            is_mock=True,
        )

    client = OpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url or None,
        timeout=settings.openai_timeout,
    )

    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=build_analysis_messages(demand),
            temperature=0.5,
        )
    except (AuthenticationError, APIStatusError, APIConnectionError, APITimeoutError) as exc:
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
            text=_mock_analysis(demand, reason="AI 返回内容为空，已使用模拟评估"),
            message="AI 返回内容为空，已使用模拟评估",
            is_mock=True,
        )

    return AnalysisResult(
        text=content.strip(),
        message="AI 可行性评估完成",
        is_mock=False,
    )
