import json
import logging
from typing import Any, Protocol

from pydantic import ValidationError

from app.core.config import settings
from app.schemas.ai_report import (
    AIReportRequest,
    AIReportResponse,
    ChannelStrategy,
    GrowthAction,
    KeyFinding,
)
from app.schemas.analysis import FunnelStage, GrowthMetrics


logger = logging.getLogger(__name__)


REPORT_JSON_EXAMPLE = {
    "summary": "基于完整分析上下文的一句话业务诊断",
    "key_findings": [
        {
            "issue": "需要优先解决的增长问题",
            "evidence": "输入指标、漏斗或渠道结果中的数据依据",
            "recommendation": "与问题和证据直接对应的建议",
        },
        {
            "issue": "第二个增长问题",
            "evidence": "可追溯的数据依据",
            "recommendation": "需要通过实验验证的建议",
        },
    ],
    "channel_strategy": [
        {
            "channel": "输入中真实存在的渠道名",
            "diagnosis": "该渠道的规模、转化和收入表现诊断",
            "strategy": "针对该渠道的差异化策略",
        }
    ],
    "growth_actions": [
        {
            "action": "可执行增长动作",
            "target_metric": "目标指标",
            "expected_direction": "increase",
        },
        {
            "action": "第二个可执行增长动作",
            "target_metric": "目标指标",
            "expected_direction": "maintain",
        },
    ],
}


