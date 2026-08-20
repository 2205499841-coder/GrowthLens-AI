from collections import Counter
from statistics import median

from app.schemas.aggregate_analysis import (
    DimensionFunnelDiagnosis,
    DimensionPerformance,
)
from app.schemas.cross_metric_diagnosis import (
    BottleneckDiagnosis,
    CrossMetricDiagnosis,
    CrossMetricSummary,
    DiagnosisSignal,
    FunnelStageDiagnosisContext,
    MetricDiagnosisContext,
    OutcomeMetricContext,
    PriorityFactors,
)
from app.schemas.growth_attribution import DimensionGrowthAttribution


SCALE_THRESHOLD = 0.02
RATE_PP_THRESHOLD = 0.005
RATE_RATIO_THRESHOLD = 0.02


def build_cross_metric_diagnoses(
    dimension_performance: list[DimensionPerformance],
    dimension_diagnosis: list[DimensionFunnelDiagnosis],
    growth_attribution: list[DimensionGrowthAttribution],
) -> list[CrossMetricDiagnosis]:
    diagnosis_lookup = {
        item.dimension_value: (index, item)
        for index, item in enumerate(dimension_diagnosis)
    }
    attribution_lookup = {
        item.dimension_value: (index, item)
        for index, item in enumerate(growth_attribution)
    }
    stage_medians = _stage_medians(dimension_diagnosis)
    conversion_values = [
        item.conversion_rate
        for item in dimension_performance
        if item.conversion_rate is not None
    ]
    conversion_median = median(conversion_values) if conversion_values else None
    conversion_rank = {
        item.dimension_value: rank
        for rank, item in enumerate(
            sorted(
                (
                    item
                    for item in dimension_performance
                    if item.conversion_rate is not None
                ),
                key=lambda item: item.conversion_rate or 0,
                reverse=True,
            ),
            start=1,
        )
    }
    traffic_values = [
        item.traffic_users
        for item in dimension_performance
        if item.traffic_users is not None
    ]
    payment_values = [
        item.payment_users
        for item in dimension_performance
        if item.payment_users is not None
    ]
    max_traffic = max(traffic_values, default=0)
    max_payment = max(payment_values, default=0)
    traffic_median = median(traffic_values) if traffic_values else None

    results = [
        _diagnose_dimension(
            performance_index=index,
            performance=performance,
            diagnosis_entry=diagnosis_lookup.get(performance.dimension_value),
            attribution_entry=attribution_lookup.get(performance.dimension_value),
            stage_medians=stage_medians,
            conversion_median=conversion_median,
            conversion_rank=conversion_rank.get(performance.dimension_value),
            traffic_median=traffic_median,
            max_traffic=max_traffic,
            max_payment=max_payment,
        )
        for index, performance in enumerate(dimension_performance)
    ]
    return sorted(results, key=lambda item: item.priority_score, reverse=True)


def build_cross_metric_summary(
    diagnoses: list[CrossMetricDiagnosis],
    *,
    has_safe_overall_scope: bool,
) -> CrossMetricSummary:
    top = diagnoses[:3]
    drivers = [
        item.attribution_driver
        for item in top
        if item.attribution_driver not in {"mixed", "unavailable"}
    ]
    bottlenecks = [
        item.primary_bottleneck.stage
        for item in diagnoses
        if item.primary_bottleneck is not None
    ]
    return CrossMetricSummary(
        scope=("safe_overall" if has_safe_overall_scope else "dimension_only"),
        top_priority_dimensions=[item.dimension_value for item in top],
        dominant_growth_driver=(
            Counter(drivers).most_common(1)[0][0] if drivers else "unavailable"
        ),
        common_bottleneck=(
            Counter(bottlenecks).most_common(1)[0][0]
            if bottlenecks
            else None
        ),
        dimension_count=len(diagnoses),
    )


