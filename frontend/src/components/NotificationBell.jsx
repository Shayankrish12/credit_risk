import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import { Bell } from "@phosphor-icons/react";
import { severityColor, signalLabel } from "@/lib/format";

export default function NotificationBell() {
  const [open, setOpen] = useState(false);
  const [alerts, setAlerts] = useState([]);
  const ref = useRef(null);

  const load = async () => {
    try {
      const res = await api.get("/alerts?unread_only=true");
      setAlerts(res.data);
    } catch {}
  };

  useEffect(() => {
    load();
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const onClick = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const markRead = async (id, e) => {
    e?.stopPropagation();
    await api.post(`/alerts/${id}/read`);
    setAlerts(prev => prev.filter(a => a.id !== id));
  };

  const markAllRead = async () => {
    await Promise.all(alerts.map(a => api.post(`/alerts/${a.id}/read`)));
    setAlerts([]);
  };

  return (
    <div ref={ref} className="relative">
      <button onClick={() => setOpen(!open)} data-testid="notification-bell" className="relative p-2 hover:bg-gray-100 transition-colors rounded-sm">
        <Bell size={18} weight={alerts.length > 0 ? "fill" : "regular"} className={alerts.length > 0 ? "text-[#E53E3E]" : "text-gray-700"} />
        {alerts.length > 0 && (
          <span data-testid="notification-count" className="absolute -top-0.5 -right-0.5 bg-[#E53E3E] text-white text-[9px] font-bold px-1 min-w-[16px] h-4 flex items-center justify-center rounded-full">
            {alerts.length > 99 ? "99+" : alerts.length}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-96 bg-white border border-gray-200 shadow-lg z-50" data-testid="notification-dropdown">
          <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
            <div>
              <div className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-semibold">Notifications</div>
              <div className="font-heading font-bold text-sm tracking-tight">Unread Alerts ({alerts.length})</div>
            </div>
            {alerts.length > 0 && (
              <button onClick={markAllRead} data-testid="mark-all-read-btn" className="text-[10px] uppercase tracking-wider font-semibold text-[#002FA7] hover:underline">
                Mark all read
              </button>
            )}
          </div>
          <div className="max-h-96 overflow-auto divide-y divide-gray-100">
            {alerts.length === 0 && <div className="p-6 text-center text-sm text-gray-500">No unread alerts</div>}
            {alerts.slice(0, 20).map(a => (
              <Link
                key={a.id}
                to={`/borrowers/${a.borrower_id}`}
                onClick={(e) => { setOpen(false); markRead(a.id, e); }}
                data-testid={`notification-${a.id}`}
                className="block px-4 py-3 hover:bg-[#F9FAFB] transition-colors"
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className={`inline-flex px-1.5 py-0.5 text-[9px] uppercase tracking-wider font-bold border rounded-sm ${severityColor(a.severity)}`}>{a.severity}</span>
                  <span className="text-xs font-medium truncate">{a.borrower_name}</span>
                </div>
                <div className="text-xs text-gray-700">{a.message}</div>
                <div className="text-[10px] uppercase tracking-wider text-gray-500 mt-1">{signalLabel(a.alert_type)} · {a.created_at?.slice(0, 10)}</div>
              </Link>
            ))}
          </div>
          <div className="border-t border-gray-200 px-4 py-2">
            <Link to="/alerts" onClick={() => setOpen(false)} data-testid="view-all-notifications" className="text-xs uppercase tracking-wider font-semibold text-[#002FA7] hover:underline">
              View all alerts →
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
