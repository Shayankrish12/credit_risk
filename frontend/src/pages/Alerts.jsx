import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { signalLabel, severityColor } from "@/lib/format";
import { Bell, ArrowUpRight } from "@phosphor-icons/react";
import { toast } from "sonner";

export default function Alerts() {
  const [alerts, setAlerts] = useState([]);
  const [filter, setFilter] = useState("all");

  const load = async () => {
    try {
      const res = await api.get("/alerts");
      setAlerts(res.data);
    } catch (e) { toast.error("Failed to load alerts"); }
  };

  useEffect(() => { load(); }, []);

  const markRead = async (id) => {
    await api.post(`/alerts/${id}/read`);
    setAlerts(prev => prev.map(a => a.id === id ? { ...a, is_read: true } : a));
  };

  const filtered = filter === "all" ? alerts : alerts.filter(a => a.severity === filter);

  return (
    <div data-testid="alerts-page">
      <PageHeader overline="MONITORING" title="Alerts" subtitle="Active and historical alerts across your portfolio." />
      <div className="p-8 space-y-4">
        <div className="flex gap-1 border-b border-gray-200">
          {["all", "critical", "high", "medium", "low"].map(f => (
            <button key={f} onClick={() => setFilter(f)} data-testid={`filter-${f}`} className={`px-4 py-2 text-xs uppercase tracking-wider font-semibold border-b-2 -mb-px transition-colors ${filter === f ? "border-[#002FA7] text-[#0A0A0A]" : "border-transparent text-gray-500 hover:text-gray-700"}`}>
              {f} {f === "all" ? `(${alerts.length})` : `(${alerts.filter(a => a.severity === f).length})`}
            </button>
          ))}
        </div>

        <div className="border border-gray-200 bg-white divide-y divide-gray-100" data-testid="alerts-list">
          {filtered.length === 0 && <div className="p-12 text-center text-sm text-gray-500">No alerts.</div>}
          {filtered.map((a) => (
            <div key={a.id} className={`p-4 flex items-start gap-3 ${!a.is_read ? "bg-[#FFFCF5]" : ""}`} data-testid={`alert-${a.id}`}>
              <Bell weight="fill" size={18} className="mt-0.5 text-[#E53E3E] shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className={`inline-flex px-2 py-0.5 text-[10px] uppercase tracking-wider font-bold border rounded-sm ${severityColor(a.severity)}`}>{a.severity}</span>
                  <span className="text-sm font-semibold">{signalLabel(a.alert_type)}</span>
                  <span className="text-xs text-gray-500 font-mono">{a.created_at?.slice(0, 16).replace("T", " ")}</span>
                </div>
                <div className="text-sm text-gray-800 mt-1">{a.message}</div>
                <Link to={`/borrowers/${a.borrower_id}`} data-testid={`alert-borrower-${a.id}`} className="text-xs text-[#002FA7] inline-flex items-center gap-1 mt-1 hover:underline">
                  {a.borrower_name} <ArrowUpRight size={11} />
                </Link>
              </div>
              {!a.is_read && (
                <button onClick={() => markRead(a.id)} data-testid={`mark-read-${a.id}`} className="text-[10px] uppercase tracking-wider font-semibold text-gray-500 hover:text-[#002FA7]">
                  Mark read
                </button>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
