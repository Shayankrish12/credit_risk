import { useEffect, useRef, useState } from "react";
import api from "@/lib/api";
import { X, PaperPlaneTilt, Sparkle } from "@phosphor-icons/react";

const SUGGESTIONS = [
  "Why is this borrower high risk?",
  "Summarize last 6 months cash flow",
  "What are the top warning signals?",
  "Generate a credit monitoring note outline",
  "Suggest follow-up questions for borrower",
  "Compare this borrower with sector risk",
];

export default function BorrowerChat({ borrowerId, borrowerName, onClose, embedded = false }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    api.get(`/chat/${borrowerId}`).then(r => setMessages(r.data)).catch(() => {});
  }, [borrowerId]);

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
      const res = await api.post("/chat", { borrower_id: borrowerId, message: msg });
      setMessages(prev => [...prev, { id: `bot-${Date.now()}`, role: "assistant", content: res.data.response }]);
    } catch (e) {
      setMessages(prev => [...prev, { id: `err-${Date.now()}`, role: "assistant", content: "Sorry, I couldn't process that. Please try again." }]);
    } finally { setLoading(false); }
  };

  const content = (
    <div className="flex flex-col h-full bg-white" data-testid="borrower-chat">
      {!embedded && (
        <div className="px-5 py-3 border-b border-gray-200 flex items-center justify-between bg-[#0A0A0A] text-white">
          <div className="flex items-center gap-2">
            <Sparkle weight="fill" size={18} className="text-[#002FA7]" />
            <div>
              <div className="text-[10px] uppercase tracking-[0.2em] text-white/60">AI Copilot</div>
              <div className="font-semibold text-sm">{borrowerName}</div>
            </div>
          </div>
          <button onClick={onClose} data-testid="close-chat-btn" className="hover:bg-white/10 p-1 rounded-sm"><X size={18}/></button>
        </div>
      )}
      <div ref={scrollRef} className="flex-1 overflow-auto p-4 space-y-3" data-testid="chat-messages">
        {messages.length === 0 && (
          <div className="text-center py-8">
            <Sparkle weight="fill" size={28} className="text-[#002FA7] mx-auto mb-3" />
            <div className="font-heading font-bold text-lg mb-1">Ask anything about {borrowerName}.</div>
            <div className="text-sm text-gray-600 mb-4">Grounded in this borrower's uploaded financial data.</div>
            <div className="space-y-1.5 max-w-md mx-auto">
              {SUGGESTIONS.map((s, i) => (
                <button key={i} onClick={() => send(s)} data-testid={`suggestion-${i}`} className="block w-full text-left text-xs px-3 py-2 border border-gray-200 hover:border-[#002FA7] hover:bg-[#F9FAFB] transition-colors rounded-sm">
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m) => (
          <div key={m.id} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[85%] px-3.5 py-2.5 text-sm rounded-sm ${m.role === "user" ? "bg-[#0A0A0A] text-white" : "bg-[#F9FAFB] border border-gray-200 text-gray-800"} whitespace-pre-wrap`}>
              {m.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-[#F9FAFB] border border-gray-200 px-3.5 py-2.5 text-sm rounded-sm">
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
          placeholder="Ask about this borrower..."
          data-testid="chat-input"
          className="flex-1 border border-gray-300 px-3 py-2 text-sm focus:border-[#002FA7] focus:outline-none focus:ring-2 focus:ring-[#002FA7]/20 rounded-sm"
        />
        <button onClick={() => send()} disabled={loading || !input.trim()} data-testid="send-chat-btn" className="px-4 py-2 bg-[#0A0A0A] text-white hover:bg-[#002FA7] disabled:opacity-50">
          <PaperPlaneTilt size={16} weight="fill" />
        </button>
      </div>
    </div>
  );

  if (embedded) return <div className="h-full">{content}</div>;

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4" onClick={onClose}>
      <div className="bg-white w-full sm:max-w-2xl h-[80vh] sm:h-[85vh] border border-gray-200 shadow-xl" onClick={(e) => e.stopPropagation()}>
        {content}
      </div>
    </div>
  );
}
