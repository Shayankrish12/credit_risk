import { useEffect, useState } from "react";
import api from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import BorrowerChat from "@/components/BorrowerChat";
import RiskBadge from "@/components/RiskBadge";

export default function Copilot() {
  const [borrowers, setBorrowers] = useState([]);
  const [selected, setSelected] = useState(null);
  const [search, setSearch] = useState("");

  useEffect(() => {
    api.get("/borrowers?limit=200").then(r => {
      setBorrowers(r.data.items);
      if (r.data.items.length) setSelected(r.data.items[0]);
    }).catch(() => {});
  }, []);

  const filtered = search ? borrowers.filter(b => b.business_name.toLowerCase().includes(search.toLowerCase())) : borrowers;

  return (
    <div data-testid="copilot-page" className="flex flex-col h-full">
      <PageHeader overline="AI · COPILOT" title="Analyst Copilot" subtitle="Ask anything about a specific borrower. Grounded only in their data." />
      <div className="flex-1 grid lg:grid-cols-12 gap-0 border-t border-gray-200">
        <div className="lg:col-span-3 border-r border-gray-200 bg-white overflow-auto" data-testid="copilot-borrower-list">
          <div className="p-3 border-b border-gray-200">
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search..."
              data-testid="copilot-search"
              className="w-full border border-gray-300 px-3 py-2 text-sm focus:border-[#002FA7] focus:outline-none rounded-sm"
            />
          </div>
          <div className="divide-y divide-gray-100">
            {filtered.map(b => (
              <button key={b.id} onClick={() => setSelected(b)} data-testid={`copilot-select-${b.id}`} className={`w-full text-left px-4 py-3 hover:bg-[#F9FAFB] transition-colors ${selected?.id === b.id ? "bg-[#F9FAFB] border-l-2 border-[#002FA7]" : ""}`}>
                <div className="flex items-center justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-medium truncate">{b.business_name}</div>
                    <div className="text-[10px] uppercase tracking-wider text-gray-500">{b.sector}</div>
                  </div>
                  <RiskBadge category={b.risk_category} score={b.risk_score} />
                </div>
              </button>
            ))}
            {filtered.length === 0 && <div className="p-6 text-center text-sm text-gray-500">No borrowers</div>}
          </div>
        </div>
        <div className="lg:col-span-9 h-[calc(100vh-180px)]">
          {selected ? (
            <BorrowerChat borrowerId={selected.id} borrowerName={selected.business_name} embedded onClose={() => {}} />
          ) : (
            <div className="h-full flex items-center justify-center text-sm text-gray-500">Select a borrower to begin chatting.</div>
          )}
        </div>
      </div>
    </div>
  );
}
