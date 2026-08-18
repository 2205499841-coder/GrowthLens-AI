import json
import logging
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Protocol

from pydantic import ValidationError

from app.core.config import settings
from app.schemas.ai_report import (
    AIReportRequest,
    AIReportResponse,
    GrowthOpportunity,
    KeyIssue,
    PriorityAction,
    ReportEvidence,
)
from app.schemas.analysis import FunnelStage, GrowthMetrics


logger = logging.getLogger(__name__)

MAX_AGGREGATE_DIMENSIONS = 20
NUMBER_PATTERN = re.compile(
    r"(?<!\w)([+-]?\d[\d,]*(?:\.\d+)?)\s*(个百分点|%|人|元)?(?!\w)"
)

REPORT_JSON_EXAMPLE = {
    "core_conclusion": "引用真实业务信号的核心结论",
    "key_issues": [
        {
            "issue": "需要优先处理的问题",
            "evidence": [
                {
                    "text": "从 evidence_catalog 原样引用的证据",
                    "evidence_ref": ["输入中真实存在的 ref"],
                }
            ],
            "impact": "问题对业务结果的影响判断",
            "confidence": "high",
        }
    ],
    "priority_actions": [
        {
            "action": "包含建议验证字样的具体动作",
            "applicable_to": "适用维度或环节",
            "reason": "与重点问题直接对应的建议原因",
            "target_metric": "输入中真实存在的指标",
        }
    ],
    "opportunities": [
        {
            "target": "机会对象",
            "evidence": [
                {
                    "text": "从 evidence_catalog 引用的机会证据",
                    "evidence_ref": ["输入中真实存在的 ref"],
                }
            ],
            "recommendation": "针对机会的建议验证动作",
        }
    ],
    "limitations": ["结构化分析结果中真实存在的数据限制"],
}

SYSTEM_PROMPT = f"""你是 GrowthLens AI，一名面向增长运营人员的业务诊断顾问。

你只能读取用户消息中的 diagnostic_context 和 evidence_catalog。后端已经完成指标计算、漏斗分析、同比环比分析和异常识别；你不得重新计算、修改或补充任何指标。

输出要求：
1. 只输出合法 JSON 对象，不要 Markdown、代码块或额外说明。
2. 统一输出 core_conclusion、key_issues、priority_actions、opportunities、limitations。
3. core_conclusion 只写一段，优先控制在 80—120 个中文字符，必须指出具体表现对象、问题节点或改善方向，禁止空泛总结。
4. key_issues 最多 3 条；每条包含 issue、evidence、impact、confidence。
5. priority_actions 最多 3 条；每条包含 action、applicable_to、reason、target_metric，并使用“建议验证”明确标识尚未被数据证明的原因或动作假设。
6. opportunities 最多 2 条；优先使用后端已经识别的业务洞察和机会。
7. evidence 中每条证据必须填写 evidence_ref，且只能使用 evidence_catalog 中真实存在的 ref。

JSON 结构示例（只表示结构，不是可引用事实）：
{json.dumps(REPORT_JSON_EXAMPLE, ensure_ascii=False, indent=2)}

事实约束：
- 所有数字必须复制 evidence_catalog 中的 display_value，不得自行计算、换算、四舍五入或修改。
- 百分比与百分点必须严格沿用 evidence_catalog 中的 unit 和 display_value。
- 不得引用输入之外的品类、渠道、用户画像、行业基准、业务事件或原因。
- diagnostic_context.business_insights 是优先事实来源；不要重新发现一套与后端结论冲突的问题。
- 原因解释必须写成待验证假设，不得当成已经证实的事实。
- 避免“赋能、抓手、形成闭环、持续深耕、多维度协同、进一步提升用户体验”等空泛表达。
- 不得声称读取过 Excel 或原始业务数据。
"""


@dataclass(frozen=True)
class EvidenceFact:
    reference: str
    label: str
    display_value: str
    unit: str

    def as_dict(self) -> dict[str, str]:
        return {
            "ref": self.reference,
            "label": self.label,
            "display_value": self.display_value,
            "unit": self.unit,
        }


class AIReportProvider(Protocol):
    name: str

    def generate(self, request: AIReportRequest) -> AIReportResponse:
        """Generate a report from validated structured analysis results."""


class AIReportProviderError(RuntimeError):
    """Raised when report generation or evidence validation fails."""