SYSTEM_PROMPT = f"""你是 GrowthLens AI，一名负责业务诊断的增长分析顾问。

你只能基于用户消息中的 analysis_context、schema_mapping、data_quality、metrics、funnel、channels 生成报告。
analysis_context 用于确定分析类型、业务类型和优先指标；schema_mapping 只用于理解字段语义；
metrics、funnel、channels 是所有诊断证据和建议的事实来源。

输出要求：
1. 只输出一个合法 JSON 对象，不要输出 Markdown、代码块或额外说明。
2. summary 用一句话给出与 analysis_context 一致的整体业务诊断。
3. key_findings 输出 2-3 条，每条严格包含 issue、evidence、recommendation。
4. evidence 必须引用输入中的实际指标或漏斗结果，建议必须与该证据直接对应。
5. channel_strategy 只能引用输入 channels 中存在的渠道，并体现渠道之间的规模、转化或收入差异。
6. growth_actions 输出 2-3 条可执行建议，并标明目标指标与预期方向。

JSON 结构示例（仅表示字段结构，不是可引用的业务事实）：
{json.dumps(REPORT_JSON_EXAMPLE, ensure_ascii=False, indent=2)}

事实约束：
- 不得使用输入之外的数字、渠道、用户画像、行业基准或业务事件。
- evidence 中的数字必须能在输入数据中找到。
- 不得把原因假设写成事实；需要解释原因时，必须使用“可能”“推测”或“假设”等措辞。
- 数据完整度或样本量不足时，只能给出验证建议，不得形成确定性判断。
- recommended_metrics 只能指导报告关注重点，不能被当作已计算的指标值。
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
        "请根据以下完整分析上下文生成业务诊断报告。"
        "不要补充输入之外的事实，只返回 JSON：\n"
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
                max_tokens=2500,
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
        metrics = request.metrics
        findings = _build_key_findings(
            bottleneck,
            previous_stage,
            highest_quality,
            largest_channel,
        )
        channel_strategy = _build_channel_strategy(
            highest_quality,
            largest_channel,
        )
        actions = _build_growth_actions(
            bottleneck,
            previous_stage,
            highest_quality,
            largest_channel,
        )
        analysis_label = _analysis_type_label(
            request.analysis_context.analysis_type
        )

        return AIReportResponse(
            summary=(
                f"本次{analysis_label}显示，{metrics.user_counts.registered_users} 名注册用户形成 "
                f"{metrics.user_counts.paid_users} 名成交用户和 "
                f"{_currency(metrics.revenue.gmv)} GMV，"
                f"当前首要优化点是{previous_stage.label}到{bottleneck.label}的转化承接。"
            ),
            key_findings=findings,
            channel_strategy=channel_strategy,
            growth_actions=actions,
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


def _build_key_findings(
    bottleneck: FunnelStage,
    previous_stage: FunnelStage,
    quality: tuple[str, GrowthMetrics],
    largest: tuple[str, GrowthMetrics],
) -> list[KeyFinding]:
    largest_name, largest_metrics = largest
    quality_name, quality_metrics = quality
    findings = [
        KeyFinding(
            issue=f"{previous_stage.label}到{bottleneck.label}是主要漏斗损耗点",
            evidence=(
                f"{previous_stage.label}阶段 {previous_stage.user_count} 人，"
                f"{bottleneck.label}阶段 {bottleneck.user_count} 人，"
                f"流失 {bottleneck.dropoff_count} 人，阶段转化率 "
                f"{_percent(bottleneck.conversion_rate_from_previous)}。"
            ),
            recommendation=(
                f"优先复盘{previous_stage.label}到{bottleneck.label}的页面路径和运营触达，"
                "用小流量实验验证承接改动。"
            ),
        ),
        KeyFinding(
            issue=(
                "渠道规模与成交效率存在差异"
                if largest_name != quality_name
                else "头部渠道同时承载主要规模与成交效率"
            ),
            evidence=(
                f"{largest_name}注册用户 {largest_metrics.user_counts.registered_users} 人，"
                f"成交率 {_percent(largest_metrics.conversion_rates.paid_rate)}；"
                f"{quality_name}成交率 {_percent(quality_metrics.conversion_rates.paid_rate)}，"
                f"成交用户 {quality_metrics.user_counts.paid_users} 人。"
            ),
            recommendation=(
                f"分别用{largest_name}验证规模渠道的漏斗优化，"
                f"用{quality_name}验证高质量流量扩量后成交率是否稳定。"
            ),
        )
    ]
    return findings


def _build_channel_strategy(
    quality: tuple[str, GrowthMetrics],
    largest: tuple[str, GrowthMetrics],
) -> list[ChannelStrategy]:
    quality_name, quality_metrics = quality
    largest_name, largest_metrics = largest
    strategies = [
        ChannelStrategy(
            channel=largest_name,
            diagnosis=(
                f"注册用户 {largest_metrics.user_counts.registered_users} 人，"
                f"成交率 {_percent(largest_metrics.conversion_rates.paid_rate)}，"
                f"GMV {_currency(largest_metrics.revenue.gmv)}。"
            ),
            strategy=(
                "优先优化高流量用户从预约到成交的承接效率，"
                "并以阶段转化率作为实验判断指标。"
            ),
        )
    ]
    if quality_name != largest_name:
        strategies.append(
            ChannelStrategy(
                channel=quality_name,
                diagnosis=(
                    f"注册用户 {quality_metrics.user_counts.registered_users} 人，"
                    f"成交率 {_percent(quality_metrics.conversion_rates.paid_rate)}，"
                    f"GMV {_currency(quality_metrics.revenue.gmv)}。"
                ),
                strategy=(
                    "保留当前高成交效率，分批扩大有效流量，"
                    "持续观察成交率和成交用户数是否同步改善。"
                ),
            )
        )
    return strategies


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


def _validate_report_channels(
    report: AIReportResponse,
    allowed_channels: set[str],
) -> None:
    reported_channels = {
        strategy.channel
        for strategy in report.channel_strategy
    }
    unknown_channels = reported_channels - allowed_channels
    if unknown_channels:
        names = "、".join(sorted(unknown_channels))
        raise AIReportProviderError(f"AI 报告引用了未知渠道：{names}")


def _analysis_type_label(analysis_type: str) -> str:
    labels = {
        "user_growth": "用户增长分析",
        "ecommerce_conversion": "电商转化分析",
        "content_growth": "内容增长分析",
    }
    return labels.get(analysis_type, "用户增长分析")


def _percent(value: float) -> str:
    return f"{value * 100:.2f}%"


def _currency(value: float) -> str:
    return f"¥{value:,.2f}"