def _diagnose_dimension(
    *,
    performance_index: int,
    performance: DimensionPerformance,
    diagnosis_entry: tuple[int, DimensionFunnelDiagnosis] | None,
    attribution_entry: tuple[int, DimensionGrowthAttribution] | None,
    stage_medians: dict[tuple[str, str], float],
    conversion_median: float | None,
    conversion_rank: int | None,
    traffic_median: float | None,
    max_traffic: int,
    max_payment: int,
) -> CrossMetricDiagnosis:
    diagnosis_index, diagnosis = (
        diagnosis_entry if diagnosis_entry else (-1, None)
    )
    _, attribution = (
        attribution_entry if attribution_entry else (-1, None)
    )
    scale_changes = {
        item.metric_key: (index, item)
        for index, item in enumerate(performance.scale_changes)
    }
    traffic = _scale_metric_context(
        performance_index,
        "traffic_users",
        "浏览用户",
        performance.traffic_users,
        scale_changes.get("traffic_users"),
    )
    booking = _scale_metric_context(
        performance_index,
        "appointment_users",
        "预约用户",
        performance.appointment_users,
        scale_changes.get("appointment_users"),
    )
    payment = _scale_metric_context(
        performance_index,
        "payment_users",
        "支付用户",
        performance.payment_users,
        scale_changes.get("payment_users"),
    )
    if attribution:
        scale_analysis = attribution.user_scale_analysis
        traffic = traffic.model_copy(
            update={"trend": scale_analysis.traffic_trend}
        )
        booking = booking.model_copy(
            update={"trend": scale_analysis.booking_user_trend}
        )
        payment = payment.model_copy(
            update={"trend": scale_analysis.payment_user_trend}
        )
    conversion = _conversion_context(
        diagnosis_index,
        performance.conversion_rate,
        diagnosis,
        conversion_median,
        conversion_rank,
    )
    funnel = _funnel_context(diagnosis_index, diagnosis, stage_medians)
    bottleneck = _primary_bottleneck(funnel)
    driver = attribution.growth_driver if attribution else "unavailable"
    driver_explanation = (
        attribution.driver_explanation
        if attribution
        else "规模或转化比较数据不足，暂无法可靠判断增长来源。"
    )
    patterns = _diagnosis_patterns(
        traffic=traffic,
        payment=payment,
        conversion=conversion,
        funnel=funnel,
        bottleneck=bottleneck,
        conversion_median=conversion_median,
        traffic_median=traffic_median,
    )
    secondary_signal = _secondary_signal(
        patterns,
        traffic,
        payment,
        conversion,
        bottleneck,
    )
    outcome_metrics = _outcome_metrics(performance_index, performance)
    factors = _priority_factors(
        traffic,
        payment,
        conversion,
        bottleneck,
        patterns,
        performance.traffic_users,
        performance.payment_users,
        max_traffic,
        max_payment,
    )
    score = round(min(sum(factors.model_dump().values()), 100), 2)
    if "traffic_up_conversion_up" in patterns and not _has_negative_pattern(patterns):
        score = min(score, 30)

    evidence_refs = list(
        dict.fromkeys(
            [
                *traffic.evidence_refs,
                *booking.evidence_refs,
                *payment.evidence_refs,
                *conversion.evidence_refs,
                *(bottleneck.evidence_refs if bottleneck else []),
            ]
        )
    )
    limitations = []
    if traffic.yoy_change is None:
        limitations.append("缺少浏览用户同比，流量方向不参与确定性模式判断。")
    if payment.yoy_change is None:
        limitations.append("缺少支付用户同比，支付规模变化仅保留本期结果。")
    if diagnosis is None:
        limitations.append("缺少可用维度漏斗诊断。")

    return CrossMetricDiagnosis(
        dimension_value=performance.dimension_value,
        business_state=_business_state(patterns, driver),
        outcome_state=_outcome_state(payment, conversion),
        traffic_state=_metric_state("浏览用户", traffic),
        conversion_state=_metric_state("支付转化率", conversion),
        payment_state=_metric_state("支付用户", payment),
        traffic=traffic,
        booking=booking,
        payment=payment,
        conversion=conversion,
        funnel=funnel,
        attribution_driver=driver,
        driver_explanation=driver_explanation,
        primary_bottleneck=bottleneck,
        secondary_signal=secondary_signal,
        diagnosis_patterns=patterns,
        outcome_metrics=outcome_metrics,
        priority_score=score,
        priority_level="high" if score >= 60 else "medium" if score >= 35 else "low",
        priority_factors=factors,
        evidence_refs=evidence_refs,
        limitations=limitations,
    )


