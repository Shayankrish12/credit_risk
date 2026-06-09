import { riskBg } from "@/lib/format";

export default function RiskBadge({ category, score, testid }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wider border rounded-sm ${riskBg(category)}`}
      data-testid={testid || `risk-badge-${category}`}
    >
      <span className="font-mono">{score?.toFixed?.(0) ?? score}</span>
      <span>{category}</span>
    </span>
  );
}