def build_model_input(request: AIReportRequest) -> str:
    payload = {
        "diagnostic_context": _build_diagnostic_context(request),
        "evidence_catalog": [
            fact.as_dict() for fact in _build_evidence_catalog(request)
        ],
    }
    return (
        "请根据以下结构化诊断上下文生成 AI 增长诊断。"
        "不要重新计算指标，只返回 JSON：\n"
        f"{json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}"
    )


def generate_ai_report(
    request: AIReportRequest,
    *,
    provider: AIReportProvider | None = None,
) -> AIReportResponse:
    active_provider = provider or get_ai_report_provider()
    report = active_provider.generate(request)
    _validate_report_evidence(request, report)
    return report


def get_ai_report_provider() -> AIReportProvider:
    if settings.ai_provider == "deepseek":
        return DeepSeekAIReportProvider(
            api_key=settings.deepseek_api_key,
            model=settings.ai_model,
        )
    if settings.ai_provider == "openai":
        return OpenAIReportProvider(
            api_key=settings.openai_api_key,
            model=settings.ai_model,
        )
    if settings.ai_provider == "mock":
        return MockAIReportProvider()
    raise AIReportProviderError(
        f"不支持的 AI_PROVIDER：{settings.ai_provider}"
    )


class OpenAICompatibleAIReportProvider:
    """Shared adapter for providers exposing OpenAI Chat Completions."""

    def __init__(
        self,
        *,
        name: str,
        display_name: str,
        api_key: str | None,
        api_key_env: str,
        model: str,
        base_url: str | None = None,
        completion_options: dict[str, Any] | None = None,
        client: Any | None = None,
    ) -> None:
        if not api_key:
            raise AIReportProviderError(
                f"未配置 {api_key_env}，无法调用 {display_name} Provider。"
            )
        if not model:
            raise AIReportProviderError(
                "未配置 AI_MODEL，无法生成 AI 增长报告。"
            )

        self.name = name
        self.display_name = display_name
        self.model = model
        self.base_url = base_url
        self.completion_options = completion_options or {}
        self._client = client or _create_openai_client(
            api_key=api_key,
            base_url=base_url,
        )

    def generate(self, request: AIReportRequest) -> AIReportResponse:
        try:
            completion = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": build_model_input(request)},
                ],
                response_format={"type": "json_object"},
                max_tokens=3000,
                stream=False,
                **self.completion_options,
            )
        except Exception as exc:
            logger.exception(
                "%s API 调用异常：%r",
                self.display_name,
                exc,
            )
            _log_provider_response_details(self.display_name, exc)
            raise AIReportProviderError(
                f"{self.display_name} API 调用失败，请检查服务配置或稍后重试。"
            ) from exc

        try:
            content = completion.choices[0].message.content
        except (AttributeError, IndexError, TypeError) as exc:
            raise AIReportProviderError(
                f"{self.display_name} API 返回了无法识别的响应结构。"
            ) from exc
        if not content or not content.strip():
            raise AIReportProviderError(
                f"{self.display_name} API 返回了空报告，请稍后重试。"
            )

        try:
            payload = json.loads(content)
            return AIReportResponse.model_validate(payload)
        except (json.JSONDecodeError, ValidationError, TypeError) as exc:
            raise AIReportProviderError(
                f"{self.display_name} 返回内容不符合 AI 报告 JSON 结构。"
            ) from exc


class DeepSeekAIReportProvider(OpenAICompatibleAIReportProvider):
    name = "deepseek"

    def __init__(
        self,
        *,
        api_key: str | None,
        model: str,
        client: Any | None = None,
    ) -> None:
        super().__init__(
            name=self.name,
            display_name="DeepSeek",
            api_key=api_key,
            api_key_env="DEEPSEEK_API_KEY",
            model=model,
            base_url="https://api.deepseek.com",
            completion_options={
                "extra_body": {
                    "thinking": {"type": "disabled"},
                }
            },
            client=client,
        )


class OpenAIReportProvider(OpenAICompatibleAIReportProvider):
    name = "openai"

    def __init__(
        self,
        *,
        api_key: str | None,
        model: str,
        client: Any | None = None,
    ) -> None:
        super().__init__(
            name=self.name,
            display_name="OpenAI",
            api_key=api_key,
            api_key_env="OPENAI_API_KEY",
            model=model,
            client=client,
        )


