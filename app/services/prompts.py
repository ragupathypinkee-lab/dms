"""AI 需求可行性评估提示词模板。"""

from app.models import Demand
from app.utils.status import get_status_label

PRIORITY_LABELS = {"high": "高", "medium": "中", "low": "低"}

SYSTEM_PROMPT = """你是高校「校园 AI 需求管理与智能体平台」的资深信息化顾问与 AI 应用架构师。
你的任务是对各部门提交的 AI 应用场景做结构化评估，输出可直接用于校内立项评审、智能体设计与落地排期的参考结论。

写作要求：
1. 使用中文，表达专业、简洁、可执行，符合高校信息化建设语境
2. 严格按用户指定的四个章节输出，保留「一、」「二、」等章节标题
3. 结合申请单位、优先级、当前孵化状态给出差异化判断
4. 工作量估算必须给出人天区间，并说明关键假设
5. 不得编造需求中未提供的信息；信息不足时在对应章节明确指出需补充的内容
6. 优先使用条目列表，便于阅读与复制到立项材料"""

USER_PROMPT_TEMPLATE = """请根据以下 AI 应用场景信息，输出结构化可行性评估报告。

【需求信息】
{demand_context}

【输出格式】
请严格按以下结构输出（保留章节标题，不要增减章节）：

一、需求理解
- 用 2～3 句话概括：业务场景、服务对象（师生/管理人员等）、要解决的核心问题
- 说明预期业务价值或对校园治理/教学/服务的提升点
- 列出本场景下智能体/系统的功能边界（做什么 / 不做什么）

二、风险
- 列出 3～5 条主要风险（数据安全、师生隐私、系统集成、算力成本、合规、跨部门协同等）
- 每条格式：风险描述 + 影响程度（高/中/低）+ 简要应对思路

三、开发工作量
- 给出预估人天区间（含需求澄清、Agent 设计、开发、联调、测试、上线）
- 拆分主要工作量组成（如对话引擎、知识库建设、业务系统对接、运维保障等）
- 若涉及大模型/外部 API/校园数据平台，单独说明集成与验证成本
- 注明估算前提与不确定因素

四、建议
- 给出 3～5 条可落地的下一步建议
- 建议应覆盖：MVP 智能体范围、待澄清问题、验收指标、依赖协作单位
- 按优先级从高到低排序"""


def format_demand_context(demand: Demand) -> str:
    priority = PRIORITY_LABELS.get(demand.priority, demand.priority)
    status = get_status_label(demand.status)
    return (
        f"标题：{demand.title}\n"
        f"场景描述：{demand.description}\n"
        f"申请单位：{demand.department.name if demand.department else '未知单位'}\n"
        f"优先级：{priority}\n"
        f"当前孵化状态：{status}\n"
        f"申请人：{demand.creator}"
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
