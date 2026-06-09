import { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import api from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import RiskBadge from "@/components/RiskBadge";
import { formatINR, severityColor } from "@/lib/format";
import { ArrowLeft, FloppyDisk, CheckCircle, Lightning, ChatTeardropText, ArrowsClockwise, Phone } from "@phosphor-icons/react";
import { toast } from "sonner";
import RecoveryCopilot from "@/components/RecoveryCopilot";

const STATUSES = ["open", "in_progress", "escalated", "resolved"];
const PRIORITIES = ["low", "medium", "high"];

export default function RecoveryDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [users, setUsers] = useState([]);
  const [edits, setEdits] = useState({});
  const [eventText, setEventText] = useState("");
  const [eventType, setEventType] = useState("contact");
  const [saving, setSaving] = useState(false);

  const load = async () => {
    try {
      const res = await api.get(`/recovery/${id}`);
      setData(res.data);
      setEdits({
        status: res.data.case.status,
        priority: res.data.case.priority,
        assigned_to: res.data.case.assigned_to || "",
        deadline: res.data.case.deadline || "",
        next_action: res.data.case.next_action || "",
      });
    } catch { toast.error("Failed to load case"); }
  };

  useEffect(() => {
    load();
    api.get("/auth/users").then(r => setUsers(r.data)).catch(() => setUsers([]));
  }, [id]);

  const saveCase = async () => {
    setSaving(true);
    try {
      const payload = { ...edits };
      if (!payload.assigned_to) payload.assigned_to = null;
      if (!payload.deadline) delete payload.deadline;
      await api.patch(`/recovery/${id}`, payload);
      toast.success("Case updated");
      load();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Update failed");
    } finally { setSaving(false); }
  };

  const addEvent = async () => {
    if (!eventText.trim()) return;
    try {
      await api.post(`/recovery/${id}/timeline`, { type: eventType, content: eventText });
      setEventText("");
      toast.success("Event added");
      load();
    } catch { toast.error("Failed to add event"); }
  };

  if (!data) return <div className="p-8 text-sm text-gray-500">Loading case...</div>;
  const { case: c, timeline, borrower } = data;

  return (
    <div data-testid="recovery-detail-page">
      <PageHeader
        overline={`CASE · ${c.status.toUpperCase()}`}
        title={c.borrower_name}
        subtitle={`Recovery case opened ${c.opened_at?.slice(0, 10)} ${c.auto_created ? "(auto)" : ""}`}
        actions={
          <div className="flex gap-2 items-center">
            {borrower && <RiskBadge category={borrower.risk_category} score={borrower.risk_score} />}
            <Link to="/recovery" data-testid="back-to-recovery" className="px-3 py-2 text-xs uppercase tracking-wider font-semibold border border-gray-300 hover:border-[#0A0A0A] inline-flex items-center gap-1.5">
              <ArrowLeft size={14} weight="bold"/> Back
            </Link>
            <Link to={`/borrowers/${c.borrower_id}`} data-testid="view-borrower-link" className="px-3 py-2 text-xs uppercase tracking-wider font-semibold bg-[#0A0A0A] text-white hover:bg-[#002FA7]">View Borrower</Link>
          </div>
        }
      />

      <div className="p-8 grid lg:grid-cols-12 gap-6">
        {/* Left: case controls */}
        <div className="lg:col-span-5 space-y-6">
          <div className="border border-gray-200 bg-white" data-testid="case-controls">
            <div className="px-5 py-3 border-b border-gray-200">
              <div className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-semibold">Case</div>
              <div className="font-heading font-bold text-base tracking-tight">Update Case</div>
            </div>
            <div className="p-5 space-y-4">
              <FieldRow label="Status">
                <select value={edits.status} onChange={(e) => setEdits({ ...edits, status: e.target.value })} data-testid="status-select" className="form-input">
                  {STATUSES.map(s => <option key={s} value={s}>{s.replace("_", " ").toUpperCase()}</option>)}
                </select>
              </FieldRow>
              <FieldRow label="Priority">
                <select value={edits.priority} onChange={(e) => setEdits({ ...edits, priority: e.target.value })} data-testid="priority-select" className="form-input">
                  {PRIORITIES.map(s => <option key={s} value={s}>{s.toUpperCase()}</option>)}
                </select>
              </FieldRow>
              <FieldRow label="Assigned To">
                <select value={edits.assigned_to} onChange={(e) => setEdits({ ...edits, assigned_to: e.target.value })} data-testid="assigned-select" className="form-input">
                  <option value="">Unassigned</option>
                  {users.map(u => <option key={u.id} value={u.id}>{u.name} ({u.role})</option>)}
                </select>
              </FieldRow>
              <FieldRow label="Deadline">
                <input type="date" value={edits.deadline} onChange={(e) => setEdits({ ...edits, deadline: e.target.value })} data-testid="deadline-input" className="form-input"/>
              </FieldRow>
              <FieldRow label="Next Action">
                <textarea value={edits.next_action} onChange={(e) => setEdits({ ...edits, next_action: e.target.value })} rows={3} data-testid="next-action-input" className="form-input resize-none"/>
              </FieldRow>
              <button onClick={saveCase} disabled={saving} data-testid="save-case-btn" className="w-full px-4 py-2.5 text-xs uppercase tracking-wider font-semibold bg-[#0A0A0A] text-white hover:bg-[#002FA7] disabled:opacity-50 inline-flex items-center justify-center gap-1.5">
                <FloppyDisk size={14} weight="bold"/> {saving ? "Saving..." : "Save Case"}
              </button>
            </div>
          </div>

          {borrower && (
            <div className="border border-gray-200 bg-white p-5" data-testid="case-borrower-summary">
              <div className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-semibold mb-2">Borrower Snapshot</div>
              <div className="font-heading font-bold text-lg tracking-tight mb-3">{borrower.business_name}</div>
              <dl className="space-y-1.5 text-xs">
                <Info l="Sector" v={borrower.sector} />
                <Info l="Location" v={borrower.location} />
                <Info l="Outstanding" v={formatINR(borrower.outstanding_amount)} />
                <Info l="Risk Score" v={`${borrower.risk_score?.toFixed(1)}/100 (${borrower.risk_category?.toUpperCase()})`} />
                <Info l="Contact" v={borrower.contact_person || "—"} />
                <Info l="Phone" v={borrower.contact_phone || "—"} mono />
              </dl>
            </div>
          )}

          {/* Recovery AI Copilot */}
          <RecoveryCopilot caseId={id} borrowerName={c.borrower_name} />
        </div>

        {/* Right: timeline */}
        <div className="lg:col-span-7 space-y-4">
          <div className="border border-gray-200 bg-white" data-testid="add-event-card">
            <div className="px-5 py-3 border-b border-gray-200">
              <div className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-semibold">Log</div>
              <div className="font-heading font-bold text-base tracking-tight">Add Timeline Event</div>
            </div>
            <div className="p-5 space-y-2">
              <div className="flex gap-2">
                {[
                  { v: "contact", l: "Contact", icon: Phone },
                  { v: "note", l: "Note", icon: ChatTeardropText },
                  { v: "action_update", l: "Action", icon: Lightning },
                ].map(t => (
                  <button key={t.v} onClick={() => setEventType(t.v)} data-testid={`event-type-${t.v}`} className={`px-3 py-1.5 text-[10px] uppercase tracking-wider font-semibold border rounded-sm transition-colors inline-flex items-center gap-1.5 ${eventType === t.v ? "border-[#002FA7] bg-[#F9FAFB] text-[#002FA7]" : "border-gray-300 hover:border-gray-400 text-gray-600"}`}>
                    <t.icon size={12} weight="bold"/> {t.l}
                  </button>
                ))}
              </div>
              <textarea value={eventText} onChange={(e) => setEventText(e.target.value)} placeholder="Describe contact, action update, or note..." rows={2} data-testid="event-input" className="w-full border border-gray-300 px-3 py-2 text-sm focus:border-[#002FA7] focus:outline-none rounded-sm resize-none"/>
              <div className="flex justify-end">
                <button onClick={addEvent} data-testid="add-event-btn" className="px-4 py-2 text-xs uppercase tracking-wider font-semibold bg-[#0A0A0A] text-white hover:bg-[#002FA7]">Log Event</button>
              </div>
            </div>
          </div>

          <div className="border border-gray-200 bg-white" data-testid="timeline-card">
            <div className="px-5 py-3 border-b border-gray-200">
              <div className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-semibold">History</div>
              <div className="font-heading font-bold text-base tracking-tight">Timeline</div>
            </div>
            <div className="divide-y divide-gray-100 max-h-[600px] overflow-auto">
              {timeline.length === 0 && <div className="p-8 text-center text-sm text-gray-500">No events yet.</div>}
              {timeline.map(ev => (
                <div key={ev.id} className="p-4" data-testid={`timeline-event-${ev.id}`}>
                  <div className="flex items-center gap-2 flex-wrap mb-1">
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-[9px] uppercase tracking-wider font-bold border rounded-sm ${eventTypeStyle(ev.type)}`}>
                      {ev.type.replace("_", " ")}
                    </span>
                    <span className="text-[11px] text-gray-500 font-mono">{ev.at?.slice(0, 16).replace("T", " ")}</span>
                    <span className="text-[11px] text-gray-700">by {ev.by_user_name}</span>
                  </div>
                  <p className="text-sm text-gray-800 ml-1">{ev.content}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <style>{`.form-input { width: 100%; padding: 0.5rem 0.75rem; border: 1px solid #D1D5DB; font-size: 0.875rem; border-radius: 0.125rem; background: white; }
        .form-input:focus { outline: none; border-color: #002FA7; box-shadow: 0 0 0 2px rgba(0,47,167,0.2); }`}</style>
    </div>
  );
}

function eventTypeStyle(t) {
  return {
    note: "bg-blue-50 text-blue-700 border-blue-200",
    contact: "bg-emerald-50 text-emerald-700 border-emerald-200",
    action_update: "bg-amber-50 text-amber-700 border-amber-200",
    status_change: "bg-purple-50 text-purple-700 border-purple-200",
    system: "bg-gray-100 text-gray-700 border-gray-300",
  }[t] || "bg-gray-100 text-gray-700 border-gray-300";
}

function FieldRow({ label, children }) {
  return (
    <div>
      <label className="text-[10px] uppercase tracking-wider font-semibold text-gray-600 mb-1 block">{label}</label>
      {children}
    </div>
  );
}

function Info({ l, v, mono }) {
  return (
    <div className="flex justify-between gap-2">
      <dt className="text-gray-500 uppercase tracking-wider text-[10px]">{l}</dt>
      <dd className={`text-gray-800 ${mono ? "font-mono" : ""}`}>{v}</dd>
    </div>
  );
}
