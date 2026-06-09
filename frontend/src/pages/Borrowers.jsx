import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import RiskBadge from "@/components/RiskBadge";
import { formatINR } from "@/lib/format";
import { MagnifyingGlass, Plus, CaretUp, CaretDown, UploadSimple } from "@phosphor-icons/react";
import { toast } from "sonner";
import { useAuth } from "@/lib/auth-context";

export default function Borrowers() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [data, setData] = useState({ items: [], total: 0 });
  const [filters, setFilters] = useState({ search: "", sector: "", risk_category: "", sort_by: "risk_score", order: "desc", page: 1 });
  const [sectors, setSectors] = useState([]);
  const [showAdd, setShowAdd] = useState(false);
  const [showBulk, setShowBulk] = useState(false);

  const load = async () => {
    try {
      const params = { ...filters, limit: 50 };
      Object.keys(params).forEach(k => params[k] === "" && delete params[k]);
      const res = await api.get("/borrowers", { params });
      setData(res.data);
    } catch (e) { toast.error("Failed to load borrowers"); }
  };

  useEffect(() => { load(); }, [filters]);
  useEffect(() => { api.get("/meta/sectors").then(r => setSectors(r.data)).catch(() => {}); }, []);

  const toggleSort = (col) => {
    setFilters(f => ({ ...f, sort_by: col, order: f.sort_by === col && f.order === "desc" ? "asc" : "desc" }));
  };

  const sortIcon = (col) => filters.sort_by !== col ? null : (filters.order === "desc" ? <CaretDown size={12} weight="bold"/> : <CaretUp size={12} weight="bold"/>);

  return (
    <div data-testid="borrowers-page">
      <PageHeader
        overline="PORTFOLIO"
        title="Borrowers"
        subtitle="Search, filter, and manage your MSME borrower portfolio."
        actions={
          (user?.role === "admin" || user?.role === "analyst") && (
            <div className="flex gap-2">
              <button onClick={() => setShowBulk(true)} data-testid="bulk-import-btn" className="px-3 py-2 text-xs uppercase tracking-wider font-semibold border border-gray-300 hover:border-[#0A0A0A] inline-flex items-center gap-1.5">
                <UploadSimple size={14} weight="bold"/> Bulk Import
              </button>
              <button onClick={() => setShowAdd(true)} data-testid="add-borrower-btn" className="px-3 py-2 text-xs uppercase tracking-wider font-semibold bg-[#0A0A0A] text-white hover:bg-[#002FA7] inline-flex items-center gap-1.5">
                <Plus size={14} weight="bold" /> Add Borrower
              </button>
            </div>
          )
        }
      />

      <div className="p-8 space-y-4">
        {/* Filters */}
        <div className="flex flex-wrap gap-2 items-center">
          <div className="relative flex-1 min-w-[240px]">
            <MagnifyingGlass size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search business name..."
              value={filters.search}
              onChange={(e) => setFilters({ ...filters, search: e.target.value, page: 1 })}
              data-testid="search-input"
              className="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-sm focus:border-[#002FA7] focus:outline-none focus:ring-2 focus:ring-[#002FA7]/20"
            />
          </div>
          <select value={filters.sector} onChange={(e) => setFilters({ ...filters, sector: e.target.value, page: 1 })} data-testid="sector-filter" className="px-3 py-2 text-sm border border-gray-300 rounded-sm bg-white">
            <option value="">All sectors</option>
            {sectors.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          <select value={filters.risk_category} onChange={(e) => setFilters({ ...filters, risk_category: e.target.value, page: 1 })} data-testid="risk-filter" className="px-3 py-2 text-sm border border-gray-300 rounded-sm bg-white">
            <option value="">All risk levels</option>
            <option value="low">Low</option>
            <option value="moderate">Moderate</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
        </div>

        {/* Table */}
        <div className="border border-gray-200 bg-white overflow-hidden" data-testid="borrowers-table">
          <table className="w-full text-sm">
            <thead className="bg-[#F9FAFB] border-b border-gray-200">
              <tr className="text-[10px] uppercase tracking-wider text-gray-600">
                <Th onClick={() => toggleSort("business_name")} icon={sortIcon("business_name")}>Business</Th>
                <Th onClick={() => toggleSort("sector")} icon={sortIcon("sector")}>Sector</Th>
                <Th onClick={() => toggleSort("location")} icon={sortIcon("location")}>Location</Th>
                <Th onClick={() => toggleSort("loan_amount")} icon={sortIcon("loan_amount")} align="right">Loan</Th>
                <Th onClick={() => toggleSort("outstanding_amount")} icon={sortIcon("outstanding_amount")} align="right">Outstanding</Th>
                <Th onClick={() => toggleSort("risk_score")} icon={sortIcon("risk_score")} align="right">Risk</Th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {data.items.map((b) => (
                <tr key={b.id} onClick={() => navigate(`/borrowers/${b.id}`)} data-testid={`borrower-row-${b.id}`} className="hover:bg-[#F9FAFB] cursor-pointer transition-colors">
                  <td className="px-4 py-3 font-medium">{b.business_name}</td>
                  <td className="px-4 py-3 text-gray-700">{b.sector}</td>
                  <td className="px-4 py-3 text-gray-700">{b.location}</td>
                  <td className="px-4 py-3 text-right font-mono text-gray-700">{formatINR(b.loan_amount)}</td>
                  <td className="px-4 py-3 text-right font-mono text-gray-700">{formatINR(b.outstanding_amount)}</td>
                  <td className="px-4 py-3 text-right"><RiskBadge category={b.risk_category} score={b.risk_score} /></td>
                </tr>
              ))}
              {data.items.length === 0 && (
                <tr><td colSpan="6" className="p-8 text-center text-sm text-gray-500">No borrowers match your filters.</td></tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="text-xs text-gray-500 font-mono">{data.total} borrower(s)</div>
      </div>

      {showAdd && <AddBorrowerDialog sectors={sectors} onClose={() => setShowAdd(false)} onCreated={load} />}
      {showBulk && <BulkImportDialog onClose={() => setShowBulk(false)} onImported={load} />}
    </div>
  );
}

function Th({ children, onClick, icon, align }) {
  return (
    <th onClick={onClick} className={`px-4 py-3 cursor-pointer font-semibold select-none ${align === "right" ? "text-right" : "text-left"}`}>
      <span className="inline-flex items-center gap-1">{children}{icon}</span>
    </th>
  );
}

function AddBorrowerDialog({ sectors, onClose, onCreated }) {
  const [form, setForm] = useState({
    business_name: "", sector: "Manufacturing", location: "", loan_amount: 1000000,
    loan_type: "Working Capital", sanction_date: new Date().toISOString().split("T")[0],
    outstanding_amount: 500000, gst_number: "", contact_person: "", contact_phone: "",
  });
  const [saving, setSaving] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api.post("/borrowers", { ...form, loan_amount: Number(form.loan_amount), outstanding_amount: Number(form.outstanding_amount) });
      toast.success("Borrower added");
      onCreated();
      onClose();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed");
    } finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={onClose} data-testid="add-borrower-dialog">
      <div className="bg-white border border-gray-200 max-w-lg w-full max-h-[90vh] overflow-auto" onClick={(e) => e.stopPropagation()}>
        <div className="border-b border-gray-200 px-6 py-4">
          <div className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-semibold">New</div>
          <h2 className="font-heading font-bold text-xl tracking-tight">Add Borrower</h2>
        </div>
        <form onSubmit={submit} className="p-6 space-y-3 grid grid-cols-2 gap-3">
          <Field label="Business Name *" colSpan={2}>
            <input required value={form.business_name} onChange={(e) => setForm({ ...form, business_name: e.target.value })} data-testid="form-business-name" className="form-input" />
          </Field>
          <Field label="Sector">
            <select value={form.sector} onChange={(e) => setForm({ ...form, sector: e.target.value })} data-testid="form-sector" className="form-input bg-white">
              {sectors.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </Field>
          <Field label="Location">
            <input value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} data-testid="form-location" className="form-input" />
          </Field>
          <Field label="Loan Type">
            <input value={form.loan_type} onChange={(e) => setForm({ ...form, loan_type: e.target.value })} data-testid="form-loan-type" className="form-input" />
          </Field>
          <Field label="Sanction Date">
            <input type="date" value={form.sanction_date} onChange={(e) => setForm({ ...form, sanction_date: e.target.value })} data-testid="form-sanction-date" className="form-input" />
          </Field>
          <Field label="Loan Amount (INR)">
            <input type="number" value={form.loan_amount} onChange={(e) => setForm({ ...form, loan_amount: e.target.value })} data-testid="form-loan-amount" className="form-input" />
          </Field>
          <Field label="Outstanding (INR)">
            <input type="number" value={form.outstanding_amount} onChange={(e) => setForm({ ...form, outstanding_amount: e.target.value })} data-testid="form-outstanding" className="form-input" />
          </Field>
          <Field label="GST Number">
            <input value={form.gst_number} onChange={(e) => setForm({ ...form, gst_number: e.target.value })} data-testid="form-gst" className="form-input" />
          </Field>
          <Field label="Contact Person">
            <input value={form.contact_person} onChange={(e) => setForm({ ...form, contact_person: e.target.value })} data-testid="form-contact" className="form-input" />
          </Field>
          <Field label="Contact Phone" colSpan={2}>
            <input value={form.contact_phone} onChange={(e) => setForm({ ...form, contact_phone: e.target.value })} data-testid="form-phone" className="form-input" />
          </Field>
          <div className="col-span-2 flex gap-2 justify-end pt-2 border-t border-gray-200">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm border border-gray-300 hover:border-gray-500" data-testid="form-cancel">Cancel</button>
            <button type="submit" disabled={saving} className="px-4 py-2 text-sm bg-[#0A0A0A] text-white hover:bg-[#002FA7] disabled:opacity-50" data-testid="form-submit">{saving ? "Saving..." : "Create"}</button>
          </div>
        </form>
      </div>
      <style>{`.form-input { width: 100%; padding: 0.5rem 0.75rem; border: 1px solid #D1D5DB; font-size: 0.875rem; border-radius: 0.125rem; }
        .form-input:focus { outline: none; border-color: #002FA7; box-shadow: 0 0 0 2px rgba(0,47,167,0.2); }`}</style>
    </div>
  );
}