def _create_openai_client(
    *,
    api_key: str,
    base_url: str | None,
) -> Any:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise AIReportProviderError(
            "缺少 openai SDK，请先安装 backend/requirements.txt。"
        ) from exc

    client_options: dict[str, Any] = {
        "api_key": api_key,
        "max_retries": 1,
        "timeout": 30.0,
    }
    if base_url:
        client_options["base_url"] = base_url
    return OpenAI(**client_options)


def _log_provider_response_details(
    provider_name: str,
    exc: Exception,
) -> None:
    response = getattr(exc, "response", None)
    status_code = getattr(exc, "status_code", None)
    if status_code is None and response is not None:
        status_code = getattr(response, "status_code", None)
    response_body = None
    if response is not None:
        try:
            response_body = getattr(response, "text", None)
        except Exception:
            logger.exception("%s API 响应体读取失败", provider_name)
    if response_body is None:
        response_body = getattr(exc, "body", None)
    if status_code is not None:
        logger.error(
            "%s API response status_code=%s",
            provider_name,
            status_code,
        )
    if response_body is not None:
        logger.error(
            "%s API response body=%r",
            provider_name,
            response_body,
        )


class MockAIReportProvider:
    name = "mock"

    def generate(self, request: AIReportRequest) -> AIReportResponse:
        if request.dataset_type == "aggregate_metrics":
            return _build_mock_aggregate_report(request)
        return _build_mock_user_report(request)


def _build_mock_user_report(request: AIReportRequest) -> AIReportResponse:
    metrics = _require(request.metrics, "metrics")
    funnel = _require(request.funnel, "funnel")
    channels = _require(request.channels, "channels")
    bottleneck_index, bottleneck = _find_bottleneck(funnel.stages)
    previous_stage = funnel.stages[max(bottleneck_index - 1, 0)]
    channel_items = list(channels.items())
    if not channel_items:
        raise AIReportProviderError("缺少渠道分析结果，无法生成增长报告。")
    largest_name, largest_metrics = max(
        channel_items,
        key=lambda item: item[1].user_counts.registered_users,
    )
    quality_name, quality_metrics = max(
        channel_items,
        key=lambda item: (
            item[1].conversion_rates.paid_rate,
            item[1].user_counts.paid_users,
        ),
    )
    bottleneck_ref = (
        f"user_level.funnel.stages[{bottleneck_index}].conversion_rate"
    )
    largest_ref = (
        f"user_level.channels.{largest_name}.registered_users"
    )
    quality_ref = f"user_level.channels.{quality_name}.paid_rate"
    return AIReportResponse(
        core_conclusion=(
            f"当前 {_display(metrics.user_counts.registered_users, 'count')} 注册用户形成 "
            f"{_display(metrics.user_counts.paid_users, 'count')} 成交用户，"
            f"{previous_stage.label}→{bottleneck.label}阶段转化率为 "
            f"{_display(bottleneck.conversion_rate_from_previous, 'ratio')}，"
            f"应优先验证该环节的承接路径；{quality_name}可作为渠道扩量观察对象。"
        ),
        key_issues=[
            KeyIssue(
                issue=f"{previous_stage.label}→{bottleneck.label}是主要流失节点",
                evidence=[
                    ReportEvidence(
                        text=(
                            f"阶段转化率 "
                            f"{_display(bottleneck.conversion_rate_from_previous, 'ratio')}"
                        ),
                        evidence_ref=[bottleneck_ref],
                    )
                ],
                impact="该环节流失会减少进入后续成交阶段的用户规模。",
                confidence="high",
            ),
            KeyIssue(
                issue="渠道规模与成交效率存在差异",
                evidence=[
                    ReportEvidence(
                        text=(
                            f"{largest_name}注册用户 "
                            f"{_display(largest_metrics.user_counts.registered_users, 'count')}"
                        ),
                        evidence_ref=[largest_ref],
                    ),
                    ReportEvidence(
                        text=(
                            f"{quality_name}成交率 "
                            f"{_display(quality_metrics.conversion_rates.paid_rate, 'ratio')}"
                        ),
                        evidence_ref=[quality_ref],
                    ),
                ],
                impact="规模渠道与高效率渠道需要采用不同的优化顺序。",
                confidence="high",
            ),
        ],
        priority_actions=[
            PriorityAction(
                action=(
                    f"建议验证{previous_stage.label}到{bottleneck.label}的页面信息、"
                    "操作路径和触达时机，减少主要流失节点的阻力。"
                ),
                applicable_to=f"{previous_stage.label}→{bottleneck.label}",
                reason="该阶段已被后端漏斗分析识别为主要损耗点。",
                target_metric=f"{previous_stage.label}→{bottleneck.label}阶段转化率",
            ),
            PriorityAction(
                action=f"建议验证{quality_name}扩大有效流量后成交效率是否稳定。",
                applicable_to=quality_name,
                reason="该渠道当前成交效率相对突出，适合小范围验证扩量。",
                target_metric=f"{quality_name}成交用户数",
            ),
        ],
        opportunities=[
            GrowthOpportunity(
                target=quality_name,
                evidence=[
                    ReportEvidence(
                        text=(
                            f"成交率 "
                            f"{_display(quality_metrics.conversion_rates.paid_rate, 'ratio')}"
                        ),
                        evidence_ref=[quality_ref],
                    )
                ],
                recommendation="建议验证分批增加有效流量后，成交率能否保持稳定。",
            )
        ],
        limitations=[
            "诊断仅基于后端已验证的用户漏斗、渠道和收入汇总结果。"
        ],
    )


