import { useEffect, useRef, useState } from "react";
import api from "@/lib/api";
import { Sparkle, PaperPlaneTilt } from "@phosphor-icons/react";

const RECOVERY_SUGGESTIONS = [
  "What's the best restructure option for this borrower?",
  "Should we consider a one-time settlement?",
  "What additional collateral would make sense?",
  "What are the next 3 concrete steps?",
  "Is this borrower likely to recover, or should we escalate?",
  "Draft a script for the next borrower call",
];

export default function RecoveryCopilot({ caseId, borrowerName }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef(null);

  const load = async () => {
    try {
      const res = await api.get(`/recovery/${caseId}/copilot`);
      setMessages(res.data);
    } catch {}
  };

  useEffect(() => { load(); }, [caseId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const send = async (text) => {
    const msg = text || input;
    if (!msg.trim()) return;
    setMessages(prev => [...prev, { id: `tmp-${Date.now()}`, role: "user", content: msg }]);
    setInput("");
    setLoading(true);
    try {
      const res = await api.post(`/recovery/${caseId}/copilot`, { message: msg });
      setMessages(prev => [...prev, { id: `bot-${Date.now()}`, role: "assistant", content: res.data.response }]);
    } catch (e) {
      setMessages(prev => [...prev, { id: `err-${Date.now()}`, role: "assistant", content: "Sorry, recovery copilot is unavailable. Please try again." }]);
    } finally { setLoading(false); }
  };

  return (
    <div className="border border-gray-200 bg-white flex flex-col" data-testid="recovery-copilot">
      <div className="px-5 py-3 border-b border-gray-200 bg-[#0A0A0A] text-white flex items-center gap-2">
        <Sparkle weight="fill" size={16} className="text-[#002FA7]" />
        <div>
          <div className="text-[10px] uppercase tracking-[0.2em] text-white/60">Recovery Strategist · AI</div>
          <div className="font-heading font-bold text-sm tracking-tight">Next-Step Advisor</div>
        </div>
      </div>

      <div ref={scrollRef} className="overflow-auto p-4 space-y-3 max-h-[480px] min-h-[300px]" data-testid="recovery-copilot-messages">
        {messages.length === 0 && (
          <div className="text-center py-4">
            <Sparkle weight="fill" size={24} className="text-[#002FA7] mx-auto mb-2" />
            <div className="font-heading font-bold text-base mb-1">Strategy for {borrowerName}</div>
            <div className="text-xs text-gray-600 mb-3">Grounded in this case's financials & timeline</div>
            <div className="space-y-1.5">
              {RECOVERY_SUGGESTIONS.map((s, i) => (
                <button key={i} onClick={() => send(s)} data-testid={`recovery-suggestion-${i}`} className="block w-full text-left text-xs px-3 py-2 border border-gray-200 hover:border-[#002FA7] hover:bg-[#F9FAFB] transition-colors rounded-sm">
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m) => (
          <div key={m.id} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[90%] px-3 py-2 text-sm rounded-sm ${m.role === "user" ? "bg-[#0A0A0A] text-white" : "bg-[#F9FAFB] border border-gray-200 text-gray-800"} whitespace-pre-wrap`}>
              {m.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-[#F9FAFB] border border-gray-200 px-3 py-2 text-sm rounded-sm">
              <span className="inline-flex gap-1">
                <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-pulse"></span>
                <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-pulse" style={{ animationDelay: "0.15s" }}></span>
                <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-pulse" style={{ animationDelay: "0.3s" }}></span>
              </span>
            </div>
          </div>
        )}
      </div>

      <div className="border-t border-gray-200 p-3 flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !loading && send()}
          placeholder="Ask for strategy, restructure, settlement..."
          data-testid="recovery-copilot-input"
          className="flex-1 border border-gray-300 px-3 py-2 text-sm focus:border-[#002FA7] focus:outline-none focus:ring-2 focus:ring-[#002FA7]/20 rounded-sm"
        />
        <button onClick={() => send()} disabled={loading || !input.trim()} data-testid="recovery-copilot-send" className="px-3 py-2 bg-[#0A0A0A] text-white hover:bg-[#002FA7] disabled:opacity-50">
          <PaperPlaneTilt size={16} weight="fill" />
        </button>
      </div>
    </div>
  );
}
