import json
from typing import Protocol

from app.core.config import settings
from app.schemas.ai_report import (
    AIReportRequest,
    AIReportResponse,
    ChannelOpportunity,
    GrowthAction,
    KeyInsight,
)
from app.schemas.analysis import FunnelStage, GrowthMetrics


SYSTEM_PROMPT = """你是 GrowthLens AI，一名写真行业用户增长分析顾问。

你只能基于用户消息中提供的 data_quality、metrics、funnel、channels 四类聚合结果生成报告。

输出要求：
1. 严格遵守给定的结构化 JSON Schema。
2. summary 用一句话概括整体增长表现。
3. key_insights 输出 2-3 条，每条包含标题、准确的数据依据、原因假设和置信度。
4. channel_opportunities 只能引用输入 channels 中存在的渠道。
5. growth_actions 输出 2-3 条可执行建议，并标明目标指标与预期方向。
6. limitations 说明仅凭当前数据无法判断的事项。

事实约束：
- 不得使用输入之外的数字、渠道、用户画像、行业基准或业务事件。
- evidence 中的数字必须能在输入数据中找到。
- interpretation 必须使用“可能”“推测”或“假设”等措辞，不得把原因假设写成事实。
- 样本量或数据完整度不足时，confidence 必须降为 medium 或 low。
- 不得声称读取过 Excel 原始数据；你只接收到后端计算后的聚合指标。
"""


class AIReportProvider(Protocol):
    name: str

    def generate(self, request: AIReportRequest) -> AIReportResponse:
        """Generate a validated report from aggregated analysis results."""


class AIReportProviderError(RuntimeError):
    """Raised when the configured AI report provider is unavailable."""


def build_model_input(request: AIReportRequest) -> str:
    payload = request.model_dump(mode="json")
    return (
        "请根据以下后端聚合分析结果生成增长报告。"
        "不要补充输入之外的事实：\n"
        f"{json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}"
    )


def generate_ai_report(
    request: AIReportRequest,
    *,
    provider: AIReportProvider | None = None,
) -> AIReportResponse:
    active_provider = provider or get_ai_report_provider()
    report = active_provider.generate(request)
    _validate_report_channels(report, set(request.channels))
    return report


def get_ai_report_provider() -> AIReportProvider:
    if settings.ai_report_provider == "mock":
        return MockAIReportProvider()
    if settings.ai_report_provider == "openai":
        raise AIReportProviderError(
            "OpenAI Provider 尚未启用，请将 AI_REPORT_PROVIDER 设置为 mock。"
        )
    raise AIReportProviderError(
        f"不支持的 AI_REPORT_PROVIDER：{settings.ai_report_provider}"
    )


