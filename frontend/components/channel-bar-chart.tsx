import {
  formatInteger,
  formatPercent,
} from "@/lib/formatters";
import type { GrowthMetrics } from "@/types/analysis";

interface ChannelBarChartProps {
  channels: Array<[string, GrowthMetrics]>;
  metric: "registered_users" | "paid_rate";
}

const CHANNEL_COLORS: Record<string, string> = {
  小红书: "#4767e8",
  抖音: "#7f91de",
  微信: "#d39a38",
  自然流量: "#4e8b7a",
  未知: "#98a2b3",
};

export function ChannelBarChart({
  channels,
  metric,
}: ChannelBarChartProps) {
  const chartRows = channels
    .map(([channel, metrics]) => ({
      channel,
      value:
        metric === "registered_users"
          ? metrics.user_counts.registered_users
          : metrics.conversion_rates.paid_rate,
    }))
    .sort((left, right) => right.value - left.value);
  const maximum = Math.max(...chartRows.map((row) => row.value), 1);
  const isRate = metric === "paid_rate";

  return (
    <article className="chart-card">
      <div className="chart-heading">
        <div>
          <h3>{isRate ? "渠道成交率" : "渠道注册人数"}</h3>
          <p>
            {isRate
              ? "成交用户 / 到店用户，按效率降序"
              : "有效注册用户，按规模降序"}
          </p>
        </div>
        <span className="chart-unit">{isRate ? "%" : "用户数"}</span>
      </div>

      <div className="bar-chart" role="img" aria-label={isRate ? "各渠道成交率柱状图" : "各渠道注册人数柱状图"}>
        {chartRows.map((row) => (
          <div className="bar-row" key={row.channel}>
            <span className="bar-label">{row.channel}</span>
            <div className="bar-track">
              <span
                className="bar-fill"
                style={{
                  backgroundColor: CHANNEL_COLORS[row.channel] ?? "#4767e8",
                  width: `${Math.max((row.value / maximum) * 100, 2)}%`,
                }}
              />
            </div>
            <strong className="bar-value">
              {isRate ? formatPercent(row.value) : formatInteger(row.value)}
            </strong>
          </div>
        ))}
      </div>
    </article>
  );
}
