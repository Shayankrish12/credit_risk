import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import RiskBadge from "@/components/RiskBadge";
import { formatINR, riskColor, signalLabel } from "@/lib/format";
import { ArrowUpRight, Database, Bell } from "@phosphor-icons/react";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell, PieChart, Pie } from "recharts";
import { toast } from "sonner";

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [seeding, setSeeding] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const res = await api.get("/portfolio/overview");
      setData(res.data);
    } catch (e) {
      toast.error("Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleSeed = async () => {
    setSeeding(true);
    try {
      const res = await api.post("/seed");
      if (res.data.seeded) toast.success(`Seeded ${res.data.count} borrowers`);
      else toast.info(res.data.message || "Already seeded");
      await load();
    } catch (e) {
      toast.error("Seed failed");
    } finally {
      setSeeding(false);
    }
  };

  if (loading) return <LoadingShell />;

  const cats = data?.by_category || {};
  const catData = [
    { name: "Low", value: cats.low || 0, color: "#38A169" },
    { name: "Moderate", value: cats.moderate || 0, color: "#002FA7" },
    { name: "High", value: cats.high || 0, color: "#D69E2E" },
    { name: "Critical", value: cats.critical || 0, color: "#E53E3E" },
  ];

  return (
    <div data-testid="dashboard-page">
      <PageHeader
        overline="PORTFOLIO · OVERVIEW"
        title="Risk Control Room"
        subtitle="Live view of your MSME portfolio. Risk scores, alerts, and exposure at a glance."
        actions={
          <button
            onClick={handleSeed}
            disabled={seeding}
            data-testid="seed-btn"
            className="px-3 py-2 text-xs uppercase tracking-wider font-semibold border border-gray-300 hover:border-[#0A0A0A] inline-flex items-center gap-1.5 rounded-sm disabled:opacity-50"
          >
            <Database size={14} weight="bold" /> {seeding ? "Seeding..." : "Seed sample data"}
          </button>
        }
      />

      <div className="p-8 space-y-6">
        {/* KPIs */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-0 border-l border-t border-gray-200" data-testid="kpi-grid">
          <Kpi label="Total Borrowers" value={data?.total_borrowers || 0} testid="kpi-total" />
          <Kpi label="Avg Risk Score" value={data?.avg_risk_score?.toFixed(1) || "0"} suffix="/100" accent={riskColor(scoreToCategory(data?.avg_risk_score))} testid="kpi-avg-risk" />
          <Kpi label="Outstanding at Risk" value={formatINR(data?.outstanding_at_risk)} testid="kpi-at-risk" />
          <Kpi label="Total Outstanding" value={formatINR(data?.total_outstanding)} testid="kpi-outstanding" />
        </div>

        <div className="grid lg:grid-cols-12 gap-6">
          {/* Risk distribution */}
          <div className="lg:col-span-5 border border-gray-200 bg-white" data-testid="risk-distribution-card">
            <CardHead title="Risk Distribution" overline="By Category" />
            <div className="p-6 grid grid-cols-2 gap-6 items-center">
              <div className="h-48">
                <ResponsiveContainer>
                  <PieChart>
                    <Pie data={catData} dataKey="value" innerRadius={40} outerRadius={75} paddingAngle={2}>
                      {catData.map((d, i) => <Cell key={i} fill={d.color} />)}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="space-y-2">
                {catData.map((d) => (
                  <div key={d.name} className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <span className="w-2.5 h-2.5" style={{ backgroundColor: d.color }}></span>
                      <span className="text-gray-700">{d.name}</span>
                    </div>
                    <span className="font-mono font-semibold">{d.value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Top risky */}
          <div className="lg:col-span-7 border border-gray-200 bg-white" data-testid="top-risky-card">
            <CardHead title="Top 5 Riskiest Borrowers" overline="Critical Watch" action={
              <Link to="/borrowers" className="text-xs uppercase tracking-wider text-[#002FA7] font-semibold inline-flex items-center gap-1 hover:underline" data-testid="view-all-borrowers">
                View all <ArrowUpRight size={12} />
              </Link>
            }/>
            <div className="divide-y divide-gray-100">
              {(data?.top_risky || []).map((b) => (
                <Link key={b.id} to={`/borrowers/${b.id}`} data-testid={`risky-row-${b.id}`} className="flex items-center justify-between px-6 py-3 hover:bg-[#F9FAFB] transition-colors">
                  <div className="min-w-0">
                    <div className="font-medium text-sm truncate">{b.business_name}</div>
                    <div className="text-[10px] uppercase tracking-wider text-gray-500 mt-0.5">{b.sector} · {b.location}</div>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <div className="text-right">
                      <div className="text-xs text-gray-500 font-mono">{formatINR(b.outstanding_amount)}</div>
                    </div>
                    <RiskBadge category={b.risk_category} score={b.risk_score} testid={`badge-${b.id}`} />
                  </div>
                </Link>
              ))}
              {(!data?.top_risky || data.top_risky.length === 0) && (
                <div className="p-6 text-center text-sm text-gray-500">No borrowers yet. Click "Seed sample data" to start.</div>
              )}
            </div>
          </div>
        </div>

        <div className="grid lg:grid-cols-12 gap-6">
          {/* Sector exposure */}
          <div className="lg:col-span-7 border border-gray-200 bg-white" data-testid="sector-exposure-card">
            <CardHead title="Sector Exposure" overline="Outstanding by Sector" />
            <div className="p-6 h-72">
              <ResponsiveContainer>
                <BarChart data={data?.sector_exposure || []}>
                  <XAxis dataKey="sector" tick={{ fontSize: 11 }} stroke="#9CA3AF" />
                  <YAxis tickFormatter={(v) => formatINR(v)} tick={{ fontSize: 11 }} stroke="#9CA3AF" />
                  <Tooltip formatter={(v, name) => name === "outstanding" ? formatINR(v) : v} />
                  <Bar dataKey="outstanding" fill="#002FA7" radius={[2, 2, 0, 0]}>
                    {(data?.sector_exposure || []).map((d, i) => (
                      <Cell key={i} fill={d.avg_risk > 60 ? "#E53E3E" : d.avg_risk > 40 ? "#D69E2E" : "#002FA7"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Recent alerts */}
          <div className="lg:col-span-5 border border-gray-200 bg-white" data-testid="recent-alerts-card">
            <CardHead title="Recent Alerts" overline="Last 10" action={
              <Link to="/alerts" className="text-xs uppercase tracking-wider text-[#002FA7] font-semibold inline-flex items-center gap-1 hover:underline" data-testid="view-all-alerts">
                View all <ArrowUpRight size={12} />
              </Link>
            }/>
            <div className="divide-y divide-gray-100 max-h-72 overflow-auto">
              {(data?.recent_alerts || []).map((a) => (
                <div key={a.id} className="px-6 py-3 flex items-start gap-3" data-testid={`alert-row-${a.id}`}>
                  <Bell size={14} weight="bold" className="mt-0.5 text-[#E53E3E] shrink-0" />
                  <div className="min-w-0 flex-1">
                    <div className="text-xs font-medium truncate">{a.borrower_name}</div>
                    <div className="text-xs text-gray-600">{a.message}</div>
                    <div className="text-[10px] uppercase tracking-wider text-gray-500 mt-1">{signalLabel(a.alert_type)} · {a.severity}</div>
                  </div>
                </div>
              ))}
              {(!data?.recent_alerts || data.recent_alerts.length === 0) && (
                <div className="p-6 text-sm text-gray-500 text-center">No alerts</div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function scoreToCategory(score) {
  if (!score) return "low";
  if (score >= 75) return "critical";
  if (score >= 50) return "high";
  if (score >= 25) return "moderate";
  return "low";
}

function Kpi({ label, value, suffix, accent, testid }) {
  return (
    <div className="border-r border-b border-gray-200 p-5 bg-white" data-testid={testid}>
      <div className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-semibold mb-2">{label}</div>
      <div className="flex items-baseline gap-1">
        <div className="font-heading font-bold text-3xl tracking-tight" style={accent ? { color: accent } : {}}>{value}</div>
        {suffix && <div className="text-sm text-gray-500 font-mono">{suffix}</div>}
      </div>
    </div>
  );
}

function CardHead({ title, overline, action }) {
  return (
    <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
      <div>
        <div className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-semibold">{overline}</div>
        <div className="font-heading font-bold text-base tracking-tight">{title}</div>
      </div>
      {action}
    </div>
  );
}

function LoadingShell() {
  return (
    <div className="p-8">
      <div className="h-8 w-64 bg-gray-100 animate-pulse mb-4"></div>
      <div className="grid grid-cols-4 gap-2 mb-6">
        {[1,2,3,4].map(i => <div key={i} className="h-24 bg-gray-100 animate-pulse"></div>)}
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div className="h-64 bg-gray-100 animate-pulse"></div>
        <div className="h-64 bg-gray-100 animate-pulse"></div>
      </div>
    </div>
  );
}
