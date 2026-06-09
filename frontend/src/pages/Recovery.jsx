import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { severityColor } from "@/lib/format";
import { ArrowUpRight, ShieldWarning, Clock, CheckCircle, Lightning } from "@phosphor-icons/react";
import { toast } from "sonner";

const STATUS_COLORS = {
  open: "bg-red-50 text-red-700 border-red-200",
  in_progress: "bg-amber-50 text-amber-700 border-amber-200",
  escalated: "bg-purple-50 text-purple-700 border-purple-200",
  resolved: "bg-emerald-50 text-emerald-700 border-emerald-200",
};

const STATUS_LABELS = {
  open: "Open",
  in_progress: "In Progress",
  escalated: "Escalated",
  resolved: "Resolved",
};

export default function Recovery() {
  const [data, setData] = useState({ items: [], stats: {} });
  const [filter, setFilter] = useState("");
  const [assignedOnly, setAssignedOnly] = useState(false);

  const load = async () => {
    try {
      const params = {};
      if (filter) params.status = filter;
      if (assignedOnly) params.assigned_to_me = true;
      const res = await api.get("/recovery", { params });
      setData(res.data);
    } catch { toast.error("Failed to load cases"); }
  };
  useEffect(() => { load(); }, [filter, assignedOnly]);

  const stats = data.stats || {};

  return (
    <div data-testid="recovery-page">
      <PageHeader
        overline="OPERATIONS"
        title="Recovery Workflow"
        subtitle="Active cases for borrowers in critical risk. Auto-opened when score crosses to Critical."
      />
      <div className="p-8 space-y-6">
        {/* KPIs */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-0 border-l border-t border-gray-200" data-testid="recovery-stats">
          <StatCard icon={ShieldWarning} label="Open" value={stats.open || 0} color="#E53E3E" testid="stat-open" />
          <StatCard icon={Clock} label="In Progress" value={stats.in_progress || 0} color="#D69E2E" testid="stat-in-progress" />
          <StatCard icon={Lightning} label="Escalated" value={stats.escalated || 0} color="#7C3AED" testid="stat-escalated" />
          <StatCard icon={CheckCircle} label="Resolved" value={stats.resolved || 0} color="#38A169" testid="stat-resolved" />
        </div>

        {/* Filters */}
        <div className="flex gap-2 flex-wrap items-center">
          <div className="flex gap-1 border-b border-gray-200 -mb-px">
            {[
              { v: "", l: "All" },
              { v: "open", l: "Open" },
              { v: "in_progress", l: "In Progress" },
              { v: "escalated", l: "Escalated" },
              { v: "resolved", l: "Resolved" },
            ].map(t => (
              <button key={t.v} onClick={() => setFilter(t.v)} data-testid={`recovery-filter-${t.v || "all"}`} className={`px-4 py-2 text-xs uppercase tracking-wider font-semibold border-b-2 transition-colors ${filter === t.v ? "border-[#002FA7] text-[#0A0A0A]" : "border-transparent text-gray-500 hover:text-gray-700"}`}>
                {t.l}
              </button>
            ))}
          </div>
          <label className="ml-auto text-xs uppercase tracking-wider font-semibold text-gray-600 inline-flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={assignedOnly} onChange={(e) => setAssignedOnly(e.target.checked)} data-testid="assigned-to-me-checkbox" className="accent-[#002FA7]"/>
            Assigned to me
          </label>
        </div>

        {/* Cases list */}
        <div className="border border-gray-200 bg-white" data-testid="recovery-cases-list">
          <table className="w-full text-sm">
            <thead className="bg-[#F9FAFB] border-b border-gray-200">
              <tr className="text-[10px] uppercase tracking-wider text-gray-600">
                <th className="px-4 py-2 text-left">Borrower</th>
                <th className="px-4 py-2 text-left">Status</th>
                <th className="px-4 py-2 text-left">Priority</th>
                <th className="px-4 py-2 text-left">Assigned</th>
                <th className="px-4 py-2 text-left">Next Action</th>
                <th className="px-4 py-2 text-left">Deadline</th>
                <th className="px-4 py-2 text-left">Opened</th>
                <th className="px-4 py-2"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {data.items.map(c => (
                <tr key={c.id} className="hover:bg-[#F9FAFB]" data-testid={`recovery-row-${c.id}`}>
                  <td className="px-4 py-3 font-medium">
                    {c.borrower_name}
                    {c.auto_created && <span className="ml-2 inline-flex items-center gap-1 text-[9px] uppercase tracking-wider text-[#002FA7] font-semibold bg-blue-50 px-1.5 py-0.5 rounded-sm border border-blue-200">AUTO</span>}
                  </td>
                  <td className="px-4 py-3"><span className={`inline-flex px-2 py-0.5 text-[10px] uppercase tracking-wider font-bold border rounded-sm ${STATUS_COLORS[c.status]}`}>{STATUS_LABELS[c.status]}</span></td>
                  <td className="px-4 py-3"><span className={`inline-flex px-2 py-0.5 text-[10px] uppercase tracking-wider font-bold border rounded-sm ${severityColor(c.priority === "high" ? "high" : c.priority === "medium" ? "medium" : "low")}`}>{c.priority}</span></td>
                  <td className="px-4 py-3 text-xs text-gray-700">{c.assigned_to_name || <span className="text-gray-400">—</span>}</td>
                  <td className="px-4 py-3 text-xs text-gray-700 max-w-xs truncate">{c.next_action || "—"}</td>
                  <td className="px-4 py-3 font-mono text-xs">{c.deadline || <span className="text-gray-400">—</span>}</td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">{c.opened_at?.slice(0, 10)}</td>
                  <td className="px-4 py-3 text-right">
                    <Link to={`/recovery/${c.id}`} data-testid={`open-case-${c.id}`} className="text-xs uppercase tracking-wider font-semibold text-[#002FA7] inline-flex items-center gap-1 hover:underline">Open <ArrowUpRight size={11}/></Link>
                  </td>
                </tr>
              ))}
              {data.items.length === 0 && <tr><td colSpan="8" className="p-8 text-center text-sm text-gray-500">No recovery cases.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function StatCard({ icon: Icon, label, value, color, testid }) {
  return (
    <div className="border-r border-b border-gray-200 p-5 bg-white" data-testid={testid}>
      <div className="flex items-center gap-2 mb-2">
        <Icon size={14} weight="bold" style={{ color }} />
        <div className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-semibold">{label}</div>
      </div>
      <div className="font-heading font-bold text-3xl tracking-tight" style={{ color }}>{value}</div>
    </div>
  );
}