function Field({ label, children, colSpan = 1 }) {
  return (
    <div className={colSpan === 2 ? "col-span-2" : ""}>
      <label className="text-[10px] uppercase tracking-wider font-semibold text-gray-600 mb-1 block">{label}</label>
      {children}
    </div>
  );
}

function BulkImportDialog({ onClose, onImported }) {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);

  const submit = async (e) => {
    e.preventDefault();
    if (!file) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await api.post("/borrowers/bulk-import", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setResult(res.data);
      if (res.data.created > 0) toast.success(`Imported ${res.data.created} borrowers`);
      if (res.data.errors.length > 0) toast.error(`${res.data.errors.length} row(s) failed`);
      onImported();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Bulk import failed");
    } finally { setUploading(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={onClose} data-testid="bulk-import-dialog">
      <div className="bg-white border border-gray-200 max-w-2xl w-full max-h-[90vh] overflow-auto" onClick={(e) => e.stopPropagation()}>
        <div className="border-b border-gray-200 px-6 py-4">
          <div className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-semibold">Import</div>
          <h2 className="font-heading font-bold text-xl tracking-tight">Bulk Import Borrowers</h2>
        </div>
        <form onSubmit={submit} className="p-6 space-y-4">
          <div className="bg-[#F9FAFB] border border-gray-200 p-4 rounded-sm text-xs">
            <div className="text-[10px] uppercase tracking-wider font-semibold text-gray-600 mb-1">Required CSV/XLSX columns</div>
            <code className="block font-mono mt-1 leading-relaxed">business_name, sector, location, loan_amount, loan_type, sanction_date, outstanding_amount</code>
            <div className="text-[10px] uppercase tracking-wider font-semibold text-gray-600 mt-2 mb-1">Optional</div>
            <code className="block font-mono leading-relaxed">gst_number, contact_person, contact_phone</code>
          </div>

          <label className="block border-2 border-dashed border-gray-300 hover:border-[#002FA7] p-8 text-center cursor-pointer transition-colors">
            <UploadSimple size={28} className="mx-auto text-gray-400 mb-2" />
            <div className="text-sm font-medium">{file ? file.name : "Click to select CSV/XLSX"}</div>
            <div className="text-xs text-gray-500 mt-1">.csv .xlsx .xls</div>
            <input type="file" accept=".csv,.xlsx,.xls" onChange={(e) => { setFile(e.target.files[0]); setResult(null); }} data-testid="bulk-import-file" className="hidden" />
          </label>

          {result && (
            <div className="border border-gray-200 p-3 rounded-sm" data-testid="bulk-import-result">
              <div className="text-sm font-semibold mb-1">Import result: {result.created} created, {result.errors.length} errors</div>
              {result.errors.length > 0 && (
                <div className="max-h-32 overflow-auto text-xs font-mono text-red-700 mt-2 space-y-0.5">
                  {result.errors.slice(0, 20).map((er, i) => <div key={i}>Row {er.row}: {er.error}</div>)}
                </div>
              )}
            </div>
          )}

          <div className="flex gap-2 justify-end pt-2 border-t border-gray-200">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm border border-gray-300 hover:border-gray-500" data-testid="bulk-cancel">Close</button>
            <button type="submit" disabled={!file || uploading} className="px-4 py-2 text-sm bg-[#0A0A0A] text-white hover:bg-[#002FA7] disabled:opacity-50" data-testid="bulk-submit">{uploading ? "Importing..." : "Import"}</button>
          </div>
        </form>
      </div>
    </div>
  );
}