def _build_mock_aggregate_report(
    request: AIReportRequest,
) -> AIReportResponse:
    analysis = _require(request.aggregate_analysis, "aggregate_analysis")
    facts = {fact.reference: fact for fact in _build_evidence_catalog(request)}
    selected_insights = analysis.business_insights[:3]
    issues: list[KeyIssue] = []
    actions: list[PriorityAction] = []
    for insight in selected_insights:
        refs = [
            f"aggregate.business_insights[{analysis.business_insights.index(insight)}]"
            f".key_evidence[{index}]"
            for index, _ in enumerate(insight.key_evidence[:2])
        ]
        evidence = [
            ReportEvidence(
                text=facts[reference].display_value,
                evidence_ref=[reference],
            )
            for reference in refs
            if reference in facts
        ]
        if not evidence:
            continue
        issues.append(
            KeyIssue(
                issue=insight.core_judgement.rstrip("。"),
                evidence=evidence,
                impact=_aggregate_impact_text(insight.priority),
                confidence=(
                    "high"
                    if insight.priority in {"high_priority", "attention"}
                    else "medium"
                ),
            )
        )
        diagnosis = next(
            (
                item
                for item in analysis.dimension_funnel_diagnostics
                if item.dimension_value == insight.dimension_value
            ),
            None,
        )
        target_metric = "支付转化率"
        applicable_to = insight.dimension_value
        if diagnosis and diagnosis.largest_declining_stage:
            movement = diagnosis.largest_declining_stage
            stage_name = f"{movement.from_label}→{movement.to_label}"
            target_metric = f"{stage_name}阶段转化率"
            applicable_to = f"{insight.dimension_value} · {stage_name}"
        actions.append(
            PriorityAction(
                action=(
                    f"建议验证{applicable_to}的信息表达、操作路径和权益说明，"
                    "优先排查后端诊断指出的主要拖累环节。"
                ),
                applicable_to=applicable_to,
                reason="该动作与后端已生成的重点经营洞察直接对应。",
                target_metric=target_metric,
            )
        )

    opportunities: list[GrowthOpportunity] = []
    for opportunity_index, opportunity in enumerate(analysis.opportunities[:2]):
        reference = (
            f"aggregate.opportunities[{opportunity_index}].evidence"
        )
        fact = facts.get(reference)
        if fact is None:
            continue
        opportunities.append(
            GrowthOpportunity(
                target=opportunity.dimension_value,
                evidence=[
                    ReportEvidence(
                        text=fact.display_value,
                        evidence_ref=[reference],
                    )
                ],
                recommendation=(
                    f"建议验证{opportunity.dimension_value}扩大有效流量或复用改善链路后，"
                    "核心转化是否保持稳定。"
                ),
            )
        )
    used_opportunity_targets = {item.target for item in opportunities}
    for insight_index, insight in enumerate(analysis.business_insights):
        if (
            len(opportunities) >= 2
            or insight.dimension_value in used_opportunity_targets
            or not insight.positive_signal
        ):
            continue
        reference = (
            f"aggregate.business_insights[{insight_index}].positive_signal"
        )
        fact = facts.get(reference)
        if fact is None:
            continue
        opportunities.append(
            GrowthOpportunity(
                target=insight.dimension_value,
                evidence=[
                    ReportEvidence(
                        text=fact.display_value,
                        evidence_ref=[reference],
                    )
                ],
                recommendation=(
                    f"建议验证{insight.dimension_value}复用当前改善路径或扩大有效流量后，"
                    "最终支付转化是否保持稳定。"
                ),
            )
        )
        used_opportunity_targets.add(insight.dimension_value)

    if selected_insights:
        primary = selected_insights[0]
        secondary = selected_insights[1] if len(selected_insights) > 1 else None
        core_conclusion = (
            f"{primary.dimension_value}当前最值得优先关注：{primary.core_judgement}"
        )
        if secondary:
            core_conclusion += (
                f"同时，{secondary.dimension_value}{secondary.core_judgement}"
            )
        core_conclusion += "建议先处理主要拖累节点，再验证改善品类的扩量空间。"
    else:
        dimension_label = (
            analysis.dimensions[0].label if analysis.dimensions else "业务维度"
        )
        core_conclusion = (
            f"当前{dimension_label}报表已完成结构化分析，但高置信度经营信号有限；"
            "建议优先核对可用的转化趋势和漏斗节点，再安排优化验证。"
        )

    limitations = _aggregate_limitations(analysis)
    if not limitations:
        limitations = ["诊断仅使用后端已验证的聚合经营分析结果。"]
    return AIReportResponse(
        core_conclusion=core_conclusion,
        key_issues=issues[:3],
        priority_actions=actions[:3],
        opportunities=opportunities[:2],
        limitations=limitations[:5],
    )