def _scale_metric_context(
    performance_index: int,
    metric_key: str,
    label: str,
    current_value: int | None,
    change_entry,
) -> MetricDiagnosisContext:
    change_index, change = change_entry if change_entry else (-1, None)
    yoy, yoy_unit = _normalized_scale_change(change, "yoy")
    mom, mom_unit = _normalized_scale_change(change, "mom")
    refs = []
    prefix = f"aggregate.dimension_performance[{performance_index}]"
    if current_value is not None:
        refs.append(f"{prefix}.{_performance_field(metric_key)}")
    if yoy is not None and change_index >= 0:
        refs.append(f"{prefix}.scale_changes[{change_index}].yoy_change")
    if mom is not None and change_index >= 0:
        refs.append(f"{prefix}.scale_changes[{change_index}].mom_change")
    return MetricDiagnosisContext(
        metric_key=metric_key,
        label=label,
        current_value=current_value,
        yoy_change=yoy,
        yoy_unit=yoy_unit,
        mom_change=mom,
        mom_unit=mom_unit,
        trend=_trend(
            yoy,
            SCALE_THRESHOLD if yoy_unit == "ratio_change" else 0,
        ),
        evidence_refs=refs,
    )


def _conversion_context(
    diagnosis_index: int,
    current_value: float | None,
    diagnosis: DimensionFunnelDiagnosis | None,
    conversion_median: float | None,
    conversion_rank: int | None,
) -> MetricDiagnosisContext:
    yoy = diagnosis.final_conversion_yoy if diagnosis else None
    mom = diagnosis.final_conversion_mom if diagnosis else None
    yoy_unit = diagnosis.final_conversion_yoy_unit if diagnosis else None
    mom_unit = diagnosis.final_conversion_mom_unit if diagnosis else None
    refs = []
    if diagnosis_index >= 0:
        prefix = f"aggregate.dimension_diagnosis[{diagnosis_index}]"
        if current_value is not None:
            refs.append(f"{prefix}.final_conversion_rate")
        if yoy is not None:
            refs.append(f"{prefix}.final_conversion_yoy")
        if mom is not None:
            refs.append(f"{prefix}.final_conversion_mom")
    return MetricDiagnosisContext(
        metric_key="payment_conversion_rate",
        label="支付转化率",
        current_value=current_value,
        yoy_change=yoy,
        yoy_unit=yoy_unit,
        mom_change=mom,
        mom_unit=mom_unit,
        trend=_trend(yoy, _rate_threshold(yoy_unit)),
        evidence_refs=refs,
        peer_median_value=conversion_median,
        rank=conversion_rank,
    )


def _funnel_context(
    diagnosis_index: int,
    diagnosis: DimensionFunnelDiagnosis | None,
    stage_medians: dict[tuple[str, str], float],
) -> list[FunnelStageDiagnosisContext]:
    if diagnosis is None:
        return []
    result = []
    for stage_index, stage in enumerate(diagnosis.stages):
        key = (stage.from_metric_key, stage.to_metric_key)
        peer_median = stage_medians.get(key)
        deviation = (
            round(stage.current_conversion_rate - peer_median, 6)
            if stage.current_conversion_rate is not None and peer_median is not None
            else None
        )
        refs = []
        prefix = (
            f"aggregate.dimension_diagnosis[{diagnosis_index}]"
            f".stages[{stage_index}]"
        )
        if stage.current_conversion_rate is not None:
            refs.append(prefix + ".current_conversion_rate")
        if stage.yoy_delta is not None:
            refs.append(prefix + ".yoy_delta")
        if stage.mom_delta is not None:
            refs.append(prefix + ".mom_delta")
        score = _bottleneck_score(
            deviation,
            stage.yoy_delta,
            stage.mom_delta,
        )
        result.append(
            FunnelStageDiagnosisContext(
                **stage.model_dump(mode="json"),
                peer_median_conversion_rate=peer_median,
                deviation_from_median=deviation,
                bottleneck_score=score,
                evidence_refs=refs,
            )
        )
    return result