class MockAIReportProvider:
    name = "mock"

    def generate(self, request: AIReportRequest) -> AIReportResponse:
        stages = request.funnel.stages
        bottleneck_index, bottleneck = _find_bottleneck(stages)
        previous_stage = stages[max(bottleneck_index - 1, 0)]
        channel_items = list(request.channels.items())
        highest_quality = _select_channel(
            channel_items,
            lambda item: (
                item[1].conversion_rates.paid_rate,
                item[1].user_counts.paid_users,
            ),
        )
        largest_channel = _select_channel(
            channel_items,
            lambda item: item[1].user_counts.registered_users,
        )
        quality = request.data_quality
        metrics = request.metrics

        insights = [
            KeyInsight(
                title=f"{previous_stage.label}到{bottleneck.label}是主要流失环节",
                evidence=(
                    f"{previous_stage.label}阶段 {previous_stage.user_count} 人，"
                    f"{bottleneck.label}阶段 {bottleneck.user_count} 人，"
                    f"流失 {bottleneck.dropoff_count} 人，"
                    f"阶段转化率 {_percent(bottleneck.conversion_rate_from_previous)}。"
                ),
                interpretation=(
                    f"该阶段流失较集中，可能与从{previous_stage.label}"
                    f"进入{bottleneck.label}时的承接效率有关，需结合页面和运营记录验证。"
                ),
                confidence=_confidence(
                    previous_stage.user_count,
                    quality.data_completeness,
                ),
            ),
            _channel_quality_insight(
                highest_quality,
                quality.data_completeness,
            ),
        ]

        if largest_channel[0] != highest_quality[0]:
            insights.append(
                _scale_quality_insight(
                    largest_channel,
                    highest_quality,
                    quality.data_completeness,
                )
            )
        else:
            insights.append(
                KeyInsight(
                    title="头部渠道同时贡献用户规模与成交效率",
                    evidence=(
                        f"{largest_channel[0]}注册用户 "
                        f"{largest_channel[1].user_counts.registered_users} 人，"
                        f"成交率 "
                        f"{_percent(largest_channel[1].conversion_rates.paid_rate)}，"
                        f"GMV {_currency(largest_channel[1].revenue.gmv)}。"
                    ),
                    interpretation=(
                        "该渠道可能是当前增长的主要支点，但仍需结合获客成本判断增量价值。"
                    ),
                    confidence=_confidence(
                        largest_channel[1].user_counts.registered_users,
                        quality.data_completeness,
                    ),
                )
            )

        opportunities = _build_channel_opportunities(
            highest_quality,
            largest_channel,
            quality.data_completeness,
        )
        actions = _build_growth_actions(
            bottleneck,
            previous_stage,
            highest_quality,
            largest_channel,
        )
        limitations = _build_limitations(request)

        return AIReportResponse(
            summary=(
                f"本期 {metrics.user_counts.registered_users} 名注册用户最终形成 "
                f"{metrics.user_counts.paid_users} 名成交用户和 "
                f"{_currency(metrics.revenue.gmv)} GMV，"
                f"主要优化空间位于{previous_stage.label}到{bottleneck.label}阶段。"
            ),
            key_insights=insights,
            channel_opportunities=opportunities,
            growth_actions=actions,
            limitations=limitations,
        )


def _find_bottleneck(
    stages: list[FunnelStage],
) -> tuple[int, FunnelStage]:
    if len(stages) < 2:
        raise AIReportProviderError("漏斗阶段不足，无法生成增长报告。")
    return max(
        enumerate(stages[1:], start=1),
        key=lambda item: (
            item[1].dropoff_rate,
            item[1].dropoff_count,
        ),
    )


def _select_channel(
    channels: list[tuple[str, GrowthMetrics]],
    score,
) -> tuple[str, GrowthMetrics]:
    if not channels:
        raise AIReportProviderError("缺少渠道分析结果，无法生成增长报告。")
    return max(channels, key=score)


def _channel_quality_insight(
    channel: tuple[str, GrowthMetrics],
    completeness: float,
) -> KeyInsight:
    name, channel_metrics = channel
    return KeyInsight(
        title=f"{name}当前成交效率领先",
        evidence=(
            f"{name}注册用户 {channel_metrics.user_counts.registered_users} 人，"
            f"到店用户 {channel_metrics.user_counts.visit_users} 人，"
            f"成交用户 {channel_metrics.user_counts.paid_users} 人，"
            f"成交率 {_percent(channel_metrics.conversion_rates.paid_rate)}。"
        ),
        interpretation=(
            "该渠道用户可能具有更高的成交意愿，"
            "但是否值得扩大投入仍需结合渠道成本验证。"
        ),
        confidence=_confidence(
            channel_metrics.user_counts.visit_users,
            completeness,
        ),
    )


def _scale_quality_insight(
    largest: tuple[str, GrowthMetrics],
    quality: tuple[str, GrowthMetrics],
    completeness: float,
) -> KeyInsight:
    largest_name, largest_metrics = largest
    quality_name, quality_metrics = quality
    return KeyInsight(
        title="渠道规模与成交效率存在差异",
        evidence=(
            f"{largest_name}注册用户最多，为 "
            f"{largest_metrics.user_counts.registered_users} 人，成交率 "
            f"{_percent(largest_metrics.conversion_rates.paid_rate)}；"
            f"{quality_name}成交率最高，为 "
            f"{_percent(quality_metrics.conversion_rates.paid_rate)}。"
        ),
        interpretation=(
            f"{largest_name}可能更适合承担获客规模，"
            f"{quality_name}可能更适合验证高意向转化策略。"
        ),
        confidence=_confidence(
            min(
                largest_metrics.user_counts.registered_users,
                quality_metrics.user_counts.visit_users,
            ),
            completeness,
        ),
    )


