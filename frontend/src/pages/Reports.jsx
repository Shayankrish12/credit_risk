import { useEffect, useState } from "react";
import api, { API } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import RiskBadge from "@/components/RiskBadge";
import { formatINR } from "@/lib/format";
import { FilePdf, FileDoc, Download } from "@phosphor-icons/react";
import { toast } from "sonner";

export default function Reports() {
  const [borrowers, setBorrowers] = useState([]);
  const [search, setSearch] = useState("");

  useEffect(() => {
    api.get("/borrowers?limit=200").then(r => setBorrowers(r.data.items)).catch(() => {});
  }, []);

  const download = async (id, name, fmt) => {
    try {
      const token = localStorage.getItem("msme_token");
      const res = await fetch(`${API}/reports/${id}/${fmt}`, { headers: { Authorization: `Bearer ${token}` } });
      if (!res.ok) throw new Error();
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${name.replace(/\s+/g, "_")}_credit_note.${fmt}`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success(`${fmt.toUpperCase()} downloaded`);
    } catch { toast.error("Download failed"); }
  };

  const filtered = search ? borrowers.filter(b => b.business_name.toLowerCase().includes(search.toLowerCase())) : borrowers;

  return (
    <div data-testid="reports-page">
      <PageHeader overline="EXPORT" title="Credit Monitoring Notes" subtitle="Generate professional credit notes as PDF or DOCX for any borrower." />
      <div className="p-8 space-y-4">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search borrowers..."
          data-testid="reports-search"
          className="w-full max-w-md border border-gray-300 px-3 py-2 text-sm focus:border-[#002FA7] focus:outline-none rounded-sm"
        />

        <div className="border border-gray-200 bg-white" data-testid="reports-table">
          <table className="w-full text-sm">
            <thead className="bg-[#F9FAFB] border-b border-gray-200">
              <tr className="text-[10px] uppercase tracking-wider text-gray-600">
                <th className="px-4 py-2 text-left">Business</th>
                <th className="px-4 py-2 text-left">Sector</th>
                <th className="px-4 py-2 text-right">Outstanding</th>
                <th className="px-4 py-2 text-right">Risk</th>
                <th className="px-4 py-2 text-right">Export</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filtered.map(b => (
                <tr key={b.id} data-testid={`report-row-${b.id}`}>
                  <td className="px-4 py-3 font-medium">{b.business_name}</td>
                  <td className="px-4 py-3 text-gray-700">{b.sector}</td>
                  <td className="px-4 py-3 text-right font-mono">{formatINR(b.outstanding_amount)}</td>
                  <td className="px-4 py-3 text-right"><RiskBadge category={b.risk_category} score={b.risk_score} /></td>
                  <td className="px-4 py-3 text-right">
                    <div className="inline-flex gap-1">
                      <button onClick={() => download(b.id, b.business_name, "pdf")} data-testid={`report-pdf-${b.id}`} className="px-2 py-1 text-[10px] uppercase tracking-wider font-semibold border border-gray-300 hover:border-[#0A0A0A] inline-flex items-center gap-1">
                        <FilePdf size={12} weight="bold"/> PDF
                      </button>
                      <button onClick={() => download(b.id, b.business_name, "docx")} data-testid={`report-docx-${b.id}`} className="px-2 py-1 text-[10px] uppercase tracking-wider font-semibold border border-gray-300 hover:border-[#0A0A0A] inline-flex items-center gap-1">
                        <FileDoc size={12} weight="bold"/> DOCX
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && <tr><td colSpan="5" className="p-8 text-center text-sm text-gray-500">No borrowers</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