def _primary_bottleneck(
    funnel: list[FunnelStageDiagnosisContext],
) -> BottleneckDiagnosis | None:
    if not funnel:
        return None
    stage = max(funnel, key=lambda item: item.bottleneck_score)
    if stage.bottleneck_score <= 0:
        return None
    return BottleneckDiagnosis(
        stage=f"{stage.from_label}→{stage.to_label}",
        stage_group=_stage_group(stage.to_metric_key),
        current_conversion_rate=stage.current_conversion_rate,
        peer_median_conversion_rate=stage.peer_median_conversion_rate,
        deviation_from_median=stage.deviation_from_median,
        yoy_delta=stage.yoy_delta,
        mom_delta=stage.mom_delta,
        yoy_unit=stage.yoy_unit,
        mom_unit=stage.mom_unit,
        evidence_refs=stage.evidence_refs,
    )


def _diagnosis_patterns(
    *,
    traffic: MetricDiagnosisContext,
    payment: MetricDiagnosisContext,
    conversion: MetricDiagnosisContext,
    funnel: list[FunnelStageDiagnosisContext],
    bottleneck: BottleneckDiagnosis | None,
    conversion_median: float | None,
    traffic_median: float | None,
) -> list[str]:
    patterns = []
    traffic_trend = traffic.trend
    conversion_trend = conversion.trend
    payment_trend = payment.trend
    pair_patterns = {
        ("decline", "growth"): "traffic_down_conversion_up",
        ("growth", "decline"): "traffic_up_conversion_down",
        ("growth", "growth"): "traffic_up_conversion_up",
        ("decline", "decline"): "traffic_down_conversion_down",
    }
    pair = pair_patterns.get((traffic_trend, conversion_trend))
    if pair:
        patterns.append(pair)
    if conversion_trend == "growth" and payment_trend == "decline":
        patterns.extend(["conversion_up_payment_down", "cross_metric_contradiction"])
    if traffic_trend == "growth" and payment_trend == "stable":
        patterns.extend(["traffic_up_payment_flat", "cross_metric_contradiction"])
    if conversion_trend == "growth" and any(
        _negative(stage.yoy_delta, _rate_threshold(stage.yoy_unit))
        for stage in funnel
    ):
        patterns.append("cross_metric_contradiction")
    if (
        _positive(conversion.yoy_change, _rate_threshold(conversion.yoy_unit))
        and _negative(conversion.mom_change, _rate_threshold(conversion.mom_unit))
    ):
        patterns.extend(["yoy_up_mom_down", "cross_metric_contradiction"])
    if bottleneck:
        patterns.append(f"funnel_{bottleneck.stage_group}_loss")
    if (
        traffic.current_value is not None
        and conversion.current_value is not None
        and traffic_median is not None
        and conversion_median is not None
    ):
        if (
            traffic.current_value >= traffic_median
            and conversion.current_value < conversion_median - RATE_PP_THRESHOLD
        ):
            patterns.append("high_traffic_low_conversion")
        if (
            traffic.current_value < traffic_median * 0.7
            and conversion.current_value > conversion_median + RATE_PP_THRESHOLD
        ):
            patterns.append("low_traffic_high_conversion")
    if not patterns:
        patterns.append("mixed")
    return list(dict.fromkeys(patterns))


def _secondary_signal(
    patterns: list[str],
    traffic: MetricDiagnosisContext,
    payment: MetricDiagnosisContext,
    conversion: MetricDiagnosisContext,
    bottleneck: BottleneckDiagnosis | None,
) -> DiagnosisSignal | None:
    if "conversion_up_payment_down" in patterns:
        return DiagnosisSignal(
            signal_type="conversion_up_payment_down",
            description="转化效率改善，但支付用户仍下降，效率贡献未抵消规模压力。",
            evidence_refs=[*conversion.evidence_refs, *payment.evidence_refs],
        )
    if "traffic_up_payment_flat" in patterns:
        return DiagnosisSignal(
            signal_type="traffic_up_payment_flat",
            description="流量增长但支付规模未同步，需要优先检查中间漏斗承接。",
            evidence_refs=[*traffic.evidence_refs, *payment.evidence_refs],
        )
    if "yoy_up_mom_down" in patterns:
        return DiagnosisSignal(
            signal_type="yoy_up_mom_down",
            description="同比改善但环比转弱，存在趋势反转信号。",
            evidence_refs=conversion.evidence_refs,
        )
    if "cross_metric_contradiction" in patterns and bottleneck:
        return DiagnosisSignal(
            signal_type="funnel_contradiction",
            description="最终转化改善，但局部关键漏斗仍在恶化。",
            evidence_refs=[*conversion.evidence_refs, *bottleneck.evidence_refs],
        )
    return None