def _build_channel_opportunities(
    quality: tuple[str, GrowthMetrics],
    largest: tuple[str, GrowthMetrics],
    completeness: float,
) -> list[ChannelOpportunity]:
    quality_name, quality_metrics = quality
    largest_name, largest_metrics = largest
    opportunities = [
        ChannelOpportunity(
            channel=quality_name,
            opportunity="保留高成交效率，验证扩大有效流量后的承接能力。",
            evidence=(
                f"成交率 {_percent(quality_metrics.conversion_rates.paid_rate)}，"
                f"成交用户 {quality_metrics.user_counts.paid_users} 人，"
                f"GMV {_currency(quality_metrics.revenue.gmv)}。"
            ),
            confidence=_confidence(
                quality_metrics.user_counts.visit_users,
                completeness,
            ),
        )
    ]
    if largest_name != quality_name:
        opportunities.append(
            ChannelOpportunity(
                channel=largest_name,
                opportunity="优先排查高流量渠道的成交承接，缩小规模与质量差距。",
                evidence=(
                    f"注册用户 {largest_metrics.user_counts.registered_users} 人，"
                    f"成交率 {_percent(largest_metrics.conversion_rates.paid_rate)}，"
                    f"成交用户 {largest_metrics.user_counts.paid_users} 人。"
                ),
                confidence=_confidence(
                    largest_metrics.user_counts.registered_users,
                    completeness,
                ),
            )
        )
    return opportunities


def _build_growth_actions(
    bottleneck: FunnelStage,
    previous_stage: FunnelStage,
    quality: tuple[str, GrowthMetrics],
    largest: tuple[str, GrowthMetrics],
) -> list[GrowthAction]:
    quality_name, _ = quality
    largest_name, _ = largest
    actions = [
        GrowthAction(
            action=(
                f"复盘{previous_stage.label}到{bottleneck.label}的页面路径与运营触达，"
                "针对主要流失节点设计一轮小流量实验。"
            ),
            target_metric=f"{previous_stage.label}到{bottleneck.label}阶段转化率",
            expected_direction="increase",
        ),
        GrowthAction(
            action=(
                f"在{quality_name}复用当前高转化链路，"
                "分批增加有效流量并观察成交效率是否稳定。"
            ),
            target_metric=f"{quality_name}成交用户数",
            expected_direction="increase",
        ),
    ]
    if largest_name != quality_name:
        actions.append(
            GrowthAction(
                action=(
                    f"针对{largest_name}梳理预约后提醒与到店承接，"
                    "以现有高质量渠道表现作为内部对照。"
                ),
                target_metric=f"{largest_name}成交率",
                expected_direction="increase",
            )
        )
    return actions


def _build_limitations(request: AIReportRequest) -> list[str]:
    quality = request.data_quality
    limitations = [
        "报告仅基于单次上传后的聚合结果，不能判断指标的时间趋势或因果关系。",
        "输入未包含渠道投放成本，当前无法比较 CAC、ROI 或真实增量价值。",
        "输入未包含复购、退款与留存字段，当前建议只覆盖注册到成交链路。",
    ]
    if quality.anomaly_count:
        limitations.append(
            f"数据中有 {quality.anomaly_count} 条异常记录，结论需结合数据质量摘要复核。"
        )
    if quality.valid_user_count < 30:
        limitations.append(
            f"当前仅有 {quality.valid_user_count} 名有效用户，样本量较小，洞察置信度已下调。"
        )
    return limitations


def _validate_report_channels(
    report: AIReportResponse,
    allowed_channels: set[str],
) -> None:
    reported_channels = {
        opportunity.channel
        for opportunity in report.channel_opportunities
    }
    unknown_channels = reported_channels - allowed_channels
    if unknown_channels:
        names = "、".join(sorted(unknown_channels))
        raise AIReportProviderError(f"AI 报告引用了未知渠道：{names}")


def _confidence(sample_size: int, completeness: float) -> str:
    if sample_size < 30 or completeness < 0.75:
        return "low"
    if sample_size < 100 or completeness < 0.9:
        return "medium"
    return "high"


def _percent(value: float) -> str:
    return f"{value * 100:.2f}%"


def _currency(value: float) -> str:
    return f"¥{value:,.2f}"
