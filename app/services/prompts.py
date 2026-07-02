"""AI 需求分析提示词模板。"""

from app.models import Demand
from app.utils.status import get_status_label

PRIORITY_LABELS = {"high": "高", "medium": "中", "low": "低"}

SYSTEM_PROMPT = """你是企业级「AI 需求登记系统」的资深产品与技术顾问。
你的任务是对业务方提交的 AI/数字化需求做结构化评估，输出可直接用于需求评审、排期与立项的参考结论。

写作要求：
1. 使用中文，表达专业、简洁、可执行，避免空泛套话
2. 严格按用户指定的四个章节输出，保留「一、」「二、」等章节标题
3. 结合需求的部门、优先级、当前状态给出差异化判断
4. 工作量估算必须给出人天区间，并说明关键假设
5. 不得编造需求中未提供的信息；信息不足时在对应章节明确指出需补充的内容
6. 优先使用条目列表，便于阅读与复制到需求文档"""

USER_PROMPT_TEMPLATE = """请根据以下需求信息，输出结构化 AI 需求分析报告。

【需求信息】
{demand_context}

【输出格式】
请严格按以下结构输出（保留章节标题，不要增减章节）：

一、需求理解
- 用 2～3 句话概括：背景、目标用户、要解决的核心问题
- 说明预期业务价值或效率提升点
- 列出本需求的功能边界（做什么 / 不做什么）

二、风险
- 列出 3～5 条主要风险（技术、数据、集成、合规、资源、排期等）
- 每条格式：风险描述 + 影响程度（高/中/低）+ 简要应对思路

三、开发工作量
- 给出预估人天区间（含需求澄清、设计、开发、联调、测试、上线）
- 拆分主要工作量组成（如前端、后端、AI 对接、数据准备等）
- 若涉及大模型/外部 API/第三方系统，单独说明集成与验证成本
- 注明估算前提与不确定因素

四、建议
- 给出 3～5 条可落地的下一步建议
- 建议应覆盖：MVP 范围、待澄清问题、验收指标、依赖协作方
- 按优先级从高到低排序"""


def format_demand_context(demand: Demand) -> str:
    priority = PRIORITY_LABELS.get(demand.priority, demand.priority)
    status = get_status_label(demand.status)
    return (
        f"标题：{demand.title}\n"
        f"描述：{demand.description}\n"
        f"所属部门：{demand.department}\n"
        f"优先级：{priority}\n"
        f"当前状态：{status}\n"
        f"创建人：{demand.creator}"
    )


def build_analysis_messages(demand: Demand) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": USER_PROMPT_TEMPLATE.format(
                demand_context=format_demand_context(demand)
            ),
        },
    ]
