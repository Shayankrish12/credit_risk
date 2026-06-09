import { useEffect, useState } from "react";
import api from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { toast } from "sonner";

const ACTION_COLORS = {
  create: "bg-emerald-50 text-emerald-700 border-emerald-200",
  update: "bg-blue-50 text-blue-700 border-blue-200",
  delete: "bg-red-50 text-red-700 border-red-200",
  upload: "bg-amber-50 text-amber-700 border-amber-200",
  bulk_import: "bg-purple-50 text-purple-700 border-purple-200",
  recompute: "bg-blue-50 text-blue-700 border-blue-200",
  export: "bg-gray-100 text-gray-700 border-gray-300",
};

export default function AuditLog() {
  const [logs, setLogs] = useState([]);
  const [resource, setResource] = useState("");

  const load = async () => {
    try {
      const params = {};
      if (resource) params.resource = resource;
      const res = await api.get("/audit", { params });
      setLogs(res.data);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Failed to load audit log");
    }
  };

  useEffect(() => { load(); }, [resource]);

  return (
    <div data-testid="audit-page">
      <PageHeader overline="COMPLIANCE" title="Audit Log" subtitle="Immutable log of all analyst and admin actions across the platform." />
      <div className="p-8 space-y-4">
        <div className="flex gap-1 border-b border-gray-200">
          {["", "borrower", "note", "recovery"].map(r => (
            <button key={r || "all"} onClick={() => setResource(r)} data-testid={`audit-filter-${r || "all"}`} className={`px-4 py-2 text-xs uppercase tracking-wider font-semibold border-b-2 -mb-px ${resource === r ? "border-[#002FA7] text-[#0A0A0A]" : "border-transparent text-gray-500 hover:text-gray-700"}`}>
              {r || "All"}
            </button>
          ))}
        </div>

        <div className="border border-gray-200 bg-white overflow-x-auto" data-testid="audit-table">
          <table className="w-full text-sm">
            <thead className="bg-[#F9FAFB] border-b border-gray-200">
              <tr className="text-[10px] uppercase tracking-wider text-gray-600">
                <th className="px-4 py-2 text-left">When</th>
                <th className="px-4 py-2 text-left">User</th>
                <th className="px-4 py-2 text-left">Role</th>
                <th className="px-4 py-2 text-left">Action</th>
                <th className="px-4 py-2 text-left">Resource</th>
                <th className="px-4 py-2 text-left">Name</th>
                <th className="px-4 py-2 text-left">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {logs.map(l => (
                <tr key={l.id} data-testid={`audit-row-${l.id}`}>
                  <td className="px-4 py-2.5 font-mono text-[11px] text-gray-600 whitespace-nowrap">{l.at?.slice(0, 16).replace("T", " ")}</td>
                  <td className="px-4 py-2.5 text-xs">{l.user_name}</td>
                  <td className="px-4 py-2.5 text-[10px] uppercase tracking-wider font-semibold text-gray-700">{l.user_role}</td>
                  <td className="px-4 py-2.5"><span className={`inline-flex px-2 py-0.5 text-[10px] uppercase tracking-wider font-bold border rounded-sm ${ACTION_COLORS[l.action] || "bg-gray-50 text-gray-700 border-gray-200"}`}>{l.action}</span></td>
                  <td className="px-4 py-2.5 text-xs text-gray-700">{l.resource}</td>
                  <td className="px-4 py-2.5 text-xs">{l.resource_name || "—"}</td>
                  <td className="px-4 py-2.5 text-xs text-gray-600">{l.details || "—"}</td>
                </tr>
              ))}
              {logs.length === 0 && <tr><td colSpan="7" className="p-8 text-center text-sm text-gray-500">No audit entries yet.</td></tr>}
            </tbody>
          </table>
        </div>

        <div className="text-xs text-gray-500 font-mono">{logs.length} entries (latest 200)</div>
      </div>
    </div>
  );
}