def _build_diagnostic_context(request: AIReportRequest) -> dict[str, Any]:
    if request.dataset_type == "user_level":
        return {
            "dataset_type": "user_level",
            "analysis_context": _require(
                request.analysis_context,
                "analysis_context",
            ).model_dump(mode="json"),
            "schema_mapping": _require(
                request.schema_mapping,
                "schema_mapping",
            ).model_dump(mode="json"),
            "data_quality": _require(
                request.data_quality,
                "data_quality",
            ).model_dump(mode="json"),
            "metrics": _require(request.metrics, "metrics").model_dump(
                mode="json"
            ),
            "funnel": _require(request.funnel, "funnel").model_dump(
                mode="json"
            ),
            "channels": {
                channel: metrics.model_dump(mode="json")
                for channel, metrics in _require(
                    request.channels,
                    "channels",
                ).items()
            },
        }

    analysis = _require(request.aggregate_analysis, "aggregate_analysis")
    selected_values = _select_aggregate_dimension_values(analysis)
    performances = [
        item.model_dump(mode="json")
        for item in analysis.dimension_performance
        if item.dimension_value in selected_values
    ]
    diagnoses = [
        item.model_dump(mode="json")
        for item in analysis.dimension_funnel_diagnostics
        if item.dimension_value in selected_values
    ]
    return {
        "dataset_type": "aggregate_metrics",
        "analysis_status": analysis.analysis_status,
        "report_period": analysis.dataset.report_period,
        "filters": analysis.dataset.filters,
        "dimension": (
            {
                "label": analysis.dimensions[0].label,
                "semantic_key": analysis.dimensions[0].semantic_key,
            }
            if analysis.dimensions
            else None
        ),
        "kpis": [item.model_dump(mode="json") for item in analysis.kpis],
        "dimension_performance": performances,
        "dimension_diagnosis": diagnoses,
        "business_insights": [
            item.model_dump(mode="json")
            for item in analysis.business_insights[:5]
        ],
        "funnel_summary": analysis.funnel.model_dump(mode="json"),
        "detected_anomalies": [
            item.model_dump(mode="json")
            for item in analysis.diagnostics[:10]
        ],
        "detected_opportunities": [
            item.model_dump(mode="json")
            for item in analysis.opportunities[:5]
        ],
        "data_limitations": _aggregate_limitations(analysis),
    }


def _select_aggregate_dimension_values(analysis) -> set[str]:
    ordered_values: list[str] = []
    for insight in analysis.business_insights:
        if insight.dimension_value not in ordered_values:
            ordered_values.append(insight.dimension_value)
    ranked_performance = sorted(
        analysis.dimension_performance,
        key=lambda item: item.traffic_users or 0,
        reverse=True,
    )
    for item in ranked_performance:
        if item.dimension_value not in ordered_values:
            ordered_values.append(item.dimension_value)
    return set(ordered_values[:MAX_AGGREGATE_DIMENSIONS])


