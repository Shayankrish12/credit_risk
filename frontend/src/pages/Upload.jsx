import { useEffect, useState } from "react";
import api, { API } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { toast } from "sonner";
import { UploadSimple, FileCsv, FilePdf, CheckCircle, Download } from "@phosphor-icons/react";

const FILE_TYPES = [
  { value: "sales", label: "Sales Data", template: "sales", accept: ".csv,.xlsx,.xls", hint: "month, amount" },
  { value: "bank", label: "Bank Statement", template: "bank", accept: ".csv,.xlsx,.xls", hint: "month, balance" },
  { value: "repayment", label: "Repayment History", template: "repayment", accept: ".csv,.xlsx,.xls", hint: "due_date, amount, status" },
  { value: "balance_sheet", label: "Balance Sheet", template: "balance_sheet", accept: ".csv,.xlsx,.xls", hint: "Quarterly: assets, liabilities, equity" },
  { value: "pnl", label: "Profit & Loss", template: "pnl", accept: ".csv,.xlsx,.xls", hint: "Quarterly: revenue, COGS, EBITDA, profit" },
  { value: "news", label: "News Article", template: null, accept: ".txt,.pdf", hint: "Adverse news sentiment scoring" },
];

export default function Upload() {
  const [borrowers, setBorrowers] = useState([]);
  const [borrowerId, setBorrowerId] = useState("");
  const [fileType, setFileType] = useState("sales");
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [history, setHistory] = useState([]);

  useEffect(() => {
    api.get("/borrowers?limit=200").then(r => {
      setBorrowers(r.data.items);
      if (r.data.items.length && !borrowerId) setBorrowerId(r.data.items[0].id);
    }).catch(() => {});
  }, []);

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file || !borrowerId) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("file_type", fileType);
      fd.append("file", file);
      const res = await api.post(`/borrowers/${borrowerId}/upload`, fd, { headers: { "Content-Type": "multipart/form-data" } });
      toast.success(`Uploaded · ${res.data.rows_processed} rows processed. Risk recomputed.`);
      const borrower = borrowers.find(b => b.id === borrowerId);
      setHistory(h => [{ filename: file.name, type: fileType, borrower: borrower?.business_name, rows: res.data.rows_processed, at: new Date().toLocaleTimeString() }, ...h]);
      setFile(null);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Upload failed");
    } finally { setUploading(false); }
  };

  const downloadTemplate = async (templateKey) => {
    try {
      const token = localStorage.getItem("msme_token");
      const res = await fetch(`${API}/templates/${templateKey}`, { headers: { Authorization: `Bearer ${token}` } });
      if (!res.ok) throw new Error();
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${templateKey}_template.csv`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("Template downloaded");
    } catch { toast.error("Download failed"); }
  };

  const activeType = FILE_TYPES.find(f => f.value === fileType);

  return (
    <div data-testid="upload-page">
      <PageHeader overline="DATA · INGEST" title="Upload Data" subtitle="Add fresh financial data per borrower. Risk score automatically recomputes after each upload." />
      <div className="p-8 grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 border border-gray-200 bg-white p-6" data-testid="upload-form-card">
          <form onSubmit={handleUpload} className="space-y-4">
            <div>
              <label className="text-[10px] uppercase tracking-wider font-semibold text-gray-600 mb-1 block">Borrower</label>
              <select value={borrowerId} onChange={(e) => setBorrowerId(e.target.value)} required data-testid="upload-borrower-select" className="w-full border border-gray-300 px-3 py-2 text-sm focus:border-[#002FA7] focus:outline-none rounded-sm bg-white">
                <option value="">Select borrower...</option>
                {borrowers.map(b => <option key={b.id} value={b.id}>{b.business_name} · {b.sector}</option>)}
              </select>
            </div>

            <div>
              <label className="text-[10px] uppercase tracking-wider font-semibold text-gray-600 mb-2 block">File Type</label>
              <div className="grid grid-cols-2 gap-2">
                {FILE_TYPES.map(ft => (
                  <button key={ft.value} type="button" onClick={() => setFileType(ft.value)} data-testid={`filetype-${ft.value}`} className={`text-left p-3 border rounded-sm transition-colors ${fileType === ft.value ? "border-[#002FA7] bg-[#F9FAFB]" : "border-gray-200 hover:border-gray-400"}`}>
                    <div className="flex items-center gap-2">
                      {ft.accept.includes("pdf") ? <FilePdf size={16} weight="bold" className="text-[#E53E3E]" /> : <FileCsv size={16} weight="bold" className="text-[#002FA7]" />}
                      <span className="font-medium text-sm">{ft.label}</span>
                    </div>
                    <div className="text-[10px] uppercase tracking-wider text-gray-500 mt-1">{ft.hint}</div>
                  </button>
                ))}
              </div>
            </div>

            {activeType?.template && (
              <button type="button" onClick={() => downloadTemplate(activeType.template)} data-testid="download-template-btn" className="text-xs uppercase tracking-wider font-semibold text-[#002FA7] inline-flex items-center gap-1.5 hover:underline">
                <Download size={14} weight="bold"/> Download {activeType.label} template
              </button>
            )}

            <div>
              <label className="text-[10px] uppercase tracking-wider font-semibold text-gray-600 mb-1 block">File</label>
              <label className="block border-2 border-dashed border-gray-300 hover:border-[#002FA7] p-8 text-center cursor-pointer transition-colors" data-testid="file-drop-zone">
                <UploadSimple size={32} className="mx-auto text-gray-400 mb-2" />
                <div className="text-sm font-medium">{file ? file.name : "Click to select file"}</div>
                <div className="text-xs text-gray-500 mt-1">{activeType?.accept}</div>
                <input type="file" accept={activeType?.accept} onChange={(e) => setFile(e.target.files[0])} data-testid="file-input" className="hidden" />
              </label>
            </div>

            <button type="submit" disabled={!file || !borrowerId || uploading} data-testid="upload-submit-btn" className="w-full px-4 py-2.5 text-sm font-semibold uppercase tracking-wider bg-[#0A0A0A] text-white hover:bg-[#002FA7] disabled:opacity-50">
              {uploading ? "Uploading..." : "Upload & Recompute Risk"}
            </button>
          </form>
        </div>

        <div className="border border-gray-200 bg-white" data-testid="upload-history-card">
          <div className="px-5 py-4 border-b border-gray-200">
            <div className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-semibold">Session</div>
            <div className="font-heading font-bold text-base tracking-tight">Recent Uploads</div>
          </div>
          <div className="divide-y divide-gray-100">
            {history.length === 0 && <div className="p-6 text-center text-sm text-gray-500">No uploads yet this session.</div>}
            {history.map((h, i) => (
              <div key={i} className="p-4">
                <div className="flex items-center gap-2">
                  <CheckCircle weight="fill" size={16} className="text-[#38A169]" />
                  <div className="text-sm font-medium truncate flex-1">{h.filename}</div>
                </div>
                <div className="text-[10px] uppercase tracking-wider text-gray-500 mt-1 ml-6">{h.type} · {h.rows} rows · {h.borrower}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Templates panel */}
        <div className="lg:col-span-3 border border-gray-200 bg-white p-6" data-testid="templates-panel">
          <div className="text-[10px] uppercase tracking-[0.2em] text-gray-500 font-semibold mb-1">Templates</div>
          <div className="font-heading font-bold text-base tracking-tight mb-4">Download CSV templates</div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
            {FILE_TYPES.filter(ft => ft.template).map(ft => (
              <button key={ft.template} onClick={() => downloadTemplate(ft.template)} data-testid={`download-tpl-${ft.template}`} className="flex items-center gap-2 px-3 py-2.5 border border-gray-200 hover:border-[#002FA7] hover:bg-[#F9FAFB] rounded-sm transition-colors text-left">
                <Download size={14} weight="bold" className="text-[#002FA7]" />
                <div className="min-w-0">
                  <div className="text-sm font-medium">{ft.label}</div>
                  <div className="text-[10px] uppercase tracking-wider text-gray-500 truncate">{ft.hint}</div>
                </div>
              </button>
            ))}
            <button onClick={() => downloadTemplate("borrowers_bulk")} data-testid="download-tpl-borrowers_bulk" className="flex items-center gap-2 px-3 py-2.5 border border-gray-200 hover:border-[#002FA7] hover:bg-[#F9FAFB] rounded-sm transition-colors text-left">
              <Download size={14} weight="bold" className="text-[#002FA7]" />
              <div className="min-w-0">
                <div className="text-sm font-medium">Borrowers Bulk Import</div>
                <div className="text-[10px] uppercase tracking-wider text-gray-500 truncate">For Borrowers → Bulk Import</div>
              </div>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
