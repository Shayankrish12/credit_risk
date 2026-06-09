import { useEffect, useState } from "react";
import api from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { signalLabel } from "@/lib/format";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell, CartesianGrid } from "recharts";

export default function Analytics() {
  const [analytics, setAnalytics] = useState(null);
  const [overview, setOverview] = useState(null);

  useEffect(() => {
    Promise.all([api.get("/portfolio/analytics"), api.get("/portfolio/overview")])
      .then(([a, o]) => { setAnalytics(a.data); setOverview(o.data); })
      .catch(() => {});
  }, []);

  if (!analytics) return <div className="p-8 text-sm text-gray-500">Loading analytics...</div>;

  return (
    <div data-testid="analytics-page">
      <PageHeader overline="PORTFOLIO · ANALYTICS" title="Risk Analytics" subtitle="Aggregate views of warning signals, score distribution, and sector exposure." />
      <div className="p-8 space-y-6">
        <div className="grid lg:grid-cols-2 gap-6">
          <div className="border border-gray-200 bg-white" data-testid="signal-freq-card">
            <div className="px-6 py-4 border-b border-gray-200">
              <div className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-semibold">Frequency</div>
              <div className="font-heading font-bold text-base tracking-tight">Warning Signal Frequency</div>
            </div>
            <div className="p-4 h-80">
              <ResponsiveContainer>
                <BarChart data={analytics.signal_frequency.map(s => ({ ...s, label: signalLabel(s.signal_type) }))} layout="vertical">
                  <CartesianGrid strokeDasharray="2 2" stroke="#E5E7EB" />
                  <XAxis type="number" tick={{ fontSize: 11 }} stroke="#9CA3AF" />
                  <YAxis type="category" dataKey="label" width={140} tick={{ fontSize: 11 }} stroke="#9CA3AF" />
                  <Tooltip />
                  <Bar dataKey="count" fill="#E53E3E" radius={[0, 2, 2, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="border border-gray-200 bg-white" data-testid="risk-dist-card">
            <div className="px-6 py-4 border-b border-gray-200">
              <div className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-semibold">Distribution</div>
              <div className="font-heading font-bold text-base tracking-tight">Risk Score Distribution</div>
            </div>
            <div className="p-4 h-80">
              <ResponsiveContainer>
                <BarChart data={analytics.risk_distribution}>
                  <CartesianGrid strokeDasharray="2 2" stroke="#E5E7EB" />
                  <XAxis dataKey="range" tick={{ fontSize: 11 }} stroke="#9CA3AF" />
                  <YAxis tick={{ fontSize: 11 }} stroke="#9CA3AF" />
                  <Tooltip />
                  <Bar dataKey="count" radius={[2, 2, 0, 0]}>
                    {analytics.risk_distribution.map((d, i) => (
                      <Cell key={i} fill={["#38A169", "#002FA7", "#D69E2E", "#E53E3E"][i]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        <div className="border border-gray-200 bg-white" data-testid="sector-table">
          <div className="px-6 py-4 border-b border-gray-200">
            <div className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-semibold">Sectors</div>
            <div className="font-heading font-bold text-base tracking-tight">Sector-wise Risk Exposure</div>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-[#F9FAFB] border-b border-gray-200">
              <tr className="text-[10px] uppercase tracking-wider text-gray-600">
                <th className="px-4 py-2 text-left">Sector</th>
                <th className="px-4 py-2 text-right">Borrowers</th>
                <th className="px-4 py-2 text-right">Outstanding</th>
                <th className="px-4 py-2 text-right">Avg Risk Score</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {(overview?.sector_exposure || []).sort((a, b) => b.avg_risk - a.avg_risk).map((s) => (
                <tr key={s.sector}>
                  <td className="px-4 py-2.5 font-medium">{s.sector}</td>
                  <td className="px-4 py-2.5 text-right font-mono">{s.count}</td>
                  <td className="px-4 py-2.5 text-right font-mono">₹{(s.outstanding / 100000).toFixed(1)}L</td>
                  <td className="px-4 py-2.5 text-right font-mono font-semibold" style={{ color: s.avg_risk >= 75 ? "#E53E3E" : s.avg_risk >= 50 ? "#D69E2E" : s.avg_risk >= 25 ? "#002FA7" : "#38A169" }}>{s.avg_risk}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