def _priority_factors(
    traffic: MetricDiagnosisContext,
    payment: MetricDiagnosisContext,
    conversion: MetricDiagnosisContext,
    bottleneck: BottleneckDiagnosis | None,
    patterns: list[str],
    traffic_value: int | None,
    payment_value: int | None,
    max_traffic: int,
    max_payment: int,
) -> PriorityFactors:
    outcome = 0.0
    if payment.trend == "decline":
        outcome += 20
    if conversion.trend == "decline":
        outcome += 5
    traffic_scale = 15 * (traffic_value or 0) / max(max_traffic, 1)
    payment_scale = 10 * (payment_value or 0) / max(max_payment, 1)
    funnel_deviation = 0.0
    if bottleneck and bottleneck.deviation_from_median is not None:
        funnel_deviation = min(
            max(-bottleneck.deviation_from_median, 0) / 0.15 * 20,
            20,
        )
    yoy_deterioration = min(
        (
            sum(
                _negative_magnitude(item.yoy_change, item.yoy_unit)
                for item in (traffic, payment, conversion)
            )
            + (
                _negative_magnitude(bottleneck.yoy_delta, bottleneck.yoy_unit)
                if bottleneck
                else 0
            )
        )
        * 40,
        10,
    )
    mom_deterioration = min(
        (
            sum(
                _negative_magnitude(item.mom_change, item.mom_unit)
                for item in (traffic, payment, conversion)
            )
            + (
                _negative_magnitude(bottleneck.mom_delta, bottleneck.mom_unit)
                if bottleneck
                else 0
            )
        )
        * 32,
        8,
    )
    contradiction = 10 if "cross_metric_contradiction" in patterns else 0
    opportunity = (
        5
        if any(
            item in patterns
            for item in (
                "traffic_up_conversion_up",
                "low_traffic_high_conversion",
            )
        )
        else 0
    )
    return PriorityFactors(
        outcome_deterioration=round(outcome, 2),
        traffic_scale=round(traffic_scale, 2),
        payment_scale=round(payment_scale, 2),
        funnel_deviation=round(funnel_deviation, 2),
        yoy_deterioration=round(yoy_deterioration, 2),
        mom_deterioration=round(mom_deterioration, 2),
        contradiction=contradiction,
        growth_opportunity=opportunity,
    )


def _outcome_metrics(
    performance_index: int,
    performance: DimensionPerformance,
) -> list[OutcomeMetricContext]:
    return [
        OutcomeMetricContext(
            metric_key=item.metric_key,
            label=item.label,
            value=item.value,
            unit=item.unit,
            evidence_ref=(
                f"aggregate.dimension_performance[{performance_index}]"
                f".supplemental_outcomes[{index}]"
            ),
        )
        for index, item in enumerate(performance.supplemental_outcomes)
    ]


def _business_state(patterns: list[str], driver: str) -> str:
    if "traffic_down_conversion_down" in patterns:
        return "流量规模和转化效率同时承压，支付结果面临双重压力。"
    if "conversion_up_payment_down" in patterns:
        return "支付规模下降伴随流量压力，转化效率改善尚未形成足够抵消。"
    if "traffic_up_payment_flat" in patterns:
        return "流量已经增长，但支付规模未同步，中间漏斗承接需要优先验证。"
    if "traffic_up_conversion_down" in patterns:
        return "流量扩大但转化效率下降，新增流量承接不足。"
    if "traffic_up_conversion_up" in patterns:
        return "流量规模与转化效率同时改善，当前呈现正向增长。"
    if "traffic_down_conversion_up" in patterns:
        return "流量下降但转化效率改善，效率贡献正在抵消部分规模压力。"
    if driver == "conversion":
        return "支付表现主要伴随转化效率改善，仍需结合局部漏斗信号判断风险。"
    if driver == "traffic":
        return "支付表现主要伴随流量规模变化，转化承接仍需结合漏斗验证。"
    if driver == "combined":
        return "流量规模与转化效率共同支撑支付表现。"
    if driver == "unavailable":
        return "比较数据不足，当前只能保留本期经营结果和漏斗信号。"
    return "多项经营信号方向不一致，暂不能形成单一增长结论。"