def _aggregate_limitations(analysis) -> list[str]:
    limitations = list(dict.fromkeys(analysis.data_quality.warnings))
    if not analysis.data_quality.total_row_detected:
        limitations.append(
            "当前报表未提供可安全汇总的整体口径，诊断以维度表现为主。"
        )
    if analysis.analysis_status == "partial":
        limitations.append("部分字段或表格结构未达到可靠识别阈值。")
    if len(analysis.dimension_performance) > MAX_AGGREGATE_DIMENSIONS:
        limitations.append(
            f"AI 上下文仅保留优先级最高或流量最大的 "
            f"{MAX_AGGREGATE_DIMENSIONS} 个维度值。"
        )
    return list(dict.fromkeys(limitations))


def _build_evidence_catalog(request: AIReportRequest) -> list[EvidenceFact]:
    if request.dataset_type == "aggregate_metrics":
        return _build_aggregate_evidence_catalog(
            _require(request.aggregate_analysis, "aggregate_analysis")
        )
    return _build_user_evidence_catalog(request)


def _build_user_evidence_catalog(
    request: AIReportRequest,
) -> list[EvidenceFact]:
    metrics = _require(request.metrics, "metrics")
    funnel = _require(request.funnel, "funnel")
    channels = _require(request.channels, "channels")
    facts: list[EvidenceFact] = []
    _append_growth_metric_facts(
        facts,
        "user_level.metrics",
        "整体",
        metrics,
    )
    for index, stage in enumerate(funnel.stages):
        prefix = f"user_level.funnel.stages[{index}]"
        facts.extend(
            [
                _fact(prefix + ".user_count", stage.label, stage.user_count, "count"),
                _fact(
                    prefix + ".conversion_rate",
                    f"{stage.label}阶段转化率",
                    stage.conversion_rate_from_previous,
                    "ratio",
                ),
                _fact(
                    prefix + ".dropoff_count",
                    f"{stage.label}阶段流失用户",
                    stage.dropoff_count,
                    "count",
                ),
            ]
        )
    for channel, channel_metrics in channels.items():
        _append_growth_metric_facts(
            facts,
            f"user_level.channels.{channel}",
            channel,
            channel_metrics,
        )
    return facts


def _append_growth_metric_facts(
    facts: list[EvidenceFact],
    prefix: str,
    label_prefix: str,
    metrics: GrowthMetrics,
) -> None:
    count_fields = {
        "registered_users": "注册用户",
        "viewed_users": "浏览用户",
        "lead_users": "留资用户",
        "appointment_users": "预约用户",
        "visit_users": "到店用户",
        "paid_users": "成交用户",
    }
    for field_name, label in count_fields.items():
        value = getattr(metrics.user_counts, field_name)
        if value is not None:
            facts.append(
                _fact(
                    f"{prefix}.{field_name}",
                    f"{label_prefix}{label}",
                    value,
                    "count",
                )
            )
    rate_fields = {
        "view_rate": "浏览率",
        "lead_rate": "留资率",
        "appointment_rate": "预约率",
        "visit_rate": "到店率",
        "paid_rate": "成交率",
    }
    for field_name, label in rate_fields.items():
        value = getattr(metrics.conversion_rates, field_name)
        if value is not None:
            facts.append(
                _fact(
                    f"{prefix}.{field_name}",
                    f"{label_prefix}{label}",
                    value,
                    "ratio",
                )
            )
    facts.extend(
        [
            _fact(
                f"{prefix}.gmv",
                f"{label_prefix}GMV",
                metrics.revenue.gmv,
                "currency",
            ),
            _fact(
                f"{prefix}.average_order_value",
                f"{label_prefix}客单价",
                metrics.revenue.average_order_value,
                "currency",
            ),
        ]
    )


