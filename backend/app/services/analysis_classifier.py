import json
import logging
from typing import Any, Protocol

from pydantic import ValidationError

from app.core.config import settings
from app.schemas.analysis_context import AnalysisContext, AnalysisType


logger = logging.getLogger(__name__)


METRIC_CATALOG: dict[AnalysisType, tuple[str, ...]] = {
    "user_growth": (
        "注册用户数",
        "浏览率",
        "留资率",
        "预约率",
        "到店率",
        "成交率",
        "GMV",
        "客单价",
    ),
    "ecommerce_conversion": (
        "访客数",
        "商品浏览率",
        "加购率",
        "下单转化率",
        "支付转化率",
        "GMV",
        "客单价",
    ),
    "content_growth": (
        "内容曝光量",
        "内容浏览量",
        "互动率",
        "关注转化率",
        "内容发布量",
    ),
}

DEFAULT_ANALYSIS_CONTEXT = AnalysisContext(
    analysis_type="user_growth",
    business_type="general",
    recommended_metrics=list(METRIC_CATALOG["user_growth"]),
)


CLASSIFIER_SYSTEM_PROMPT = (
    f"""你是 GrowthLens AI 的数据分析场景分类器。

你只能根据输入的字段映射与 Excel 字段名称判断最适合的分析类型。

支持的 analysis_type：
- user_growth：用户注册、访问、留资、预约、到店、
  支付等用户增长漏斗
- ecommerce_conversion：商品浏览、加购、下单、
  支付等电商转化漏斗
- content_growth：内容曝光、阅读、互动、关注、发布等内容增长

支持的 business_type：general、local_service、ecommerce、content。

推荐指标只能从对应目录中选择：
{json.dumps(METRIC_CATALOG, ensure_ascii=False, indent=2)}

只输出合法 JSON：
{{
  "analysis_type": "user_growth | ecommerce_conversion | content_growth",
  "business_type": "general | local_service | ecommerce | content",
  "recommended_metrics": ["指标名称"]
}}

约束：
1. 只能依据输入字段，不得虚构业务背景。
2. 无法确定时返回 analysis_type=user_growth、business_type=general。
3. 不输出 Markdown、代码块或 JSON 之外的解释。
"""
)


class AnalysisClassifierError(RuntimeError):
    """Raised when an AI classification response cannot be used."""


class AnalysisClassifierProvider(Protocol):
    name: str

    def classify(
        self,
        schema_mapping: dict[str, Any],
        columns: list[str],
    ) -> dict[str, Any]:
        """Return a raw structured classification response."""


def classify_analysis_context(
    schema_mapping: dict[str, Any],
    columns: list[str] | tuple[str, ...],
    *,
    provider: AnalysisClassifierProvider | None = None,
) -> AnalysisContext:
    """Classify the dataset without making analysis availability depend on AI."""
    normalized_columns = _normalize_columns(columns)
    try:
        active_provider = provider or get_analysis_classifier_provider()
        raw_result = active_provider.classify(
            schema_mapping,
            normalized_columns,
        )
        return _validate_classifier_result(raw_result)
    except Exception as exc:
        logger.warning(
            "分析类型识别失败，回退 user_growth：%r",
            exc,
            exc_info=True,
        )
        return DEFAULT_ANALYSIS_CONTEXT.model_copy(deep=True)


def get_analysis_classifier_provider() -> AnalysisClassifierProvider:
    if settings.ai_provider != "deepseek":
        raise AnalysisClassifierError(
            "分析类型识别当前仅支持 AI_PROVIDER=deepseek。"
        )
    return DeepSeekAnalysisClassifierProvider(
        api_key=settings.deepseek_api_key,
        model=settings.ai_model,
    )


class DeepSeekAnalysisClassifierProvider:
    name = "deepseek"

    def __init__(
        self,
        *,
        api_key: str | None,
        model: str,
        client: Any | None = None,
    ) -> None:
        if not api_key:
            raise AnalysisClassifierError(
                "未配置 DEEPSEEK_API_KEY，无法执行分析类型识别。"
            )
        if not model:
            raise AnalysisClassifierError(
                "未配置 AI_MODEL，无法执行分析类型识别。"
            )

        self.model = model
        self.base_url = "https://api.deepseek.com"
        self._client = client or _create_deepseek_client(api_key)

    def classify(
        self,
        schema_mapping: dict[str, Any],
        columns: list[str],
    ) -> dict[str, Any]:
        model_input = {
            "schema_mapping": schema_mapping,
            "columns": columns,
        }
        try:
            completion = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": CLASSIFIER_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": json.dumps(
                            model_input,
                            ensure_ascii=False,
                            separators=(",", ":"),
                        ),
                    },
                ],
                response_format={"type": "json_object"},
                max_tokens=800,
                stream=False,
                extra_body={"thinking": {"type": "disabled"}},
            )
        except Exception as exc:
            raise AnalysisClassifierError(
                "DeepSeek 分析类型识别调用失败。"
            ) from exc

        try:
            content = completion.choices[0].message.content
        except (AttributeError, IndexError, TypeError) as exc:
            raise AnalysisClassifierError(
                "DeepSeek 分析类型识别返回了无法解析的响应。"
            ) from exc

        if not content or not content.strip():
            raise AnalysisClassifierError(
                "DeepSeek 分析类型识别返回了空结果。"
            )

        try:
            payload = json.loads(content)
        except (json.JSONDecodeError, TypeError) as exc:
            raise AnalysisClassifierError(
                "DeepSeek 分析类型识别结果不是合法 JSON。"
            ) from exc

        if not isinstance(payload, dict):
            raise AnalysisClassifierError(
                "DeepSeek 分析类型识别结果必须是 JSON 对象。"
            )
        return payload


def _create_deepseek_client(api_key: str) -> Any:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise AnalysisClassifierError(
            "缺少 openai SDK，请先安装 backend/requirements.txt。"
        ) from exc

    return OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
        max_retries=1,
        timeout=30.0,
    )


def _validate_classifier_result(raw_result: dict[str, Any]) -> AnalysisContext:
    try:
        result = AnalysisContext.model_validate(raw_result)
    except ValidationError as exc:
        raise AnalysisClassifierError(
            "DeepSeek 分析类型识别结果不符合约定结构。"
        ) from exc

    allowed_metrics = set(METRIC_CATALOG[result.analysis_type])
    recommended_metrics = [
        metric
        for metric in dict.fromkeys(result.recommended_metrics)
        if metric in allowed_metrics
    ]
    if not recommended_metrics:
        recommended_metrics = list(METRIC_CATALOG[result.analysis_type])

    return result.model_copy(
        update={"recommended_metrics": recommended_metrics}
    )


def _normalize_columns(columns: list[str] | tuple[str, ...]) -> list[str]:
    normalized: list[str] = []
    for column in columns:
        value = str(column).strip()
        if value and value not in normalized:
            normalized.append(value)
    return normalized