def _outcome_state(
    payment: MetricDiagnosisContext,
    conversion: MetricDiagnosisContext,
) -> str:
    if payment.trend == "decline":
        return "支付用户下降，是当前需要解释的核心业务结果。"
    if payment.trend == "growth":
        return "支付用户增长，需结合流量和转化判断增长来源。"
    if conversion.trend == "decline":
        return "支付转化率下降，支付效率承压。"
    if payment.trend == "unavailable":
        return "缺少支付用户同比，无法确认支付规模变化方向。"
    return "支付规模整体稳定，需关注局部漏斗和趋势变化。"


def _metric_state(label: str, context: MetricDiagnosisContext) -> str:
    return {
        "growth": f"{label}同比增长。",
        "decline": f"{label}同比下降。",
        "stable": f"{label}同比基本稳定。",
        "unavailable": f"{label}缺少可比同比数据。",
    }[context.trend]


def _stage_medians(
    diagnoses: list[DimensionFunnelDiagnosis],
) -> dict[tuple[str, str], float]:
    grouped: dict[tuple[str, str], list[float]] = {}
    for diagnosis in diagnoses:
        for stage in diagnosis.stages:
            if stage.current_conversion_rate is None:
                continue
            key = (stage.from_metric_key, stage.to_metric_key)
            grouped.setdefault(key, []).append(stage.current_conversion_rate)
    return {
        key: median(values)
        for key, values in grouped.items()
        if len(values) >= 2
    }


def _bottleneck_score(
    deviation: float | None,
    yoy: float | None,
    mom: float | None,
) -> float:
    score = max(-(deviation or 0), 0) * 100
    score += max(-(yoy or 0), 0) * 60
    score += max(-(mom or 0), 0) * 40
    return round(score, 4)


def _normalized_scale_change(change, period: str) -> tuple[float | None, str | None]:
    if change is None:
        return None, None
    value = getattr(change, f"{period}_change")
    unit = getattr(change, f"{period}_unit")
    if value is None:
        return None, None
    if unit in {"ratio_change", "absolute_change"}:
        return value, unit
    return None, None


def _performance_field(metric_key: str) -> str:
    return {
        "traffic_users": "traffic_users",
        "appointment_users": "appointment_users",
        "payment_users": "payment_users",
    }[metric_key]


def _trend(value: float | None, threshold: float) -> str:
    if value is None:
        return "unavailable"
    if value > threshold:
        return "growth"
    if value < -threshold:
        return "decline"
    return "stable"


def _rate_threshold(unit: str | None) -> float:
    return RATE_PP_THRESHOLD if unit == "percentage_point" else RATE_RATIO_THRESHOLD


def _positive(value: float | None, threshold: float) -> bool:
    return value is not None and value > threshold


def _negative(value: float | None, threshold: float) -> bool:
    return value is not None and value < -threshold


def _negative_magnitude(value: float | None, unit: str | None) -> float:
    if value is None or value >= 0:
        return 0
    return abs(value) if unit != "percentage_point" else abs(value) * 2


def _stage_group(to_metric_key: str) -> str:
    if to_metric_key in {"product_detail_users", "appointment_users"}:
        return "front"
    if to_metric_key == "payment_users":
        return "late"
    return "mid"


def _has_negative_pattern(patterns: list[str]) -> bool:
    return any(
        item in patterns
        for item in (
            "traffic_down_conversion_up",
            "traffic_up_conversion_down",
            "traffic_down_conversion_down",
            "conversion_up_payment_down",
            "traffic_up_payment_flat",
            "cross_metric_contradiction",
            "yoy_up_mom_down",
        )
    )