def _build_aggregate_evidence_catalog(analysis) -> list[EvidenceFact]:
    facts: list[EvidenceFact] = []
    selected_values = _select_aggregate_dimension_values(analysis)
    for index, kpi in enumerate(analysis.kpis):
        facts.append(
            _fact(
                f"aggregate.kpis[{index}].value",
                kpi.label,
                kpi.value,
                kpi.unit,
            )
        )
    for index, item in enumerate(analysis.dimension_performance):
        if item.dimension_value not in selected_values:
            continue
        prefix = f"aggregate.dimension_performance[{index}]"
        for field_name, label, unit in (
            ("traffic_users", "浏览用户", "count"),
            ("appointment_users", "预约用户", "count"),
            ("payment_users", "支付用户", "count"),
            ("conversion_rate", "支付转化率", "ratio"),
            ("gmv", "GMV", "currency"),
            ("average_order_value", "客单价", "currency"),
            ("yoy", "同比", item.yoy_unit),
            ("mom", "环比", item.mom_unit),
        ):
            value = getattr(item, field_name)
            if value is not None and unit is not None:
                facts.append(
                    _fact(
                        f"{prefix}.{field_name}",
                        f"{item.dimension_value}{label}",
                        value,
                        unit,
                    )
                )
        for outcome_index, outcome in enumerate(item.supplemental_outcomes):
            facts.append(
                _fact(
                    f"{prefix}.supplemental_outcomes[{outcome_index}]",
                    f"{item.dimension_value}{outcome.label}",
                    outcome.value,
                    outcome.unit,
                )
            )
    for index, diagnosis in enumerate(analysis.dimension_funnel_diagnostics):
        if diagnosis.dimension_value not in selected_values:
            continue
        prefix = f"aggregate.dimension_diagnosis[{index}]"
        for field_name, label, unit in (
            ("final_conversion_rate", "支付转化率", "ratio"),
            (
                "final_conversion_yoy",
                "支付转化率同比",
                diagnosis.final_conversion_yoy_unit,
            ),
            (
                "final_conversion_mom",
                "支付转化率环比",
                diagnosis.final_conversion_mom_unit,
            ),
        ):
            value = getattr(diagnosis, field_name)
            if value is not None and unit is not None:
                facts.append(
                    _fact(
                        f"{prefix}.{field_name}",
                        f"{diagnosis.dimension_value}{label}",
                        value,
                        unit,
                    )
                )
        for stage_index, stage in enumerate(diagnosis.stages):
            stage_prefix = f"{prefix}.stages[{stage_index}]"
            stage_label = f"{stage.from_label}→{stage.to_label}"
            if stage.current_conversion_rate is not None:
                facts.append(
                    _fact(
                        stage_prefix + ".current_conversion_rate",
                        f"{diagnosis.dimension_value}{stage_label}转化率",
                        stage.current_conversion_rate,
                        "ratio",
                    )
                )
            for field_name, period_label, unit in (
                ("yoy_delta", "同比", stage.yoy_unit),
                ("mom_delta", "环比", stage.mom_unit),
            ):
                value = getattr(stage, field_name)
                if value is not None and unit is not None:
                    facts.append(
                        _fact(
                            f"{stage_prefix}.{field_name}",
                            f"{diagnosis.dimension_value}{stage_label}{period_label}",
                            value,
                            unit,
                        )
                    )
    for index, insight in enumerate(analysis.business_insights[:5]):
        for field_name in ("positive_signal", "risk_signal"):
            signal = getattr(insight, field_name)
            if signal:
                facts.append(
                    EvidenceFact(
                        reference=(
                            f"aggregate.business_insights[{index}].{field_name}"
                        ),
                        label=f"{insight.dimension_value}经营信号",
                        display_value=signal,
                        unit="text",
                    )
                )
        for evidence_index, evidence in enumerate(insight.key_evidence[:2]):
            facts.append(
                EvidenceFact(
                    reference=(
                        f"aggregate.business_insights[{index}]"
                        f".key_evidence[{evidence_index}]"
                    ),
                    label=f"{insight.dimension_value}经营证据",
                    display_value=evidence,
                    unit="text",
                )
            )
    for index, diagnostic in enumerate(analysis.diagnostics[:10]):
        facts.append(
            EvidenceFact(
                reference=f"aggregate.diagnostics[{index}].evidence",
                label=diagnostic.title,
                display_value=diagnostic.evidence,
                unit="text",
            )
        )
    for index, opportunity in enumerate(analysis.opportunities[:5]):
        facts.append(
            EvidenceFact(
                reference=f"aggregate.opportunities[{index}].evidence",
                label=opportunity.title,
                display_value=opportunity.evidence,
                unit="text",
            )
        )
    return facts


