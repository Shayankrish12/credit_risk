import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import RiskBadge from "@/components/RiskBadge";
import { formatINR, severityColor, signalLabel, riskColor } from "@/lib/format";
import { toast } from "sonner";
import { ResponsiveContainer, LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, Area, AreaChart, Cell } from "recharts";
import { ArrowUpRight, FilePdf, FileDoc, Trash, ArrowsClockwise, ChatCircle, PencilSimple } from "@phosphor-icons/react";
import { API } from "@/lib/api";
import BorrowerChat from "@/components/BorrowerChat";
import FinancialsTab from "@/components/FinancialsTab";
import { useAuth } from "@/lib/auth-context";

export default function BorrowerDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [noteContent, setNoteContent] = useState("");
  const [showChat, setShowChat] = useState(false);
  const [showEdit, setShowEdit] = useState(false);
  const [tab, setTab] = useState("overview");

  const load = async () => {
    try {
      const res = await api.get(`/borrowers/${id}/details`);
      setData(res.data);
    } catch (e) { toast.error("Failed to load borrower"); }
  };
  useEffect(() => { load(); }, [id]);

  const recompute = async () => {
    try {
      await api.post(`/borrowers/${id}/recompute`);
      toast.success("Risk recomputed");
      load();
    } catch (e) { toast.error("Recompute failed"); }
  };

  const handleDelete = async () => {
    if (!window.confirm(`Delete ${data.borrower.business_name}?`)) return;
    try {
      await api.delete(`/borrowers/${id}`);
      toast.success("Borrower deleted");
      navigate("/borrowers");
    } catch (e) { toast.error(e.response?.data?.detail || "Delete failed"); }
  };

  const addNote = async () => {
    if (!noteContent.trim()) return;
    try {
      await api.post("/notes", { borrower_id: id, content: noteContent });
      setNoteContent("");
      toast.success("Note added");
      load();
    } catch (e) { toast.error("Failed to add note"); }
  };

  const downloadReport = async (fmt) => {
    try {
      const token = localStorage.getItem("msme_token");
      const res = await fetch(`${API}/reports/${id}/${fmt}`, { headers: { Authorization: `Bearer ${token}` } });
      if (!res.ok) throw new Error("Report failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${data.borrower.business_name.replace(/\s+/g, "_")}_credit_note.${fmt}`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success(`${fmt.toUpperCase()} downloaded`);
    } catch (e) { toast.error("Download failed"); }
  };

  if (!data) return <div className="p-8 text-sm text-gray-500">Loading borrower...</div>;

  const { borrower, sales, bank, repayments, signals, alerts, notes, risk_history } = data;

  const salesData = sales.map(s => ({ month: s.month.slice(5), amount: s.amount }));
  const bankData = bank.map(b => ({ month: b.month.slice(5), balance: b.balance }));
  const repayData = repayments.map(r => ({
    month: r.due_date.slice(0, 7).slice(5),
    delay: r.days_delayed,
    status: r.status,
  }));
  const historyData = risk_history.map(h => ({
    date: h.recorded_at.slice(0, 10),
    score: h.score,
  }));

  return (
    <div data-testid="borrower-detail-page">
      <PageHeader
        overline={`BORROWER · ${borrower.sector?.toUpperCase()}`}
        title={borrower.business_name}
        subtitle={`${borrower.location} · ${borrower.loan_type} · Sanctioned ${borrower.sanction_date}`}
        actions={
          <div className="flex gap-2 items-center">
            <RiskBadge category={borrower.risk_category} score={borrower.risk_score} testid="detail-risk-badge" />
            <button onClick={recompute} data-testid="recompute-btn" className="px-3 py-2 text-xs uppercase tracking-wider font-semibold border border-gray-300 hover:border-[#0A0A0A] inline-flex items-center gap-1.5">
              <ArrowsClockwise size={14} weight="bold"/> Recompute
            </button>
            <button onClick={() => downloadReport("pdf")} data-testid="export-pdf-btn" className="px-3 py-2 text-xs uppercase tracking-wider font-semibold border border-gray-300 hover:border-[#0A0A0A] inline-flex items-center gap-1.5">
              <FilePdf size={14} weight="bold"/> PDF
            </button>
            <button onClick={() => downloadReport("docx")} data-testid="export-docx-btn" className="px-3 py-2 text-xs uppercase tracking-wider font-semibold border border-gray-300 hover:border-[#0A0A0A] inline-flex items-center gap-1.5">
              <FileDoc size={14} weight="bold"/> DOCX
            </button>
            <button onClick={() => setShowChat(true)} data-testid="open-chat-btn" className="px-3 py-2 text-xs uppercase tracking-wider font-semibold bg-[#002FA7] text-white hover:bg-[#0A0A0A] inline-flex items-center gap-1.5">
              <ChatCircle size={14} weight="bold"/> AI Copilot
            </button>
            {(user?.role === "admin" || user?.role === "analyst") && (
              <button onClick={() => setShowEdit(true)} data-testid="edit-borrower-btn" className="px-3 py-2 text-xs uppercase tracking-wider font-semibold border border-gray-300 hover:border-[#0A0A0A] inline-flex items-center gap-1.5">
                <PencilSimple size={14} weight="bold"/> Edit
              </button>
            )}
            {user?.role === "admin" && (
              <button onClick={handleDelete} data-testid="delete-borrower-btn" className="px-3 py-2 text-xs uppercase tracking-wider font-semibold border border-red-300 text-red-700 hover:bg-red-50 inline-flex items-center gap-1.5">
                <Trash size={14} weight="bold"/>
              </button>
            )}
          </div>
        }
      />

      <div className="p-8 space-y-6">
        {/* Tabs */}
        <div className="flex gap-0 border-b border-gray-200">
          {["overview", "signals", "financials", "statements", "notes"].map(t => (
            <button key={t} onClick={() => setTab(t)} data-testid={`tab-${t}`} className={`px-4 py-2 text-sm font-medium uppercase tracking-wider border-b-2 -mb-px transition-colors ${tab === t ? "border-[#002FA7] text-[#0A0A0A]" : "border-transparent text-gray-500 hover:text-gray-700"}`}>
              {t === "financials" ? "Financials" : t === "statements" ? "BS / P&L" : t}
            </button>
          ))}
        </div>

        {tab === "overview" && (
          <>
            {/* KPIs */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-0 border-l border-t border-gray-200">
              <Kpi label="Risk Score" value={borrower.risk_score?.toFixed(1)} suffix="/100" color={riskColor(borrower.risk_category)} />
              <Kpi label="Outstanding" value={formatINR(borrower.outstanding_amount)} />
              <Kpi label="Loan Amount" value={formatINR(borrower.loan_amount)} />
              <Kpi label="Active Signals" value={signals.length} suffix={`/ ${signals.filter(s => s.severity === "critical" || s.severity === "high").length} critical`} />
            </div>

            {/* Charts row */}
            <div className="grid lg:grid-cols-2 gap-6">
              <ChartCard title="Monthly Sales Trend" overline="Last 12 months">
                <ResponsiveContainer>
                  <AreaChart data={salesData}>
                    <defs>
                      <linearGradient id="salesGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#002FA7" stopOpacity={0.3} />
                        <stop offset="100%" stopColor="#002FA7" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="2 2" stroke="#E5E7EB" />
                    <XAxis dataKey="month" tick={{ fontSize: 11 }} stroke="#9CA3AF" />
                    <YAxis tickFormatter={(v) => formatINR(v)} tick={{ fontSize: 11 }} stroke="#9CA3AF" />
                    <Tooltip formatter={(v) => formatINR(v)} />
                    <Area type="monotone" dataKey="amount" stroke="#002FA7" strokeWidth={2} fill="url(#salesGrad)" />
                  </AreaChart>
                </ResponsiveContainer>
              </ChartCard>
              <ChartCard title="Bank Balance Trend" overline="Closing balance">
                <ResponsiveContainer>
                  <LineChart data={bankData}>
                    <CartesianGrid strokeDasharray="2 2" stroke="#E5E7EB" />
                    <XAxis dataKey="month" tick={{ fontSize: 11 }} stroke="#9CA3AF" />
                    <YAxis tickFormatter={(v) => formatINR(v)} tick={{ fontSize: 11 }} stroke="#9CA3AF" />
                    <Tooltip formatter={(v) => formatINR(v)} />
                    <Line type="monotone" dataKey="balance" stroke="#38A169" strokeWidth={2} dot={{ r: 3 }} />
                  </LineChart>
                </ResponsiveContainer>
              </ChartCard>
            </div>

            <div className="grid lg:grid-cols-2 gap-6">
              <ChartCard title="EMI Delay (days)" overline="Per repayment cycle">
                <ResponsiveContainer>
                  <BarChart data={repayData}>
                    <CartesianGrid strokeDasharray="2 2" stroke="#E5E7EB" />
                    <XAxis dataKey="month" tick={{ fontSize: 11 }} stroke="#9CA3AF" />
                    <YAxis tick={{ fontSize: 11 }} stroke="#9CA3AF" />
                    <Tooltip />
                    <Bar dataKey="delay" radius={[2, 2, 0, 0]}>
                      {repayData.map((d, i) => (
                        <Cell key={i} fill={d.status === "bounced" ? "#E53E3E" : d.status === "delayed" ? "#D69E2E" : "#38A169"} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </ChartCard>
              <ChartCard title="Risk Score History" overline="Over time">
                <ResponsiveContainer>
                  <LineChart data={historyData}>
                    <CartesianGrid strokeDasharray="2 2" stroke="#E5E7EB" />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} stroke="#9CA3AF" />
                    <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} stroke="#9CA3AF" />
                    <Tooltip />
                    <Line type="monotone" dataKey="score" stroke="#E53E3E" strokeWidth={2} dot={{ r: 4 }} />
                  </LineChart>
                </ResponsiveContainer>
              </ChartCard>
            </div>

            {/* Risk factors */}
            <div className="border border-gray-200 bg-white" data-testid="risk-factors-card">
              <div className="px-6 py-4 border-b border-gray-200">
                <div className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-semibold">Why</div>
                <div className="font-heading font-bold text-base tracking-tight">Top Contributing Risk Factors</div>
              </div>
              <table className="w-full text-sm">
                <thead className="bg-[#F9FAFB] border-b border-gray-200">
                  <tr className="text-[10px] uppercase tracking-wider text-gray-600">
                    <th className="px-4 py-2 text-left">Factor</th>
                    <th className="px-4 py-2 text-right">Impact</th>
                    <th className="px-4 py-2 text-left">Detail</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {(borrower.risk_factors || []).map((f, i) => (
                    <tr key={i}>
                      <td className="px-4 py-2.5 font-medium">{f.factor}</td>
                      <td className="px-4 py-2.5 text-right font-mono font-semibold text-[#E53E3E]">+{f.impact}</td>
                      <td className="px-4 py-2.5 text-gray-700">{f.detail}</td>
                    </tr>
                  ))}
                  {(!borrower.risk_factors || borrower.risk_factors.length === 0) && (
                    <tr><td colSpan="3" className="p-4 text-center text-sm text-gray-500">No major risk factors detected.</td></tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Borrower info */}
            <div className="border border-gray-200 bg-white p-6 grid md:grid-cols-3 gap-x-6 gap-y-3 text-sm" data-testid="borrower-info">
              <InfoRow label="GST Number" value={borrower.gst_number || "—"} mono />
              <InfoRow label="Contact" value={borrower.contact_person || "—"} />
              <InfoRow label="Phone" value={borrower.contact_phone || "—"} mono />
            </div>
          </>
        )}

        {tab === "signals" && (
          <div className="border border-gray-200 bg-white" data-testid="signals-tab">
            <div className="px-6 py-4 border-b border-gray-200">
              <div className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-semibold">Active</div>
              <div className="font-heading font-bold text-base tracking-tight">Early Warning Signals</div>
            </div>
            <div className="divide-y divide-gray-100">
              {signals.length === 0 && <div className="p-8 text-center text-sm text-gray-500">No active warning signals.</div>}
              {signals.map((s) => (
                <div key={s.id} className="p-5" data-testid={`signal-${s.id}`}>
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 mb-1.5">
                        <span className={`inline-flex items-center px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider border rounded-sm ${severityColor(s.severity)}`}>{s.severity}</span>
                        <span className="font-semibold text-sm">{signalLabel(s.signal_type)}</span>
                        <span className="text-[10px] text-gray-500 font-mono">{s.detected_at?.slice(0, 10)}</span>
                      </div>
                      <p className="text-sm text-gray-700">{s.explanation}</p>
                      <p className="text-xs text-[#002FA7] mt-1.5 font-medium"><span className="uppercase tracking-wider mr-1">Action →</span> {s.suggested_action}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {tab === "financials" && (
          <div className="space-y-6">
            <div className="border border-gray-200 bg-white" data-testid="repayments-table">
              <div className="px-6 py-4 border-b border-gray-200">
                <div className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-semibold">History</div>
                <div className="font-heading font-bold text-base tracking-tight">Repayment Schedule</div>
              </div>
              <table className="w-full text-sm">
                <thead className="bg-[#F9FAFB] border-b border-gray-200">
                  <tr className="text-[10px] uppercase tracking-wider text-gray-600">
                    <th className="px-4 py-2 text-left">Due Date</th>
                    <th className="px-4 py-2 text-left">Paid Date</th>
                    <th className="px-4 py-2 text-right">Amount</th>
                    <th className="px-4 py-2 text-left">Status</th>
                    <th className="px-4 py-2 text-right">Days Delayed</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {repayments.map((r) => (
                    <tr key={r.id}>
                      <td className="px-4 py-2 font-mono text-xs">{r.due_date}</td>
                      <td className="px-4 py-2 font-mono text-xs">{r.paid_date || "—"}</td>
                      <td className="px-4 py-2 text-right font-mono">{formatINR(r.amount)}</td>
                      <td className="px-4 py-2"><span className={`inline-flex px-2 py-0.5 text-[10px] uppercase tracking-wider font-bold border rounded-sm ${severityColor(r.status === "bounced" ? "critical" : r.status === "delayed" ? "medium" : "low")}`}>{r.status}</span></td>
                      <td className="px-4 py-2 text-right font-mono">{r.days_delayed || 0}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {tab === "statements" && (
          <FinancialsTab borrowerId={id} />
        )}

        {tab === "notes" && (
          <div className="space-y-4">
            {(user?.role === "admin" || user?.role === "analyst") && (
              <div className="border border-gray-200 bg-white p-4" data-testid="add-note-form">
                <textarea
                  value={noteContent}
                  onChange={(e) => setNoteContent(e.target.value)}
                  placeholder="Add an analyst observation..."
                  rows={3}
                  data-testid="note-input"
                  className="w-full border border-gray-300 px-3 py-2 text-sm focus:border-[#002FA7] focus:outline-none rounded-sm resize-none"
                />
                <div className="flex justify-end mt-2">
                  <button onClick={addNote} data-testid="add-note-btn" className="px-4 py-2 text-xs uppercase tracking-wider font-semibold bg-[#0A0A0A] text-white hover:bg-[#002FA7]">Add Note</button>
                </div>
              </div>
            )}
            <div className="border border-gray-200 bg-white divide-y divide-gray-100" data-testid="notes-list">
              {notes.length === 0 && <div className="p-8 text-center text-sm text-gray-500">No analyst notes yet.</div>}
              {notes.map(n => (
                <div key={n.id} className="p-4">
                  <div className="text-xs text-gray-500 mb-1 font-mono">{n.created_by_name || "Analyst"} · {n.created_at?.slice(0, 16).replace("T", " ")}</div>
                  <div className="text-sm text-gray-800">{n.content}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {showChat && <BorrowerChat borrowerId={id} borrowerName={borrower.business_name} onClose={() => setShowChat(false)} />}
      {showEdit && <EditBorrowerDialog borrower={borrower} onClose={() => setShowEdit(false)} onUpdated={() => { setShowEdit(false); load(); }} />}
    </div>
  );
}

function Kpi({ label, value, suffix, color }) {
  return (
    <div className="border-r border-b border-gray-200 p-5 bg-white">
      <div className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-semibold mb-2">{label}</div>
      <div className="flex items-baseline gap-1.5">
        <div className="font-heading font-bold text-2xl tracking-tight" style={color ? { color } : {}}>{value}</div>
        {suffix && <div className="text-xs text-gray-500 font-mono">{suffix}</div>}
      </div>
    </div>
  );
}

function ChartCard({ title, overline, children }) {
  return (
    <div className="border border-gray-200 bg-white">
      <div className="px-6 py-3 border-b border-gray-200">
        <div className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-semibold">{overline}</div>
        <div className="font-heading font-bold text-sm tracking-tight">{title}</div>
      </div>
      <div className="p-4 h-64">{children}</div>
    </div>
  );
}

function InfoRow({ label, value, mono }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold">{label}</div>
      <div className={`text-sm text-gray-800 ${mono ? "font-mono" : ""}`}>{value}</div>
    </div>
  );
}

function EditBorrowerDialog({ borrower, onClose, onUpdated }) {
  const [form, setForm] = useState({
    business_name: borrower.business_name || "",
    sector: borrower.sector || "",
    location: borrower.location || "",
    loan_amount: borrower.loan_amount || 0,
    loan_type: borrower.loan_type || "",
    sanction_date: borrower.sanction_date || "",
    outstanding_amount: borrower.outstanding_amount || 0,
    gst_number: borrower.gst_number || "",
    contact_person: borrower.contact_person || "",
    contact_phone: borrower.contact_phone || "",
  });
  const [sectors, setSectors] = useState([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.get("/meta/sectors").then(r => setSectors(r.data)).catch(() => {});
  }, []);

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api.put(`/borrowers/${borrower.id}`, {
        ...form,
        loan_amount: Number(form.loan_amount),
        outstanding_amount: Number(form.outstanding_amount),
      });
      toast.success("Borrower updated");
      onUpdated();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Update failed");
    } finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={onClose} data-testid="edit-borrower-dialog">
      <div className="bg-white border border-gray-200 max-w-lg w-full max-h-[90vh] overflow-auto" onClick={(e) => e.stopPropagation()}>
        <div className="border-b border-gray-200 px-6 py-4">
          <div className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-semibold">Edit</div>
          <h2 className="font-heading font-bold text-xl tracking-tight">{borrower.business_name}</h2>
        </div>
        <form onSubmit={submit} className="p-6 grid grid-cols-2 gap-3">
          <EditField label="Business Name *" colSpan={2}>
            <input required value={form.business_name} onChange={(e) => setForm({ ...form, business_name: e.target.value })} data-testid="edit-business-name" className="edit-input" />
          </EditField>
          <EditField label="Sector">
            <select value={form.sector} onChange={(e) => setForm({ ...form, sector: e.target.value })} data-testid="edit-sector" className="edit-input bg-white">
              {sectors.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </EditField>
          <EditField label="Location">
            <input value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} data-testid="edit-location" className="edit-input" />
          </EditField>
          <EditField label="Loan Type">
            <input value={form.loan_type} onChange={(e) => setForm({ ...form, loan_type: e.target.value })} data-testid="edit-loan-type" className="edit-input" />
          </EditField>
          <EditField label="Sanction Date">
            <input type="date" value={form.sanction_date?.slice(0, 10)} onChange={(e) => setForm({ ...form, sanction_date: e.target.value })} data-testid="edit-sanction-date" className="edit-input" />
          </EditField>
          <EditField label="Loan Amount (INR)">
            <input type="number" value={form.loan_amount} onChange={(e) => setForm({ ...form, loan_amount: e.target.value })} data-testid="edit-loan-amount" className="edit-input" />
          </EditField>
          <EditField label="Outstanding (INR)">
            <input type="number" value={form.outstanding_amount} onChange={(e) => setForm({ ...form, outstanding_amount: e.target.value })} data-testid="edit-outstanding" className="edit-input" />
          </EditField>
          <EditField label="GST Number">
            <input value={form.gst_number} onChange={(e) => setForm({ ...form, gst_number: e.target.value })} data-testid="edit-gst" className="edit-input" />
          </EditField>
          <EditField label="Contact Person">
            <input value={form.contact_person} onChange={(e) => setForm({ ...form, contact_person: e.target.value })} data-testid="edit-contact" className="edit-input" />
          </EditField>
          <EditField label="Contact Phone" colSpan={2}>
            <input value={form.contact_phone} onChange={(e) => setForm({ ...form, contact_phone: e.target.value })} data-testid="edit-phone" className="edit-input" />
          </EditField>
          <div className="col-span-2 flex gap-2 justify-end pt-2 border-t border-gray-200">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm border border-gray-300 hover:border-gray-500" data-testid="edit-cancel">Cancel</button>
            <button type="submit" disabled={saving} className="px-4 py-2 text-sm bg-[#0A0A0A] text-white hover:bg-[#002FA7] disabled:opacity-50" data-testid="edit-submit">{saving ? "Saving..." : "Save Changes"}</button>
          </div>
        </form>
        <style>{`.edit-input { width: 100%; padding: 0.5rem 0.75rem; border: 1px solid #D1D5DB; font-size: 0.875rem; border-radius: 0.125rem; }
          .edit-input:focus { outline: none; border-color: #002FA7; box-shadow: 0 0 0 2px rgba(0,47,167,0.2); }`}</style>
      </div>
    </div>
  );
}

function EditField({ label, children, colSpan = 1 }) {
  return (
    <div className={colSpan === 2 ? "col-span-2" : ""}>
      <label className="text-[10px] uppercase tracking-wider font-semibold text-gray-600 mb-1 block">{label}</label>
      {children}
    </div>
  );
}

