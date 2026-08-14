export function formatInteger(value: number): string {
  return value.toLocaleString("zh-CN");
}

export function formatOptionalInteger(value: number | null): string {
  return value === null ? "不可用" : formatInteger(value);
}

export function formatCurrency(value: number): string {
  return new Intl.NumberFormat("zh-CN", {
    style: "currency",
    currency: "CNY",
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatCurrencyPrecise(value: number): string {
  return new Intl.NumberFormat("zh-CN", {
    style: "currency",
    currency: "CNY",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

export function formatPercent(value: number): string {
  return new Intl.NumberFormat("zh-CN", {
    style: "percent",
    minimumFractionDigits: 1,
    maximumFractionDigits: 2,
  }).format(value);
}

export function formatOptionalPercent(value: number | null): string {
  return value === null ? "不可用" : formatPercent(value);
}

export function formatDateRange(
  startDate: string | null,
  endDate: string | null,
): string {
  if (!startDate || !endDate) {
    return "暂无有效时间";
  }
  return `${formatDate(startDate)} — ${formatDate(endDate)}`;
}

function formatDate(dateValue: string): string {
  const [year, month, day] = dateValue.split("-");
  return `${year}.${month}.${day}`;
}
