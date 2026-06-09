import { useEffect, useState } from "react";
import api from "@/lib/api";
import { formatINR } from "@/lib/format";
import { CheckCircle, Warning, XCircle } from "@phosphor-icons/react";

const STATUS_STYLE = {
  good: { color: "#38A169", bg: "bg-emerald-50 border-emerald-200 text-emerald-800", icon: CheckCircle },
  warning: { color: "#D69E2E", bg: "bg-amber-50 border-amber-200 text-amber-800", icon: Warning },
  bad: { color: "#E53E3E", bg: "bg-red-50 border-red-200 text-red-800", icon: XCircle },
};

export default function FinancialsTab({ borrowerId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.get(`/borrowers/${borrowerId}/financials`).then(r => {
      setData(r.data);
    }).catch(() => {}).finally(() => setLoading(false));
  }, [borrowerId]);

  if (loading) return <div className="p-6 text-sm text-gray-500">Loading financials...</div>;
  if (!data) return null;

  const { balance_sheets, pnl, ratios } = data;

  if (balance_sheets.length === 0 && pnl.length === 0) {
    return (
      <div className="border border-gray-200 bg-white p-12 text-center" data-testid="financials-empty">
        <div className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-semibold mb-2">No data</div>
        <div className="font-heading font-bold text-lg tracking-tight mb-2">Balance Sheet & P&amp;L not uploaded</div>
        <p className="text-sm text-gray-600 max-w-md mx-auto">Upload quarterly balance sheet and P&amp;L statements from the Upload Data page to see ratio analysis here.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="financials-tab">
      {/* Ratios grid */}
      {Object.keys(ratios).length > 0 && (
        <div data-testid="ratios-grid">
          <div className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-semibold mb-2">Latest Ratios · {data.latest_period}</div>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-2">
            {Object.values(ratios).map(r => {
              const s = STATUS_STYLE[r.status] || STATUS_STYLE.warning;
              const Icon = s.icon;
              return (
                <div key={r.label} className={`border p-3 rounded-sm ${s.bg}`} data-testid={`ratio-${r.label.replace(/\s+/g,'-').toLowerCase()}`}>
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="text-[9px] uppercase tracking-wider font-semibold opacity-80">{r.label}</div>
                    <Icon size={14} weight="fill" />
                  </div>
                  <div className="font-heading font-bold text-xl tracking-tight">{r.value}{r.suffix}</div>
                  <div className="text-[10px] mt-1 opacity-70">Target {r.benchmark}</div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* P&L Table */}
      {pnl.length > 0 && (
        <div className="border border-gray-200 bg-white overflow-x-auto" data-testid="pnl-table">
          <div className="px-5 py-3 border-b border-gray-200">
            <div className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-semibold">Profit & Loss</div>
            <div className="font-heading font-bold text-base tracking-tight">Quarterly P&amp;L</div>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-[#F9FAFB] border-b border-gray-200">
              <tr className="text-[10px] uppercase tracking-wider text-gray-600">
                <th className="px-4 py-2 text-left">Line Item</th>
                {pnl.map(p => <th key={p.period} className="px-4 py-2 text-right font-mono">{p.period}</th>)}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {[
                ["Revenue", "revenue"],
                ["COGS", "cogs"],
                ["Gross Profit", "gross_profit", true],
                ["Operating Expenses", "operating_expenses"],
                ["EBITDA", "ebitda", true],
                ["Depreciation", "depreciation"],
                ["EBIT", "ebit", true],
                ["Interest Expense", "interest_expense"],
                ["PBT", "pbt", true],
                ["Tax", "tax"],
                ["Net Profit", "net_profit", true],
              ].map(([label, key, bold]) => (
                <tr key={key} className={bold ? "bg-[#F9FAFB]/50 font-semibold" : ""}>
                  <td className="px-4 py-2">{label}</td>
                  {pnl.map(p => (
                    <td key={p.period} className={`px-4 py-2 text-right font-mono ${p[key] < 0 ? "text-red-700" : ""}`}>{formatINR(p[key])}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Balance Sheet Table */}
      {balance_sheets.length > 0 && (
        <div className="border border-gray-200 bg-white overflow-x-auto" data-testid="bs-table">
          <div className="px-5 py-3 border-b border-gray-200">
            <div className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-semibold">Balance Sheet</div>
            <div className="font-heading font-bold text-base tracking-tight">Quarterly Balance Sheet</div>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-[#F9FAFB] border-b border-gray-200">
              <tr className="text-[10px] uppercase tracking-wider text-gray-600">
                <th className="px-4 py-2 text-left">Line Item</th>
                {balance_sheets.map(b => <th key={b.period} className="px-4 py-2 text-right font-mono">{b.period}</th>)}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {[
                ["ASSETS", null, true],
                ["Cash", "cash"],
                ["Receivables", "receivables"],
                ["Inventory", "inventory"],
                ["Current Assets", "current_assets", true],
                ["Fixed Assets", "fixed_assets"],
                ["Other Assets", "other_assets"],
                ["LIABILITIES", null, true],
                ["Short-term Debt", "short_term_debt"],
                ["Current Liabilities", "current_liabilities", true],
                ["Long-term Debt", "long_term_debt"],
                ["Other Liabilities", "other_liabilities"],
                ["EQUITY", "equity", true],
              ].map(([label, key, bold], i) => (
                <tr key={i} className={bold ? "bg-[#F9FAFB]/50 font-semibold" : ""}>
                  <td className={`px-4 py-2 ${key === null ? "text-[10px] uppercase tracking-wider text-gray-500" : ""}`}>{label}</td>
                  {balance_sheets.map(b => (
                    <td key={b.period} className="px-4 py-2 text-right font-mono">{key ? formatINR(b[key]) : ""}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