def _validate_report_evidence(
    request: AIReportRequest,
    report: AIReportResponse,
) -> None:
    facts = _build_evidence_catalog(request)
    fact_lookup = {fact.reference: fact for fact in facts}
    allowed_mentions = {
        mention
        for fact in facts
        for mention in _numeric_mentions(fact.display_value)
    }
    evidence_items = [
        evidence
        for issue in report.key_issues
        for evidence in issue.evidence
    ] + [
        evidence
        for opportunity in report.opportunities
        for evidence in opportunity.evidence
    ]
    for evidence in evidence_items:
        unknown_refs = set(evidence.evidence_ref) - set(fact_lookup)
        if unknown_refs:
            raise AIReportProviderError(
                "AI 报告引用了未知 evidence_ref："
                + "、".join(sorted(unknown_refs))
            )
        referenced_mentions = {
            mention
            for reference in evidence.evidence_ref
            for mention in _numeric_mentions(
                fact_lookup[reference].display_value
            )
        }
        unsupported = (
            _numeric_mentions(evidence.text) - referenced_mentions
        )
        if unsupported:
            raise AIReportProviderError(
                "AI 报告证据中的数字与 evidence_ref 不一致。"
            )

    report_mentions = {
        mention
        for text in _report_content_texts(report)
        for mention in _numeric_mentions(text)
    }
    unsupported_report_mentions = report_mentions - allowed_mentions
    if unsupported_report_mentions:
        raise AIReportProviderError(
            "AI 报告包含后端分析结果中不存在的数字或单位。"
        )


def _report_content_texts(report: AIReportResponse) -> list[str]:
    texts = [report.core_conclusion, *report.limitations]
    for issue in report.key_issues:
        texts.extend([issue.issue, issue.impact])
        texts.extend(evidence.text for evidence in issue.evidence)
    for action in report.priority_actions:
        texts.extend(
            [
                action.action,
                action.applicable_to,
                action.reason,
                action.target_metric,
            ]
        )
    for opportunity in report.opportunities:
        texts.extend([opportunity.target, opportunity.recommendation])
        texts.extend(evidence.text for evidence in opportunity.evidence)
    return texts


def _numeric_mentions(text: str) -> set[tuple[str, str]]:
    mentions: set[tuple[str, str]] = set()
    for raw_value, raw_unit in NUMBER_PATTERN.findall(text):
        normalized = _normalize_number(raw_value)
        if normalized is None:
            continue
        unit = {
            "个百分点": "percentage_point",
            "%": "ratio",
            "人": "count",
            "元": "currency",
            "": "number",
        }[raw_unit]
        mentions.add((normalized, unit))
    return mentions


def _normalize_number(value: str) -> str | None:
    try:
        decimal_value = Decimal(value.replace(",", ""))
    except InvalidOperation:
        return None
    normalized = format(decimal_value.normalize(), "f")
    return "0" if normalized in {"-0", "+0"} else normalized


def _fact(
    reference: str,
    label: str,
    value: int | float,
    unit: str,
) -> EvidenceFact:
    return EvidenceFact(
        reference=reference,
        label=label,
        display_value=_display(value, unit),
        unit=unit,
    )


def _display(value: int | float, unit: str) -> str:
    if unit == "count":
        return f"{int(value):,} 人"
    if unit in {"ratio", "ratio_change"}:
        sign = "+" if unit == "ratio_change" and value > 0 else ""
        return f"{sign}{value * 100:.2f}%"
    if unit == "percentage_point":
        sign = "+" if value > 0 else ""
        return f"{sign}{value * 100:.2f} 个百分点"
    if unit in {"currency", "currency_per_order"}:
        return f"¥{value:,.2f}"
    if unit == "absolute_change":
        sign = "+" if value > 0 else ""
        return f"{sign}{value:,.2f}"
    return f"{value}"


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


def _aggregate_impact_text(priority: str) -> str:
    if priority == "high_priority":
        return "该问题同时具有明显变化幅度和较高业务影响，应优先处理。"
    if priority == "attention":
        return "该信号可能继续影响后续支付转化，需要优先关注。"
    if priority == "improving":
        return "该改善信号可用于验证有效路径，并评估是否能够扩大规模。"
    return "当前变化相对稳定，可持续观察并避免局部节点转弱。"


def _require(value, field_name: str):
    if value is None:
        raise AIReportProviderError(f"AI 报告输入缺少 {field_name}。")
    return value
