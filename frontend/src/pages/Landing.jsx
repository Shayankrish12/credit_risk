import { Link } from "react-router-dom";
import { useAuth } from "@/lib/auth-context";
import { Warning, ChartLineDown, ShieldCheck, Lightning, ChatCircleDots, FileText, ArrowUpRight } from "@phosphor-icons/react";

export default function Landing() {
  const { user } = useAuth();

  return (
    <div className="min-h-screen bg-white text-[#0A0A0A]" data-testid="landing-page">
      {/* Header */}
      <header className="border-b border-gray-200 bg-white sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 bg-[#002FA7] flex items-center justify-center">
              <Warning weight="bold" size={18} className="text-white" />
            </div>
            <div>
              <div className="font-heading font-bold text-base tracking-tight">CREDIT.RISK</div>
              <div className="text-[10px] uppercase tracking-[0.2em] text-gray-500">Early Warning System</div>
            </div>
          </div>
          <nav className="flex items-center gap-1">
            {user ? (
              <Link to="/dashboard" data-testid="landing-dashboard-link" className="px-4 py-2 text-sm font-medium bg-[#0A0A0A] text-white hover:bg-[#002FA7] transition-colors">
                Open Dashboard
              </Link>
            ) : (
              <>
                <Link to="/login" data-testid="landing-login-link" className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-[#002FA7] transition-colors">
                  Sign in
                </Link>
                <Link to="/signup" data-testid="landing-signup-link" className="px-4 py-2 text-sm font-medium bg-[#0A0A0A] text-white hover:bg-[#002FA7] transition-colors">
                  Get started
                </Link>
              </>
            )}
          </nav>
        </div>
      </header>

      {/* Ticker stripe */}
      <div className="bg-[#0A0A0A] text-white py-2 overflow-hidden border-b border-black">
        <div className="flex items-center gap-8 text-[11px] uppercase tracking-[0.2em] px-6 whitespace-nowrap font-mono">
          <span className="text-[#38A169]">● LIVE</span>
          <span>SECTOR · TEXTILE: HIGH</span>
          <span className="text-gray-500">|</span>
          <span>SECTOR · MFG: MOD</span>
          <span className="text-gray-500">|</span>
          <span>EWS · 12 SIGNALS ACTIVE</span>
          <span className="text-gray-500">|</span>
          <span className="text-[#E53E3E]">CRITICAL · 3 BORROWERS</span>
          <span className="text-gray-500">|</span>
          <span>PORTFOLIO Δ +1.4%</span>
        </div>
      </div>

      {/* Hero */}
      <section className="relative">
        <div className="max-w-7xl mx-auto px-6 py-20 grid lg:grid-cols-12 gap-8">
          <div className="lg:col-span-7">
            <div className="text-[10px] uppercase tracking-[0.2em] text-[#002FA7] font-semibold mb-6">
              MSME · CREDIT MONITORING · AI ASSISTED
            </div>
            <h1 className="font-heading font-black text-5xl lg:text-6xl tracking-tighter leading-[0.95] mb-6">
              Catch borrower distress<br />
              <span className="text-[#002FA7]">before</span> default.
            </h1>
            <p className="text-base text-gray-700 max-w-xl mb-8 leading-relaxed">
              A control-room for credit analysts, relationship managers and risk teams. Real-time risk scores, early warning signals, and an AI copilot trained on borrower context.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link to={user ? "/dashboard" : "/signup"} data-testid="hero-cta-primary" className="px-6 py-3 bg-[#0A0A0A] text-white text-sm font-semibold hover:bg-[#002FA7] transition-colors inline-flex items-center gap-2">
                {user ? "Open Dashboard" : "Start Free"} <ArrowUpRight size={16} />
              </Link>
              <Link to="/login" data-testid="hero-cta-secondary" className="px-6 py-3 border border-gray-300 text-sm font-semibold hover:border-[#0A0A0A] transition-colors">
                Sign in
              </Link>
            </div>

            {/* Mini stats */}
            <div className="grid grid-cols-3 gap-0 mt-12 border-t border-gray-200">
              <Stat n="0–100" l="Risk Score" />
              <Stat n="9+" l="Signal Types" />
              <Stat n="Real" l="Data, Real ML" />
            </div>
          </div>

          <div className="lg:col-span-5">
            <div className="relative border border-gray-200 bg-[#F9FAFB] p-6 rounded-sm">
              <div className="absolute -top-3 left-6 bg-white px-2 text-[10px] uppercase tracking-[0.2em] font-semibold text-[#002FA7]">LIVE PREVIEW</div>
              <div className="space-y-3">
                <PreviewRow name="Sharma Textiles" sec="Textile" score={82} cat="critical" />
                <PreviewRow name="Verma Auto" sec="Manufacturing" score={67} cat="high" />
                <PreviewRow name="Patel Trading" sec="Trading" score={42} cat="moderate" />
                <PreviewRow name="Krishna Retail" sec="Retail" score={28} cat="moderate" />
                <PreviewRow name="Nair Software" sec="IT" score={18} cat="low" />
              </div>
              <div className="mt-4 pt-4 border-t border-gray-200 text-[10px] uppercase tracking-[0.2em] text-gray-500 font-mono">
                12 borrowers · 9 signals · 5 alerts
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="border-t border-gray-200 bg-[#F9FAFB] py-20">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-[10px] uppercase tracking-[0.2em] text-[#002FA7] font-semibold mb-3">Capabilities</div>
          <h2 className="font-heading font-bold text-4xl tracking-tight mb-12 max-w-2xl">A complete operating system for MSME credit risk.</h2>
          <div className="grid md:grid-cols-3 gap-0 border-l border-t border-gray-200">
            <Feat icon={ChartLineDown} title="Risk Scoring Engine" desc="Rule + ML hybrid: declining sales, bounces, EMI delays, cash flow stress, sector risk." />
            <Feat icon={ShieldCheck} title="Early Warning Signals" desc="9+ signal types with severity, explanation, and analyst-grade next actions." />
            <Feat icon={Lightning} title="Real-time Recompute" desc="Every upload re-runs the engine — score and signals update instantly." />
            <Feat icon={ChatCircleDots} title="AI Analyst Copilot" desc="Ask anything about a borrower. Grounded only in their data. Never hallucinates portfolio." />
            <Feat icon={FileText} title="Credit Notes" desc="Generate full credit monitoring notes as PDF or DOCX, ready for committee." />
            <Feat icon={Warning} title="Alert Routing" desc="Threshold-based alerts surface in dashboard and borrower profile." />
          </div>
        </div>
      </section>

      <footer className="border-t border-gray-200 py-8">
        <div className="max-w-7xl mx-auto px-6 flex items-center justify-between flex-wrap gap-4">
          <div className="text-xs text-gray-500 font-mono">© CREDIT.RISK · MSME Early Warning System</div>
          <div className="text-[10px] uppercase tracking-[0.2em] text-gray-500">Built for analysts who hate surprises</div>
        </div>
      </footer>
    </div>
  );
}

function Stat({ n, l }) {
  return (
    <div className="border-r border-gray-200 last:border-r-0 px-4 py-4 first:pl-0">
      <div className="font-heading font-bold text-2xl tracking-tight">{n}</div>
      <div className="text-[10px] uppercase tracking-[0.2em] text-gray-500 mt-1">{l}</div>
    </div>
  );
}

function PreviewRow({ name, sec, score, cat }) {
  const colors = {
    critical: "bg-red-50 text-red-700 border-red-200",
    high: "bg-amber-50 text-amber-700 border-amber-200",
    moderate: "bg-blue-50 text-blue-700 border-blue-200",
    low: "bg-emerald-50 text-emerald-700 border-emerald-200",
  };
  return (
    <div className="flex items-center justify-between bg-white border border-gray-200 px-3 py-2.5 rounded-sm">
      <div>
        <div className="font-medium text-sm">{name}</div>
        <div className="text-[10px] uppercase tracking-wider text-gray-500">{sec}</div>
      </div>
      <div className={`text-[11px] font-semibold uppercase tracking-wider border px-2 py-0.5 rounded-sm ${colors[cat]}`}>
        <span className="font-mono">{score}</span> {cat}
      </div>
    </div>
  );
}

function Feat({ icon: Icon, title, desc }) {
  return (
    <div className="border-r border-b border-gray-200 p-8 bg-white hover:bg-[#F9FAFB] transition-colors">
      <Icon size={28} weight="bold" className="text-[#002FA7] mb-4" />
      <div className="font-heading font-bold text-lg tracking-tight mb-2">{title}</div>
      <div className="text-sm text-gray-600 leading-relaxed">{desc}</div>
    </div>
  );
}
