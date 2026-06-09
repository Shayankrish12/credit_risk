export const formatINR = (n) => {
  if (n == null || isNaN(n)) return "—";
  if (n >= 10000000) return `₹${(n / 10000000).toFixed(2)}Cr`;
  if (n >= 100000) return `₹${(n / 100000).toFixed(2)}L`;
  if (n >= 1000) return `₹${(n / 1000).toFixed(1)}K`;
  return `₹${Math.round(n).toLocaleString("en-IN")}`;
};

export const formatNumber = (n) => {
  if (n == null || isNaN(n)) return "—";
  return new Intl.NumberFormat("en-IN").format(Math.round(n));
};

export const riskColor = (category) => {
  switch (category) {
    case "critical": return "#E53E3E";
    case "high": return "#D69E2E";
    case "moderate": return "#002FA7";
    case "low": return "#38A169";
    default: return "#4B5563";
  }
};

export const riskBg = (category) => {
  switch (category) {
    case "critical": return "bg-red-50 text-red-700 border-red-200";
    case "high": return "bg-amber-50 text-amber-700 border-amber-200";
    case "moderate": return "bg-blue-50 text-blue-700 border-blue-200";
    case "low": return "bg-emerald-50 text-emerald-700 border-emerald-200";
    default: return "bg-gray-50 text-gray-700 border-gray-200";
  }
};

export const severityColor = (severity) => {
  switch (severity) {
    case "critical": return "bg-red-100 text-red-800 border-red-300";
    case "high": return "bg-amber-100 text-amber-800 border-amber-300";
    case "medium": return "bg-blue-100 text-blue-800 border-blue-300";
    case "low": return "bg-emerald-100 text-emerald-800 border-emerald-300";
    default: return "bg-gray-100 text-gray-700 border-gray-300";
  }
};

export const signalLabel = (key) => {
  const labels = {
    sales_decline: "Sales Decline",
    cash_flow_stress: "Cash Flow Stress",
    emi_delay: "EMI Delay",
    cheque_bounce: "Cheque Bounce",
    negative_news: "Negative News",
    high_leverage: "High Leverage",
    gst_mismatch: "GST Mismatch",
    low_bank_balance: "Low Bank Balance",
    revenue_volatility: "Revenue Volatility",
    risk_threshold: "Risk Threshold",
  };
  return labels[key] || key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
};
